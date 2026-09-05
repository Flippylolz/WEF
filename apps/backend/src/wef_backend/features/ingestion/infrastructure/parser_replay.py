"""Versioned replay with short claims and guarded atomic field/provenance writes."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select, text

from wef_backend.features.admin.application.offer_enrichment import value_fingerprint
from wef_backend.features.admin.infrastructure.ai_enrichment_models import OfferFieldOriginRow
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.parse_quality import POLICY_VERSION
from wef_backend.features.ingestion.application.parser_replay import (
    ACCEPTED_RELEASE,
    FIELD_COLUMNS,
    SCHEMA_VERSION,
    ReplayPlan,
    plan_replay,
    scalar,
)
from wef_backend.features.ingestion.application.persistence import extraction_fingerprint
from wef_backend.features.ingestion.domain.model import SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.parse_evaluation_store import (
    record_parse_evaluation,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.domain.extraction import ExtractionResult

RELEASE = f"{PARSER_VERSION}/{POLICY_VERSION}/{SCHEMA_VERSION}"
CHUNK_SIZE = 10
CANARY_SIZE = 25
TICK_LIMIT = 100
YIELD_SECONDS = 5


class SQLAlchemyParserReplay:
    """A bounded worker tick never submits providers or invokes the broad offer upsert."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind the existing database pool."""
        self._sessions = sessions

    async def tick(self, now: datetime, *, apply: bool, live_ready: Callable[[], bool]) -> None:
        """Pause unsupported/downgraded versions and yield before each short transaction."""
        if (PARSER_VERSION, POLICY_VERSION) != ACCEPTED_RELEASE or not live_ready():
            return
        started = time.monotonic()
        after_id = None
        for _ in range(CHUNK_SIZE):
            if not live_ready() or time.monotonic() - started >= YIELD_SECONDS:
                return
            selected, after_id = await self.discover(now, after_id=after_id)
            if selected < CHUNK_SIZE:
                break
        for _ in range(TICK_LIMIT):
            if not live_ready() or time.monotonic() - started >= YIELD_SECONDS:
                break
            work = await self.claim(now, apply=apply)
            if work is None:
                break
            try:
                await self.process(work, now, apply=apply and live_ready())
            except Exception:  # noqa: BLE001 - durable bounded retries contain no exception/source body
                await self.fail(work, now)
        await self.promote()

    async def discover(
        self, now: datetime, *, after_id: UUID | None = None
    ) -> tuple[int, UUID | None]:
        """Anti-identity keyset order prevents terminal first-page starvation."""
        async with self._sessions.begin() as session:
            await session.execute(
                text("""
INSERT INTO parser_replay_releases(version,parser_version,policy_version,phase)
VALUES (:release,:parser,:policy,'canary') ON CONFLICT DO NOTHING
"""),
                {"release": RELEASE, "parser": PARSER_VERSION, "policy": POLICY_VERSION},
            )
            newer = await session.scalar(
                text("""
                SELECT EXISTS(SELECT 1 FROM parser_replay_releases
                    WHERE parser_version ~ '^e2-v[0-9]+$'
                    AND substring(parser_version from 5)::integer > :generation)
            """),
                {"generation": int(PARSER_VERSION.removeprefix("e2-v"))},
            )
            if newer:
                await session.execute(
                    text(
                        """
UPDATE parser_replay_releases SET phase='paused',reason='version_downgrade' WHERE
version=:release
"""
                    ),
                    {"release": RELEASE},
                )
                return 0, after_id
            rows = (
                await session.execute(
                    text("""
SELECT m.id,m.current_revision_id FROM source_messages m WHERE NOT EXISTS(SELECT 1
FROM parser_replay_work w WHERE w.revision_id=m.current_revision_id AND
w.release_version=:release)
AND (CAST(:after AS uuid) IS NULL OR m.id>CAST(:after AS uuid))
ORDER BY m.id LIMIT 10
"""),
                    {"release": RELEASE, "after": after_id},
                )
            ).all()
            for message, revision in rows:
                await session.execute(
                    text("""
INSERT INTO
parser_replay_work(id,release_version,message_id,revision_id,state,next_eligible_at)
VALUES (:id,:release,:message,:revision,'queued',:now) ON CONFLICT DO NOTHING
"""),
                    {
                        "id": uuid4(),
                        "release": RELEASE,
                        "message": message,
                        "revision": revision,
                        "now": now,
                    },
                )

            return len(rows), rows[-1][0] if rows else after_id

    async def claim(self, now: datetime, *, apply: bool) -> dict[str, object] | None:
        """Claim/reclaim one item without holding its source or offer across parsing."""
        async with self._sessions.begin() as session:
            await session.execute(
                text(
                    "SELECT version FROM parser_replay_releases WHERE version=:release FOR UPDATE"
                ),
                {"release": RELEASE},
            )
            row = (
                (
                    await session.execute(
                        text("""
SELECT w.*,r.phase FROM parser_replay_work w JOIN parser_replay_releases r ON
r.version=w.release_version WHERE w.release_version=:release AND r.phase<>'paused'
                AND NOT EXISTS(SELECT 1 FROM parser_replay_work busy
                    WHERE busy.release_version=r.version AND busy.state='claimed'
                    AND busy.lease_until>:now)
AND (r.phase<>'canary' OR (SELECT count(*) FROM parser_replay_work c WHERE
c.release_version=r.version AND c.canary_passed)<25) AND (w.state IN
('queued','deferred') OR (w.state='claimed' AND w.lease_until<=:now) OR
(w.state='observed' AND r.phase='running' AND :apply)) AND w.next_eligible_at<=:now
ORDER BY w.next_eligible_at,w.id LIMIT 1 FOR UPDATE OF w SKIP LOCKED
"""),
                        {"release": RELEASE, "now": now, "apply": apply},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            work = dict(row)
            work["claim_id"] = uuid4()
            await session.execute(
                text("""
UPDATE parser_replay_work SET state='claimed',claim_id=:claim,lease_until=:lease,
attempts=attempts+1 WHERE id=:id
"""),
                {
                    "claim": work["claim_id"],
                    "lease": now + timedelta(seconds=120),
                    "id": work["id"],
                },
            )
            return work

    async def process(self, work: dict[str, object], now: datetime, *, apply: bool) -> None:
        """Decode retained original evidence outside the canonical transaction."""
        async with self._sessions() as session:
            message = await session.get(SourceMessageRow, work["message_id"])
            revision = await session.get(SourceMessageRevisionRow, work["revision_id"])
            channel = (
                await session.get(SourceChannelRow, message.source_channel_id) if message else None
            )
        if message is None or revision is None or channel is None or message.deleted_at is not None:
            await self.finish(work, "excluded", "deleted_or_missing", now)
            return
        if not isinstance(revision.raw_payload_json, Mapping):
            await self.finish(work, "source_absent", "missing_original", now)
            return
        try:
            raw = decode_archived_payload(
                revision.raw_payload_json,
                SourceIdentity(
                    SourcePlatform.TELEGRAM,
                    channel.external_id,
                    channel.display_name,
                    "public_channel",
                ),
            )
        except (TypeError, ValueError):
            await self.finish(work, "excluded", "unsupported_original", now)
            return
        if (
            raw.checksum != revision.raw_checksum
            or raw.text != revision.text_original
            or raw.external_message_id != message.external_message_id
        ):
            await self.finish(work, "source_absent", "original_evidence_mismatch", now)
            return
        extraction = extract_listing(raw)
        if extraction.listing is None:
            await self.finish(work, "excluded", "non_candidate", now)
            return
        await self.apply(work, now, extraction, raw.text, enabled=apply)

    async def apply(
        self,
        work: dict[str, object],
        now: datetime,
        extraction: ExtractionResult,
        source: str,
        *,
        enabled: bool,
    ) -> None:
        """Lock source, offer and origins; commit fields, lineage and progress together."""
        async with self._sessions.begin() as session:
            current = await session.get(SourceMessageRow, work["message_id"], with_for_update=True)
            if (
                current is None
                or current.current_revision_id != work["revision_id"]
                or current.deleted_at
            ):
                await self._finish(session, work, "excluded", "source_changed", now)
                return
            held = await session.scalar(
                text(
                    """
SELECT id FROM parser_replay_work WHERE id=:id AND claim_id=:claim AND
state='claimed' FOR UPDATE
"""
                ),
                {"id": work["id"], "claim": work["claim_id"]},
            )
            if held is None:
                return
            link = await session.scalar(
                select(OfferSourceRow)
                .where(
                    OfferSourceRow.source_message_revision_id == current.current_revision_id,
                    OfferSourceRow.relationship == "primary",
                )
                .with_for_update()
            )
            if link is None:
                await self._finish(session, work, "excluded", "no_current_offer_link", now)
                return
            offer = await session.get(OfferRow, link.offer_id, with_for_update=True)
            if offer is None or re.fullmatch(r"e2-v[0-9]+", offer.parser_version) is None:
                await self._finish(session, work, "excluded", "non_parser_offer", now)
                return
            if int(offer.parser_version.removeprefix("e2-v")) > int(
                PARSER_VERSION.removeprefix("e2-v")
            ):
                await self._finish(session, work, "excluded", "newer_parser", now)
                return
            origins = {
                row.field_name: row
                for row in (
                    await session.scalars(
                        select(OfferFieldOriginRow)
                        .where(OfferFieldOriginRow.offer_id == offer.id)
                        .with_for_update()
                    )
                ).all()
            }
            values = {
                name: scalar(getattr(offer, column)) for name, column in FIELD_COLUMNS.items()
            }
            protected = frozenset(
                name
                for name, origin in origins.items()
                if origin.origin != "parser"
                or origin.state != "active"
                or origin.value_fingerprint != value_fingerprint(values.get(name))
            )
            previous = link.extraction_json if isinstance(link.extraction_json, dict) else {}
            plan = plan_replay(extraction, source, previous, values, protected)
            if work["phase"] == "canary" or not enabled:
                await self._finish(session, work, "observed", "validated_canary", now)
                await session.execute(
                    text("UPDATE parser_replay_work SET canary_passed=true WHERE id=:id"),
                    {"id": work["id"]},
                )
                return
            await self._write(session, work, now, offer, link, plan, values, origins)
            await record_parse_evaluation(
                session,
                message_id=current.id,
                revision_id=current.current_revision_id,
                text=source,
                extraction=extraction,
            )
            changed = any(
                values[name] != scalar(field.value) for name, field in plan.fields.items()
            )
            state = (
                "protected_conflict" if plan.protected else ("updated" if changed else "unchanged")
            )
            await self._finish(
                session, work, state, "protected_fields" if plan.protected else None, now
            )

    async def _write(  # noqa: PLR0913, PLR0917 - one atomic transaction context
        self,
        session: AsyncSession,
        work: dict[str, object],
        now: datetime,
        offer: OfferRow,
        link: OfferSourceRow,
        plan: ReplayPlan,
        values: dict[str, object],
        origins: dict[str, OfferFieldOriginRow],
    ) -> None:
        for name, field in plan.fields.items():
            origin = origins.get(name)
            before_origin: dict[str, object] = (
                {
                    "origin": origin.origin,
                    "state": origin.state,
                    "parser_version": origin.parser_version,
                    "canonical_value": origin.canonical_value,
                    "source_revision_id": str(origin.source_revision_id)
                    if origin.source_revision_id
                    else None,
                    "value_fingerprint": origin.value_fingerprint,
                }
                if origin
                else {"origin": None}
            )
            old_document = link.extraction_json if isinstance(link.extraction_json, dict) else {}
            before_origin["extraction"] = old_document.get(field.group)
            before_origin["group"] = field.group
            before_origin["offer_parser_version"] = offer.parser_version
            await session.execute(
                text("""
INSERT INTO parser_replay_field_events(id,work_id,offer_id,field_name,before_value,
after_value,before_origin,parser_version,source_start,source_end) VALUES
(:id,:work,:offer,:name,CAST(:before AS jsonb),CAST(:after AS jsonb), CAST(:origin
AS jsonb),:parser,:start,:end) ON CONFLICT DO NOTHING
"""),
                {
                    "id": uuid4(),
                    "work": work["id"],
                    "offer": offer.id,
                    "name": name,
                    "before": json.dumps(values[name]),
                    "after": json.dumps(scalar(field.value)),
                    "origin": json.dumps(before_origin),
                    "parser": PARSER_VERSION,
                    "start": field.start,
                    "end": field.end,
                },
            )
            setattr(
                offer,
                FIELD_COLUMNS[name],
                Decimal(str(field.value)) if name.startswith("area_") else field.value,
            )
            if origin is None:
                origin = OfferFieldOriginRow(offer_id=offer.id, field_name=name)
                session.add(origin)
            origin.origin, origin.state = "parser", "active"
            origin.canonical_value = scalar(field.value)
            origin.value_fingerprint = value_fingerprint(scalar(field.value))
            origin.source_revision_id = link.source_message_revision_id
            origin.parser_version, origin.field_event_id, origin.updated_at = (
                PARSER_VERSION,
                None,
                now,
            )
        # Preserve the previous evidence for protected groups.
        previous = dict(link.extraction_json) if isinstance(link.extraction_json, dict) else {}
        for field in plan.fields.values():
            previous[field.group] = plan.extraction[field.group]
        link.extraction_json = previous
        offer.canonical_fingerprint = extraction_fingerprint(previous)
        if not plan.protected:
            offer.parser_version = PARSER_VERSION
        offer.updated_at = now

    async def _finish(
        self,
        session: AsyncSession,
        work: dict[str, object],
        state: str,
        reason: str | None,
        now: datetime,
    ) -> None:
        await session.execute(
            text("""
UPDATE parser_replay_work SET
state=:state,reason=:reason,claim_id=NULL,lease_until=NULL, updated_at=:now WHERE
id=:id AND claim_id=:claim AND state='claimed'
"""),
            {
                "id": work["id"],
                "claim": work["claim_id"],
                "state": state,
                "reason": reason,
                "now": now,
            },
        )

    async def finish(self, work: dict[str, object], state: str, reason: str, now: datetime) -> None:
        """Checkpoint noncanonical outcomes with a claim comparison."""
        async with self._sessions.begin() as session:
            await self._finish(session, work, state, reason, now)

    async def fail(self, work: dict[str, object], now: datetime) -> None:
        """Release local failures with bounded backoff; repeated failures become one exception."""
        async with self._sessions.begin() as session:
            await session.execute(
                text("""
UPDATE parser_replay_work SET state=CASE WHEN attempts>=3 THEN 'failed' ELSE
'deferred' END, reason='local_failure',claim_id=NULL,lease_until=NULL,
next_eligible_at=CAST(:now AS
timestamptz)+make_interval(secs=>least(3600,60*power(2,attempts-1))),updated_at=:now
WHERE id=:id AND claim_id=:claim AND state='claimed'
"""),
                {"id": work["id"], "claim": work["claim_id"], "now": now},
            )

    async def promote(self) -> None:
        """Expand after 25 read-only validations, or all available records in a small backlog."""
        async with self._sessions.begin() as session:
            await session.execute(
                text("""
UPDATE parser_replay_releases r SET phase='running' WHERE version=:release AND
phase='canary' AND NOT EXISTS(SELECT 1 FROM parser_replay_work w WHERE
w.release_version=r.version AND w.state='failed') AND ((SELECT count(*) FROM
parser_replay_work w WHERE w.release_version=r.version AND w.canary_passed)>=25 OR
(EXISTS(SELECT 1 FROM parser_replay_work w WHERE w.release_version=r.version AND
w.canary_passed) AND NOT EXISTS(SELECT 1 FROM parser_replay_work w WHERE
w.release_version=r.version AND w.state IN ('queued','claimed','deferred')) AND NOT
EXISTS(SELECT 1 FROM source_messages m WHERE NOT EXISTS(SELECT 1 FROM
parser_replay_work w WHERE w.release_version=r.version AND
w.revision_id=m.current_revision_id))))
"""),
                {"release": RELEASE},
            )

    async def counts(self) -> dict[str, int]:
        """Mutually exclusive record outcomes sum to the selected denominator."""
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    text(
                        """
SELECT state,count(*) FROM parser_replay_work WHERE release_version=:release GROUP
BY state
"""
                    ),
                    {"release": RELEASE},
                )
            ).all()
        return {str(state): int(count) for state, count in rows}
