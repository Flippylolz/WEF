"""PostgreSQL bounded discovery, fenced revalidation and atomic location receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select, text

from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.application.location_revalidation import (
    LEASE_SECONDS,
    ValidationClaim,
)
from wef_backend.features.ingestion.domain.geocoding import (
    normalize_geocode_query,
    normalize_location_display_name,
    review_geocode_result,
)
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.engine import RowMapping
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.geocoding import GeocodeResolution

_LOCATION = """
    SELECT l.id, l.display_address, l.normalized_address_hash, l.district, l.city,
           l.country_code, l.review_status, l.precision, l.confidence,
           l.selected_geocode_result_id, l.out_of_scope,
           ST_X(l.point) AS longitude, ST_Y(l.point) AS latitude,
           coalesce(s.selection_version, 0) AS selection_version, s.actor_type, s.actor_id
    FROM locations l LEFT JOIN LATERAL (
        SELECT selection_version, actor_type, actor_id FROM location_geocode_selections
        WHERE location_id = l.id ORDER BY selection_version DESC LIMIT 1
    ) s ON true
"""
DISCOVERY_LIMIT = 100
MAX_FAILURES = 5
CANARY_LIMIT = 25

_SOURCE_FIELDS = ("display_address", "normalized_address_hash", "district", "city", "country_code")


def _source(row: RowMapping) -> dict[str, Any]:
    return {key: row[key] for key in _SOURCE_FIELDS}


def _fingerprint(source: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def _protected(row: RowMapping) -> bool:
    return row["actor_type"] not in {None, "automatic_policy"} and not (
        row["actor_type"] == "operator" and row["actor_id"] == "ad-034-accept-pending-pins"
    )


def _snapshot(row: RowMapping) -> dict[str, Any]:
    keys = (
        "review_status",
        "precision",
        "longitude",
        "latitude",
        "out_of_scope",
        "selection_version",
    )
    return {
        **{key: row[key] for key in keys},
        "confidence": str(row["confidence"]),
        "result_id": str(row["selected_geocode_result_id"])
        if row["selected_geocode_result_id"]
        else None,
    }


@dataclass(frozen=True, slots=True)
class SQLAlchemyLocationValidationStore:
    """Keep network work outside locks and preserve all source/identity/owner state."""

    factory: async_sessionmaker[AsyncSession]

    async def discover(self, *, target: str, now: datetime) -> int:
        """Advance a version-specific durable keyset scan by at most 100 rows."""
        async with self.factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('location-validation-discovery'))")
            )
            created = await session.scalar(
                text(
                    "INSERT INTO location_validation_control(target) VALUES (:target) ON "
                    "CONFLICT DO NOTHING RETURNING target"
                ),
                {"target": target},
            )
            if created is not None:
                await session.execute(
                    text(
                        "UPDATE location_validation_control SET mode='off' WHERE target != :target"
                    ),
                    {"target": target},
                )
            control = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM location_validation_control WHERE target=:target FOR "
                            "UPDATE"
                        ),
                        {"target": target},
                    )
                )
                .mappings()
                .one()
            )
            if control["mode"] == "off":
                return 0
            rows = (
                (
                    await session.execute(
                        text(
                            _LOCATION + " WHERE (CAST(:cursor AS uuid) IS NULL OR l.id > :cursor) "
                            "ORDER BY l.id LIMIT 100"
                        ),
                        {"cursor": control["cursor_id"]},
                    )
                )
                .mappings()
                .all()
            )
            inserted = 0
            for row in rows:
                source = _source(row)
                work_id = uuid4()
                added = await session.scalar(
                    text("""
                    INSERT INTO location_validation_work
                        (id,location_id,source_fingerprint,target,source_json,selection_version,state,outcome)
                    VALUES (:id,:location,:fingerprint,:target,CAST(:source AS jsonb),
                            :version,:state,:outcome)
                    ON CONFLICT DO NOTHING RETURNING id
                """),
                    {
                        "id": work_id,
                        "location": row["id"],
                        "fingerprint": _fingerprint(source),
                        "target": target,
                        "source": json.dumps(source),
                        "version": row["selection_version"],
                        "state": "exception" if _protected(row) else "pending",
                        "outcome": "protected" if _protected(row) else None,
                    },
                )
                if added:
                    inserted += 1
                    if _protected(row):
                        await self._receipt(
                            session, work_id, "observe", _snapshot(row), _snapshot(row), "protected"
                        )
            await session.execute(
                text(
                    "UPDATE location_validation_control SET cursor_id=:cursor, "
                    "updated_at=:now WHERE target=:target"
                ),
                {
                    "cursor": rows[-1]["id"] if len(rows) == DISCOVERY_LIMIT else None,
                    "now": now,
                    "target": target,
                },
            )
            return inserted

    async def claim(self, *, target: str, now: datetime) -> ValidationClaim | None:
        """Lease one eligible snapshot with a monotonically increasing fence."""
        async with self.factory() as session, session.begin():
            control = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM location_validation_control WHERE target=:target FOR "
                            "UPDATE"
                        ),
                        {"target": target},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if control is None or control["mode"] == "off":
                return None
            mode = control["mode"]
            if control["next_eligible_at"] > now:
                return None
            if mode == "apply" and not control["discovery_ready"]:
                return None
            row = (
                (
                    await session.execute(
                        text("""
                SELECT * FROM location_validation_work
                WHERE target=:target AND (
                    (state IN ('pending','deferred') AND next_attempt_at <= :now)
                    OR (state='leased' AND lease_until <= :now)
                    OR (state='observed' AND :mode='apply')
                ) AND (:mode != 'apply' OR :verified OR location_id::text IN
                    (SELECT jsonb_array_elements_text(CAST(:canaries AS jsonb))))
                ORDER BY next_attempt_at,id LIMIT 1 FOR UPDATE SKIP LOCKED
            """),
                        {
                            "target": target,
                            "now": now,
                            "mode": mode,
                            "verified": control["canary_verified"],
                            "canaries": json.dumps(control["canary_ids"]),
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            await session.execute(
                text("""
                UPDATE location_validation_work SET state='leased', mode=:mode, fence=fence+1,
                    lease_until=:until, updated_at=:now WHERE id=:id
            """),
                {
                    "mode": mode,
                    "until": now + timedelta(seconds=LEASE_SECONDS),
                    "now": now,
                    "id": row["id"],
                },
            )
            source = row["source_json"]
            return ValidationClaim(
                row["id"],
                row["location_id"],
                row["source_fingerprint"],
                source["display_address"],
                source["district"],
                row["selection_version"],
                row["fence"] + 1,
                mode,
                row["failures"],
            )

    async def finish(
        self, claim: ValidationClaim, result: GeocodeResolution, *, now: datetime
    ) -> str:
        """Commit source-guarded selection and its receipt together or neither."""
        async with self.factory() as session, session.begin():
            work = await self._owned(session, claim, now)
            if work is None:
                return "stale_lease"
            # Lock the canonical row before evaluating the latest owner/source state.
            location = await session.scalar(
                select(LocationRow).where(LocationRow.id == claim.location_id).with_for_update()
            )
            if location is None:
                return "missing_location"
            row = (
                (
                    await session.execute(
                        text(_LOCATION + " WHERE l.id=:id"), {"id": claim.location_id}
                    )
                )
                .mappings()
                .one()
            )
            before = _snapshot(row)
            protected = _protected(row)
            stale = _fingerprint(_source(row)) != claim.fingerprint
            if protected or stale:
                outcome = "protected" if protected else "source_changed"
                await self._terminal(
                    session, claim, "exception" if protected else "terminal", outcome, now
                )
                await self._receipt(session, claim.work_id, claim.mode, before, before, outcome)
                return outcome
            if row["selection_version"] != claim.selection_version:
                await session.execute(
                    text("""
                    UPDATE location_validation_work SET state='pending', selection_version=:version,
                        lease_until=NULL, next_attempt_at=:now, updated_at=:now WHERE id=:id
                """),
                    {"version": row["selection_version"], "now": now, "id": claim.work_id},
                )
                return "selection_changed"
            after = before
            outcome = "validated" if result.decision.select_result else "unresolved"
            if claim.mode == "apply":
                await SQLAlchemyGeocodeStore(self.factory).select_in_session(
                    session,
                    location=location,
                    cached=result.cached,
                    decision=result.decision,
                    actor_type="automatic_policy",
                    actor_id=None,
                )
                location.display_name = normalize_location_display_name(
                    claim.address, district=claim.district
                )
                await session.flush()
                row = (
                    (
                        await session.execute(
                            text(_LOCATION + " WHERE l.id=:id"), {"id": claim.location_id}
                        )
                    )
                    .mappings()
                    .one()
                )
                after = {**_snapshot(row), "reason": result.decision.reason.value}
                outcome = "corrected" if result.decision.select_result else "unresolved"
            else:
                after = {
                    "review_status": result.decision.status.value,
                    "precision": result.cached.result.precision.value,
                    "reason": result.decision.reason.value,
                    "result_id": str(result.cached.result_id),
                }
            await self._receipt(session, claim.work_id, claim.mode, before, after, outcome)
            await self._terminal(
                session, claim, "terminal" if claim.mode == "apply" else "observed", outcome, now
            )
            await session.execute(
                text(
                    "UPDATE location_validation_work SET observation_result_id=:result, "
                    "failures=0 WHERE id=:id"
                ),
                {"result": result.cached.result_id, "id": claim.work_id},
            )
            return outcome

    async def renew(self, claim: ValidationClaim, *, now: datetime) -> bool:
        """Extend only a current, unexpired lease while provider I/O is still active."""
        async with self.factory() as session, session.begin():
            if await self._owned(session, claim, now) is None:
                return False
            await session.execute(
                text("UPDATE location_validation_work SET lease_until=:until WHERE id=:id"),
                {"until": now + timedelta(seconds=LEASE_SECONDS), "id": claim.work_id},
            )
            return True

    async def defer(
        self,
        claim: ValidationClaim,
        *,
        reason: str,
        next_attempt: datetime,
        failure: bool,
        now: datetime,
    ) -> None:
        """Persist quota pacing separately from the five-consecutive-failure bound."""
        async with self.factory() as session, session.begin():
            if await self._owned(session, claim, now) is None:
                return
            if reason == "quota":
                await session.execute(
                    text(
                        "UPDATE location_validation_control SET next_eligible_at=:next "
                        "WHERE target=(SELECT target FROM location_validation_work WHERE id=:id)"
                    ),
                    {"next": next_attempt, "id": claim.work_id},
                )
            failures = claim.failures + int(failure)
            await session.execute(
                text("""
                UPDATE location_validation_work SET state=:state, failures=:failures,
                    outcome=:reason, next_attempt_at=:next, lease_until=NULL, updated_at=:now
                WHERE id=:id
            """),
                {
                    "state": "exception" if failures >= MAX_FAILURES else "deferred",
                    "failures": failures,
                    "reason": reason,
                    "next": next_attempt,
                    "now": now,
                    "id": claim.work_id,
                },
            )

    async def _owned(
        self, session: AsyncSession, claim: ValidationClaim, now: datetime
    ) -> RowMapping | None:
        # Match claim/control/rollback lock order before taking the work-row lock.
        await session.execute(
            text(
                "SELECT target FROM location_validation_control WHERE target=("
                "SELECT target FROM location_validation_work WHERE id=:id) FOR UPDATE"
            ),
            {"id": claim.work_id},
        )
        return (
            (
                await session.execute(
                    text("""
            SELECT w.* FROM location_validation_work w
            JOIN location_validation_control c ON c.target=w.target
            WHERE w.id=:id AND w.state='leased' AND w.fence=:fence AND w.lease_until>:now
                AND c.mode=w.mode AND c.mode != 'off'
            FOR UPDATE OF w
        """),
                    {"id": claim.work_id, "fence": claim.fence, "now": now},
                )
            )
            .mappings()
            .one_or_none()
        )

    async def _receipt(  # noqa: PLR0913, PLR0917 - one immutable receipt envelope
        self,
        session: AsyncSession,
        work_id: UUID,
        mode: str,
        before: dict[str, Any],
        after: dict[str, Any],
        outcome: str,
    ) -> None:
        await session.execute(
            text("""
            INSERT INTO location_validation_receipts(id,work_id,mode,before_json,after_json,outcome)
            VALUES (:id,:work,:mode,CAST(:before AS jsonb),CAST(:after AS jsonb),:outcome)
            ON CONFLICT DO NOTHING
        """),
            {
                "id": uuid4(),
                "work": work_id,
                "mode": mode,
                "before": json.dumps(before),
                "after": json.dumps(after),
                "outcome": outcome,
            },
        )

    async def _terminal(
        self, session: AsyncSession, claim: ValidationClaim, state: str, outcome: str, now: datetime
    ) -> None:
        await session.execute(
            text("""
            UPDATE location_validation_work SET state=:state, outcome=:outcome,
                lease_until=NULL, updated_at=:now WHERE id=:id
        """),
            {"id": claim.work_id, "state": state, "outcome": outcome, "now": now},
        )

    async def _advance_canary(self, session: AsyncSession, control: RowMapping) -> None:
        if control["mode"] != "apply" or control["canary_verified"] or not control["canary_ids"]:
            return
        outcomes = (
            await session.execute(
                text("""
            SELECT DISTINCT ON (location_id) state,outcome
            FROM location_validation_work WHERE target=:target
                AND location_id::text IN (SELECT jsonb_array_elements_text(CAST(:ids AS jsonb)))
                ORDER BY location_id,created_at DESC
        """),
                {"target": control["target"], "ids": json.dumps(control["canary_ids"])},
            )
        ).all()
        if len(outcomes) == len(control["canary_ids"]) and all(
            (row.state == "terminal" and row.outcome in {"corrected", "unresolved"})
            or (row.state == "exception" and row.outcome == "protected")
            for row in outcomes
        ):
            await session.execute(
                text(
                    "UPDATE location_validation_control SET canary_verified=true WHERE "
                    "target=:target"
                ),
                {"target": control["target"]},
            )

    async def verify_canary(self, *, target: str) -> None:
        """Record operator verification of real geometry/discovery after canary application."""
        async with self.factory() as session, session.begin():
            control = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM location_validation_control "
                            "WHERE target=:target FOR UPDATE"
                        ),
                        {"target": target},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if control is None or control["mode"] != "apply":
                message = "canary verification requires active application"
                raise ValueError(message)
            await self._advance_canary(session, control)
            verified = await session.scalar(
                text(
                    "SELECT canary_verified FROM location_validation_control WHERE target=:target"
                ),
                {"target": target},
            )
            if not verified:
                message = "all canaries must have completed application before verification"
                raise ValueError(message)
            await session.execute(
                text(
                    "UPDATE location_validation_control SET operator_actions=operator_actions+1 "
                    "WHERE target=:target"
                ),
                {"target": target},
            )

    async def control(
        self,
        *,
        target: str,
        mode: str,
        canary_ids: tuple[UUID, ...] = (),
        discovery_ready: bool = False,
    ) -> None:
        """Apply explicit rollout readiness once; ordinary records remain automatic."""
        if mode not in {"off", "observe", "apply"}:
            message = "unknown validation mode"
            raise ValueError(message)
        if mode == "apply" and (not discovery_ready or not 1 <= len(canary_ids) <= CANARY_LIMIT):
            message = "application requires verified discovery and 1-25 observed canary locations"
            raise ValueError(message)
        async with self.factory() as session, session.begin():
            if mode == "apply":
                observed = await session.scalar(
                    text("""
                    SELECT count(DISTINCT location_id) FROM location_validation_work
                    WHERE target=:target AND (state IN ('observed','terminal')
                        OR (state='exception' AND outcome='protected'))
                        AND location_id::text IN
                        (SELECT jsonb_array_elements_text(CAST(:ids AS jsonb)))
                """),
                    {"target": target, "ids": json.dumps([str(item) for item in canary_ids])},
                )
                if observed != len(canary_ids):
                    message = "every canary must have a completed observation"
                    raise ValueError(message)
            await session.execute(
                text("""
                INSERT INTO location_validation_control
                    (target,mode,discovery_ready,canary_ids,operator_actions)
                VALUES (:target,:mode,:ready,CAST(:ids AS jsonb),1) ON CONFLICT(target) DO UPDATE
                SET mode=excluded.mode,
                    discovery_ready=CASE WHEN excluded.mode='apply' THEN excluded.discovery_ready
                        ELSE location_validation_control.discovery_ready END,
                    canary_ids=CASE WHEN excluded.mode='apply' THEN excluded.canary_ids
                        ELSE location_validation_control.canary_ids END,
                    canary_verified=false, updated_at=now(),
                    operator_actions=location_validation_control.operator_actions+1
            """),
                {
                    "target": target,
                    "mode": mode,
                    "ready": discovery_ready,
                    "ids": json.dumps([str(item) for item in canary_ids]),
                },
            )

            await session.execute(
                text(
                    "UPDATE location_validation_work SET state='deferred', fence=fence+1, "
                    "lease_until=NULL, next_attempt_at=now() "
                    "WHERE target=:target AND state='leased'"
                ),
                {"target": target},
            )

    async def rollback(self, *, target: str) -> dict[str, int]:
        """Pause work and restore at most 25 unchanged, still-valid automatic predecessors."""
        await self.control(target=target, mode="off")
        counts: dict[str, int] = {}
        async with self.factory() as session, session.begin():
            control = await session.scalar(
                text(
                    "SELECT mode FROM location_validation_control WHERE target=:target FOR UPDATE"
                ),
                {"target": target},
            )
            if control != "off":
                message = "rollback requires paused validation"
                raise ValueError(message)
            receipts = (
                (
                    await session.execute(
                        text("""
                SELECT r.work_id,r.before_json,r.after_json,w.location_id,w.source_fingerprint
                FROM location_validation_receipts r
                JOIN location_validation_work w ON w.id=r.work_id
                WHERE w.target=:target AND r.mode='apply' AND NOT EXISTS (
                    SELECT 1 FROM location_validation_receipts done
                    WHERE done.work_id=w.id AND done.mode='rollback')
                ORDER BY r.created_at DESC,r.id LIMIT 25
            """),
                        {"target": target},
                    )
                )
                .mappings()
                .all()
            )
            for receipt in receipts:
                location = await session.scalar(
                    select(LocationRow)
                    .where(LocationRow.id == receipt["location_id"])
                    .with_for_update()
                )
                if location is None:
                    continue
                row = (
                    (
                        await session.execute(
                            text(_LOCATION + " WHERE l.id=:id"), {"id": location.id}
                        )
                    )
                    .mappings()
                    .one()
                )
                before = _snapshot(row)
                outcome = "retained_quarantine"
                unchanged = (
                    not _protected(row)
                    and _fingerprint(_source(row)) == receipt["source_fingerprint"]
                    and all(
                        before.get(key) == value
                        for key, value in receipt["after_json"].items()
                        if key != "reason"
                    )
                )
                predecessor = receipt["before_json"].get("result_id")
                after = before
                if not unchanged:
                    outcome = "edited_or_protected"
                elif predecessor:
                    geocodes = SQLAlchemyGeocodeStore(self.factory)
                    cached = await geocodes.result_in_session(session, UUID(predecessor))
                    if cached is not None:
                        decision = review_geocode_result(
                            cached.result,
                            query=normalize_geocode_query(
                                row["display_address"], district=row["district"]
                            ),
                        )
                        if decision.select_result:
                            await geocodes.select_in_session(
                                session,
                                location=location,
                                cached=cached,
                                decision=decision,
                                actor_type="automatic_policy",
                                actor_id="e26-guarded-rollback",
                            )
                            await session.flush()
                            after = _snapshot(
                                (
                                    await session.execute(
                                        text(_LOCATION + " WHERE l.id=:id"), {"id": location.id}
                                    )
                                )
                                .mappings()
                                .one()
                            )
                            outcome = "restored_valid_predecessor"
                await self._receipt(session, receipt["work_id"], "rollback", before, after, outcome)
                counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    async def status(self, *, target: str) -> dict[str, Any]:
        """Return aggregate progress and transition counts without source addresses."""
        async with self.factory() as session:
            control = (
                (
                    await session.execute(
                        text(
                            "SELECT mode,canary_verified,next_eligible_at,operator_actions "
                            "FROM location_validation_control WHERE "
                            "target=:target"
                        ),
                        {"target": target},
                    )
                )
                .mappings()
                .one_or_none()
            )
            states = (
                (
                    await session.execute(
                        text(
                            "SELECT state,outcome,count(*) AS count FROM location_validation_work "
                            "WHERE target=:target GROUP BY state,outcome"
                        ),
                        {"target": target},
                    )
                )
                .mappings()
                .all()
            )
            transitions = (
                (
                    await session.execute(
                        text("""
                SELECT r.mode,r.before_json->>'precision' AS before_precision,
                    r.after_json->>'precision' AS after_precision,r.outcome,count(*) AS count
                FROM location_validation_receipts r
                JOIN location_validation_work w ON w.id=r.work_id
                WHERE w.target=:target GROUP BY r.mode,before_precision,after_precision,r.outcome
            """),
                        {"target": target},
                    )
                )
                .mappings()
                .all()
            )
            populations = (
                (
                    await session.execute(
                        text("""
                    WITH affected AS (
                        SELECT DISTINCT location_id FROM location_validation_work
                        WHERE target=:target
                    )
                    SELECT (SELECT count(*) FROM affected) AS unique_locations,
                        (SELECT count(*) FROM offers o
                            JOIN affected a ON a.location_id=o.location_id)
                            AS existing_offers,
                        (SELECT count(*) FROM offers o
                            JOIN affected a ON a.location_id=o.location_id
                            WHERE o.visibility='visible') AS visible_offers,
                        (SELECT count(*) FROM favorite_locations f
                            JOIN affected a ON a.location_id=f.location_id) AS existing_favorites
                """),
                        {"target": target},
                    )
                )
                .mappings()
                .one()
            )
            reasons = (
                (
                    await session.execute(
                        text("""
                    SELECT r.mode,r.after_json->>'reason' AS reason,count(*) AS count
                    FROM location_validation_receipts r
                    JOIN location_validation_work w ON w.id=r.work_id
                    WHERE w.target=:target GROUP BY r.mode,reason
                """),
                        {"target": target},
                    )
                )
                .mappings()
                .all()
            )
            return {
                "target": target,
                "control": {
                    **dict(control),
                    "next_eligible_at": control["next_eligible_at"].isoformat(),
                }
                if control
                else None,
                "states": [dict(row) for row in states],
                "transitions": [dict(row) for row in transitions],
                "population": dict(populations),
                "reasons": [dict(row) for row in reasons],
            }
