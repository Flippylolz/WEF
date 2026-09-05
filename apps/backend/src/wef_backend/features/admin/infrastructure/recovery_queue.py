"""Bounded eligible work selection and durable per-revision recovery claims."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text

from wef_backend.features.admin.application.automatic_recovery import RecoveryWork
from wef_backend.features.admin.infrastructure.provider_budget_store import next_day
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION
from wef_backend.features.ingestion.application.parse_quality import POLICY_VERSION

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

CHUNK_SIZE = 10
YIELD_SECONDS = 5
CANARY_SIZE = 10
SCHEMA_VERSION = "e25-recovery-v2"


class SQLAlchemyRecoveryQueue:
    """Keep source text out of checkpoints; current eligibility is always rechecked."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind short database transactions."""
        self._sessions = sessions

    async def enqueue(self, owner: UUID, now: datetime) -> int:
        """Skip completed identities so later records cannot starve."""
        await self.reconcile_unsubmitted(owner, now)
        total, started = 0, time.monotonic()
        for _ in range(10):
            async with self._sessions.begin() as session:
                rows = (
                    (
                        await session.execute(
                            text("""
                    SELECT e.* FROM parse_evaluations e
                    JOIN source_messages m ON m.current_revision_id=e.source_message_revision_id
                    WHERE e.state='open' AND e.recovery_eligible AND m.deleted_at IS NULL
                      AND e.parser_version=:parser AND e.policy_version=:policy
                      AND NOT EXISTS (SELECT 1 FROM ai_recovery_work w
                        WHERE w.source_revision_id=e.source_message_revision_id
                        AND w.parser_version=e.parser_version AND w.policy_version=e.policy_version
                        AND w.schema_version=:schema)
                    ORDER BY e.created_at,e.id LIMIT 10
                """),
                            {
                                "parser": PARSER_VERSION,
                                "policy": POLICY_VERSION,
                                "schema": SCHEMA_VERSION,
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                for row in rows:
                    fields = [
                        field["field_name"]
                        for field in row["fields_json"]
                        if field["classification"] == "extraction_miss"
                    ]
                    await session.execute(
                        text("""
                        INSERT INTO ai_recovery_work(id,evaluation_id,source_revision_id,
                            parser_version,policy_version,schema_version,state,missing_fields,
                            owner_id,next_eligible_at,created_at,updated_at)
                        VALUES (:id,:evaluation,:revision,:parser,:policy,:schema,'queued',
                            CAST(:fields AS jsonb),:owner,:now,:now,:now) ON CONFLICT DO NOTHING
                    """),
                        {
                            "id": uuid4(),
                            "evaluation": row["id"],
                            "revision": row["source_message_revision_id"],
                            "parser": PARSER_VERSION,
                            "policy": POLICY_VERSION,
                            "schema": SCHEMA_VERSION,
                            "fields": json.dumps(fields),
                            "owner": owner,
                            "now": now,
                        },
                    )
                total += len(rows)
            if len(rows) < CHUNK_SIZE or time.monotonic() - started >= YIELD_SECONDS:
                break
            await asyncio.sleep(0)
        return total

    async def reconcile_unsubmitted(self, owner: UUID, now: datetime) -> int:
        """Restore at most ten incorrectly terminal, provably unsubmitted cohorts."""
        async with self._sessions.begin() as session:
            result = await session.execute(
                text("""
                WITH candidates AS (
                    SELECT w.id FROM ai_recovery_work w
                    JOIN offer_ai_enrichment_batches b ON b.id=w.id
                    WHERE w.owner_id=:owner AND b.owner_user_id=:owner
                      AND w.state='terminal' AND w.reason='unsupported_or_failed_proposal'
                      AND w.proposal_id IS NULL
                      AND ((b.state IN ('queued','running') AND b.failure_category IS NULL)
                        OR (b.state='paused' AND b.failure_category='daily_limit'))
                      AND EXISTS (SELECT 1 FROM offer_ai_enrichment_items i WHERE i.batch_id=w.id)
                      AND NOT EXISTS (SELECT 1 FROM offer_ai_enrichment_items i
                        WHERE i.batch_id=w.id AND (i.state NOT IN ('queued','processing')
                          OR i.provider_called_at IS NOT NULL OR i.outcome IS NOT NULL))
                      AND NOT EXISTS (SELECT 1 FROM ai_provider_attempts p
                        WHERE p.operation_id=w.id)
                      AND NOT EXISTS (SELECT 1 FROM offer_ai_field_events e WHERE e.batch_id=w.id)
                    ORDER BY w.updated_at,w.id LIMIT 10 FOR UPDATE OF w SKIP LOCKED
                )
                UPDATE ai_recovery_work w SET state='queued',reason='unsubmitted_reconciled',
                    next_eligible_at=:now,claim_id=NULL,lease_until=NULL,updated_at=:now
                FROM candidates c WHERE w.id=c.id RETURNING w.id
                """),
                {"owner": owner, "now": now},
            )
            return len(result.all())

    async def claim(self, owner: UUID, now: datetime) -> RecoveryWork | None:
        """Lease one current item; application services reconcile saved proposal/item state."""
        async with self._sessions.begin() as session:
            row = (
                (
                    await session.execute(
                        text("""
                SELECT w.* FROM ai_recovery_work w
                WHERE w.owner_id=:owner AND (w.state IN ('queued','deferred','validated') OR
                    (w.state='claimed' AND w.lease_until<=:now)) AND w.next_eligible_at<=:now
                ORDER BY w.next_eligible_at,w.id LIMIT 1 FOR UPDATE SKIP LOCKED
            """),
                        {"now": now, "owner": owner},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            current = await session.scalar(
                text("""
                SELECT m.id FROM source_messages m JOIN parse_evaluations e
                    ON e.source_message_revision_id=m.current_revision_id
                WHERE e.id=:evaluation AND e.state='open' AND e.recovery_eligible
                    AND m.deleted_at IS NULL
            """),
                {"evaluation": row["evaluation_id"]},
            )
            if (
                current is None
                or row["parser_version"] != PARSER_VERSION
                or row["policy_version"] != POLICY_VERSION
                or row["schema_version"] != SCHEMA_VERSION
            ):
                await session.execute(
                    text("""
                    UPDATE ai_recovery_work SET state='superseded',
                            reason='source_or_evaluation_changed',
                        updated_at=:now WHERE id=:id
                """),
                    {"id": row["id"], "now": now},
                )
                return None
            claim = uuid4()
            await session.execute(
                text("""
                UPDATE ai_recovery_work SET state='claimed',claim_id=:claim,lease_until=:lease,
                    attempts=attempts+1,updated_at=:now WHERE id=:id
            """),
                {
                    "claim": claim,
                    "lease": now + timedelta(seconds=120),
                    "now": now,
                    "id": row["id"],
                },
            )
            offer = await session.scalar(
                text("""
                SELECT offer_id FROM offer_sources WHERE source_message_id=:message
                AND relationship='primary' LIMIT 1
            """),
                {"message": current},
            )
            return RecoveryWork(
                row["id"],
                row["source_revision_id"],
                row["owner_id"],
                claim,
                offer,
                row["proposal_id"],
                row["attempts"] + 1,
                tuple(row["missing_fields"]),
            )

    async def finish(
        self,
        work: RecoveryWork,
        state: str,
        reason: str | None,
        now: datetime,
        proposal_id: UUID | None = None,
    ) -> None:
        """Only a still-held claim can checkpoint a result."""
        async with self._sessions.begin() as session:
            await session.execute(
                text("""
                UPDATE ai_recovery_work SET state=:state,reason=:reason,proposal_id=:proposal,
                    lease_until=NULL,claim_id=NULL,updated_at=:now
                WHERE id=:id AND claim_id=:claim AND state='claimed'
            """),
                {
                    "state": state,
                    "reason": reason,
                    "proposal": proposal_id,
                    "now": now,
                    "id": work.id,
                    "claim": work.claim_id,
                },
            )

    async def retry_local(self, work: RecoveryWork, now: datetime) -> None:
        """Release claims with exponential delay, then stop repeated systemic failures."""
        async with self._sessions.begin() as session:
            await session.execute(
                text("""
                UPDATE ai_recovery_work SET local_failures=local_failures+1,
                    state=CASE WHEN local_failures>=2 THEN 'terminal' ELSE 'deferred' END,
                    reason=CASE WHEN local_failures>=2 THEN 'systemic_failure'
                        ELSE 'local_retry' END,
                    next_eligible_at=CAST(:now AS timestamptz) +
                        make_interval(secs=>LEAST(3600,60*power(2,local_failures))::int),
                    lease_until=NULL,claim_id=NULL,updated_at=:now
                WHERE id=:id AND claim_id=:claim
            """),
                {"now": now, "id": work.id, "claim": work.claim_id},
            )

    async def cohort_outcome(self, work: RecoveryWork) -> tuple[str, str | None]:
        """Reject unsupported/skipped fields from the observation canary."""
        async with self._sessions() as session:
            events = (
                (
                    await session.execute(
                        text("SELECT outcome,reason FROM offer_ai_field_events WHERE batch_id=:id"),
                        {"id": work.id},
                    )
                )
                .mappings()
                .all()
            )
            if not events or any(
                event["reason"] not in {"applied", "below_threshold"} for event in events
            ):
                return "terminal", "unsupported_or_failed_proposal"
            if any(event["outcome"] == "applied" for event in events):
                return "applied", None
            return "observed", "validated_observation"

    async def canary_passed(self) -> bool:
        """Only validated observations of this accepted policy count toward canary."""
        async with self._sessions() as session:
            count = await session.scalar(
                text("""
                SELECT count(DISTINCT source_revision_id) FROM ai_recovery_work
                WHERE state='observed' AND reason='validated_observation'
                    AND parser_version=:parser AND policy_version=:policy
                    AND schema_version=:schema
            """),
                {"parser": PARSER_VERSION, "policy": POLICY_VERSION, "schema": SCHEMA_VERSION},
            )
            return int(count or 0) >= CANARY_SIZE

    async def defer_provider(self, work: RecoveryWork, now: datetime) -> bool:
        """Read allocation state and checkpoint deferral without consuming another item."""
        async with self._sessions.begin() as session:
            attempt = (
                (
                    await session.execute(
                        text(
                            "SELECT state,reason FROM ai_provider_attempts "
                            "WHERE operation_id=:id ORDER BY created_at DESC LIMIT 1"
                        ),
                        {"id": work.id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if attempt is not None and attempt["state"] in {"terminal", "uncertain"}:
                await session.execute(
                    text(
                        "UPDATE ai_recovery_work SET state='terminal',reason=:reason,"
                        "lease_until=NULL,claim_id=NULL,updated_at=:now "
                        "WHERE id=:id AND claim_id=:claim"
                    ),
                    {
                        "reason": attempt["reason"],
                        "now": now,
                        "id": work.id,
                        "claim": work.claim_id,
                    },
                )
                return True
            if attempt is not None and attempt["state"] == "succeeded":
                return False
            row = (
                (
                    await session.execute(
                        text("""
                SELECT * FROM ai_provider_accounts WHERE owner_id=:owner
            """),
                        {"owner": work.owner_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            daily_paused = await session.scalar(
                text("""
                SELECT id FROM offer_ai_enrichment_batches
                WHERE id=:id AND state='paused' AND failure_category='daily_limit'
                """),
                {"id": work.id},
            )
            if row is None and daily_paused is None:
                return False
            eligible = row["next_eligible_at"] if row is not None else now
            if daily_paused is not None or (
                row is not None and row["budget_day"] == now.date() and row["used"] >= 20  # noqa: PLR2004
            ):
                # Recover accounts written before quota refusal persisted its window.
                eligible = max(eligible, next_day(now))
            if eligible <= now:
                return False
            await session.execute(
                text("""
                UPDATE ai_recovery_work SET state='deferred',reason='provider_window',
                    next_eligible_at=:next,lease_until=NULL,claim_id=NULL,updated_at=:now
                WHERE id=:id AND claim_id=:claim
            """),
                {
                    "id": work.id,
                    "claim": work.claim_id,
                    "now": now,
                    "next": eligible,
                },
            )
            return True
