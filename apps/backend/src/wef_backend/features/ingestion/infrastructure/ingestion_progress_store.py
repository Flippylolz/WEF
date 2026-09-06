"""Durable minute observations, deadline classification and incident episodes."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import text

from wef_backend.features.ingestion.application.archive_retry import RETRY_POLICY_VERSION
from wef_backend.features.ingestion.application.media_recovery import MEDIA_RECOVERY_POLICY
from wef_backend.features.ingestion.domain.ingestion_progress import (
    MAX_SAMPLE_GAP,
    SAMPLE_SECONDS,
    AcceptanceSample,
    ProgressCheckpoint,
    ProgressSnapshot,
    assess_acceptance,
    classify_progress,
)
from wef_backend.features.ingestion.infrastructure import ingestion_progress_queries as queries

MIN_WINDOW_SAMPLES = 16
WINDOW_SECONDS = 900
RECOVERY_SAMPLES = 2

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _json(value: object) -> str:
    return json.dumps(value, default=lambda item: item.isoformat())


def _checkpoint(payload: dict[str, Any]) -> ProgressCheckpoint:
    return ProgressCheckpoint(
        token=payload["token"],
        sampled_at=datetime.fromisoformat(payload["sampled_at"]),
        progressed_at=datetime.fromisoformat(payload["progressed_at"]),
        stagnant_samples=payload["stagnant_samples"],
        healthy_samples=payload["healthy_samples"],
        status=payload["status"],
        reason=payload["reason"],
        terminal_replays=payload.get("terminal_replays", 0),
        replay_samples=payload.get("replay_samples", 0),
    )


class SQLAlchemyIngestionProgressStore:
    """Serialize monitors only; never retain a lock on canonical or queue records."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        channel: str,
        *,
        release_sha: str | None = None,
        traversal_interval_seconds: float = 60,
    ) -> None:
        """Scope all observations and incidents to the selected channel."""
        self.factory = factory
        self.channel = channel
        self.release_sha = release_sha
        self.traversal_interval_seconds = traversal_interval_seconds

    async def sample(self, now: datetime | None = None) -> list[dict[str, str]]:
        """Persist one coherent snapshot per minute and emit only incident transitions."""
        started = time.monotonic()
        current = now or datetime.now(UTC)
        async with self.factory() as session, session.begin():
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            await session.execute(text("SET LOCAL statement_timeout=5000"))
            await session.execute(text("SET LOCAL lock_timeout=1000"))
            await session.execute(
                text(
                    "INSERT INTO ingestion_progress_controls(channel) VALUES (:channel) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"channel": self.channel},
            )
            control = (
                await session.execute(
                    text(
                        "SELECT enabled FROM ingestion_progress_controls WHERE "
                        "channel=:channel FOR UPDATE"
                    ),
                    {"channel": self.channel},
                )
            ).one()
            last = await session.scalar(
                text(
                    "SELECT max(sampled_at) FROM ingestion_progress_samples WHERE channel=:channel"
                ),
                {"channel": self.channel},
            )
            if last is not None and (current - last).total_seconds() < SAMPLE_SECONDS:
                return []
            snapshots, evidence = await self._snapshots(session, current)
            stages: dict[str, object] = {}
            events: list[dict[str, str]] = []
            for snapshot in snapshots:
                params = {"channel": self.channel, "stage": snapshot.stage}
                previous = await session.scalar(
                    text(
                        "SELECT payload FROM ingestion_progress_checkpoints WHERE "
                        "channel=:channel AND stage=:stage"
                    ),
                    params,
                )
                result = classify_progress(
                    snapshot, _checkpoint(previous) if previous else None, current
                )
                await session.execute(
                    text(
                        "INSERT INTO "
                        "ingestion_progress_checkpoints(channel,stage,payload) VALUES "
                        "(:channel,:stage,CAST(:payload AS jsonb)) ON "
                        "CONFLICT(channel,stage) DO UPDATE SET payload=excluded.payload"
                    ),
                    {**params, "payload": _json(asdict(result))},
                )
                stages[snapshot.stage] = {
                    **asdict(snapshot),
                    **asdict(result),
                    "total": snapshot.total,
                }
                if control.enabled:
                    events.extend(await self._incident(session, snapshot.stage, result))
            payload = {
                "stages": stages,
                "evidence": evidence,
                "incidents_enabled": control.enabled,
                "release_sha": self.release_sha,
                "query_seconds": round(time.monotonic() - started, 3),
            }
            await session.execute(
                text(
                    "INSERT INTO ingestion_progress_samples(channel,sampled_at,payload) "
                    "VALUES (:channel,:now,CAST(:payload AS jsonb))"
                ),
                {"channel": self.channel, "now": current, "payload": _json(payload)},
            )
            await session.execute(
                text(
                    "DELETE FROM ingestion_progress_samples WHERE channel=:channel AND "
                    "sampled_at<:cutoff"
                ),
                {"channel": self.channel, "cutoff": current - timedelta(hours=48)},
            )
            return events

    async def _snapshots(
        self, session: AsyncSession, now: datetime
    ) -> tuple[list[ProgressSnapshot], dict[str, object]]:
        params = {
            "channel": self.channel,
            "now": now,
            "archive_policy": RETRY_POLICY_VERSION,
            "media_policy": MEDIA_RECOVERY_POLICY,
        }
        control = dict(
            (await session.execute(text(queries.CONTROL), params)).mappings().first() or {}
        )
        snapshots = []
        for stage, query in (
            ("archive", queries.ARCHIVE),
            ("media", queries.MEDIA),
            ("media_discovery", queries.DISCOVERY),
        ):
            row = dict((await session.execute(text(query), params)).mappings().one())
            if stage == "media_discovery":
                row["eligible"] += int(control.get("undiscovered_sources") or 0)
                if control.get("oldest_source") is not None:
                    row["oldest_due"] = min(
                        row["oldest_due"] or control["oldest_source"], control["oldest_source"]
                    )
            terminal = int(row["terminal"])
            quarantined = int(row.get("quarantined", 0))
            phase = control.get("archive_phase" if stage == "archive" else "media_phase")
            pause_reason = control.get("archive_reason" if stage == "archive" else "media_reason")
            if (
                stage == "media"
                and control.get("media_wait") is not None
                and control["media_wait"] > now
            ):
                row["delayed"] += row["eligible"]
                row["eligible"] = 0
                row["oldest_due"] = None
            snapshots.append(
                ProgressSnapshot(
                    stage=stage,
                    token=f"{terminal}:{quarantined}",
                    **row,
                    paused=phase in {"paused", "canary_ready"},
                    actionable_pause=phase == "paused"
                    and pause_reason not in {None, "operator_pause"},
                    wait_until=control.get("media_wait") if stage == "media" else None,
                )
            )
        scheduled = control.get("last_polled_at")
        if scheduled is not None:
            scheduled += timedelta(seconds=self.traversal_interval_seconds)
        source_wait = control.get("traversal_wait")
        deadlines = [value for value in (scheduled, source_wait) if value is not None]
        traversal_due = max(deadlines) if deadlines else None
        has_work = bool(control.get("known_head"))
        waiting = traversal_due is not None and traversal_due > now
        snapshots.append(
            ProgressSnapshot(
                stage="traversal",
                token=f"{control.get('polled_through_id')}:{control.get('sweep_after_id')}:{control.get('last_polled_at')}:{control.get('last_sweep_at')}",
                eligible=int(has_work and not waiting),
                delayed=int(has_work and waiting),
                oldest_due=traversal_due,
                wait_until=traversal_due,
            )
        )
        evidence: dict[str, object] = dict(
            (await session.execute(text(queries.EVIDENCE), params)).mappings().one()
        )
        counters = (
            (
                await session.execute(
                    text(
                        "SELECT name,value,since FROM ingestion_observation_counters "
                        "WHERE channel=:channel"
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        evidence["observations_since_instrumentation"] = {
            row["name"]: {"value": row["value"], "since": row["since"]} for row in counters
        }
        evidence["legacy_fetched"] = None
        replays = next(
            (int(row["value"]) for row in counters if row["name"] == "terminal_replays"), 0
        )
        snapshots = [
            replace(snapshot, terminal_replays=replays) if snapshot.stage == "archive" else snapshot
            for snapshot in snapshots
        ]
        return snapshots, evidence

    async def _incident(
        self, session: AsyncSession, stage: str, result: ProgressCheckpoint
    ) -> list[dict[str, str]]:
        params = {"channel": self.channel, "stage": stage, "now": result.sampled_at}
        existing = (
            await session.execute(
                text(
                    "SELECT id,reason FROM ingestion_progress_incidents WHERE "
                    "channel=:channel AND stage=:stage AND closed_at IS NULL"
                ),
                params,
            )
        ).first()
        events = []
        if existing is not None and (
            result.healthy_samples >= RECOVERY_SAMPLES
            or (result.reason is not None and result.reason != existing.reason)
        ):
            await session.execute(
                text("UPDATE ingestion_progress_incidents SET closed_at=:now WHERE id=:id"),
                {**params, "id": existing.id},
            )
            events.append({"stage": stage, "transition": "closed", "reason": existing.reason})
            existing = None
        if result.reason is not None and existing is None:
            await session.execute(
                text(
                    "INSERT INTO "
                    "ingestion_progress_incidents(id,channel,stage,reason,opened_at) "
                    "VALUES (:id,:channel,:stage,:reason,:now)"
                ),
                {**params, "id": uuid4(), "reason": result.reason},
            )
            events.append({"stage": stage, "transition": "opened", "reason": result.reason})
        return events

    async def status(self) -> dict[str, Any]:
        """Return private aggregates and durable active incidents, not source identities."""
        async with self.factory() as session:
            await session.execute(text("SET LOCAL statement_timeout=5000"))
            row = (
                await session.execute(
                    text(
                        "SELECT sampled_at,payload FROM ingestion_progress_samples WHERE "
                        "channel=:channel ORDER BY sampled_at DESC LIMIT 1"
                    ),
                    {"channel": self.channel},
                )
            ).first()
            incidents = (
                (
                    await session.execute(
                        text(
                            "SELECT stage,reason,opened_at FROM "
                            "ingestion_progress_incidents WHERE channel=:channel AND "
                            "closed_at IS NULL"
                        ),
                        {"channel": self.channel},
                    )
                )
                .mappings()
                .all()
            )
            enabled = await session.scalar(
                text("SELECT enabled FROM ingestion_progress_controls WHERE channel=:channel"),
                {"channel": self.channel},
            )
            enabled_at = await session.scalar(
                text("SELECT enabled_at FROM ingestion_progress_controls WHERE channel=:channel"),
                {"channel": self.channel},
            )
            samples = (
                (
                    await session.execute(
                        text(
                            "SELECT sampled_at,payload FROM ingestion_progress_samples "
                            "WHERE channel=:channel AND sampled_at>=:start ORDER BY "
                            "sampled_at"
                        ),
                        {"channel": self.channel, "start": enabled_at},
                    )
                ).all()
                if enabled_at
                else []
            )
            acceptance = []
            for sample in samples:
                stages = sample.payload["stages"].values()
                observations = sample.payload["evidence"]["observations_since_instrumentation"]
                acceptance.append(
                    AcceptanceSample(
                        sample.sampled_at,
                        all(
                            stage["status"] not in {"stalled", "observing", "paused"}
                            and stage["reason"] is None
                            for stage in stages
                        ),
                        sum(stage["eligible"] for stage in stages),
                        int(observations.get("terminal_replays", {}).get("value", 0)),
                        sample.payload.get("release_sha"),
                    )
                )
            fresh = (
                row is not None
                and 0 <= (datetime.now(UTC) - row.sampled_at).total_seconds() <= MAX_SAMPLE_GAP
            )
            return {
                "acceptance": assess_acceptance(acceptance, datetime.now(UTC))
                if enabled
                else {"status": "observation_only"},
                "sampling_fresh": fresh,
                "progress_healthy": fresh
                and all(
                    stage["status"] not in {"stalled", "observing"} and stage["reason"] is None
                    for stage in row.payload["stages"].values()
                )
                if row
                else False,
                "sampled_at": row.sampled_at.isoformat() if row else None,
                "snapshot": row.payload if row else None,
                "incidents_enabled": bool(enabled),
                "incidents": [
                    {
                        "stage": r["stage"],
                        "reason": r["reason"],
                        "opened_at": r["opened_at"].isoformat(),
                    }
                    for r in incidents
                ],
            }

    async def control(self, *, enabled: bool) -> None:
        """Enable after a contiguous observation window; disable without erasing evidence."""
        now = datetime.now(UTC)
        async with self.factory() as session, session.begin():
            await session.execute(text("SET LOCAL statement_timeout=5000"))
            if enabled:
                rows = (
                    await session.execute(
                        text(
                            "SELECT sampled_at,payload FROM ingestion_progress_samples "
                            "WHERE channel=:channel AND sampled_at>=:cutoff ORDER BY "
                            "sampled_at"
                        ),
                        {"channel": self.channel, "cutoff": now - timedelta(minutes=18)},
                    )
                ).all()
                valid = (
                    len(rows) >= MIN_WINDOW_SAMPLES
                    and (rows[-1].sampled_at - rows[0].sampled_at).total_seconds() >= WINDOW_SECONDS
                )
                valid = valid and 0 <= (now - rows[-1].sampled_at).total_seconds() <= MAX_SAMPLE_GAP
                valid = valid and all(
                    0 < (b.sampled_at - a.sampled_at).total_seconds() <= MAX_SAMPLE_GAP
                    for a, b in pairwise(rows)
                )
                valid = valid and all(
                    s["status"] not in {"stalled", "observing"} and s["reason"] is None
                    for row in rows[1:]
                    for s in row.payload["stages"].values()
                )
                if not valid:
                    message = "a contiguous healthy 15-minute observation is required"
                    raise ValueError(message)
            await session.execute(
                text(
                    "INSERT INTO ingestion_progress_controls(channel,enabled,enabled_at) VALUES "
                    "(:channel,:enabled,CASE WHEN :enabled THEN now() ELSE NULL END) "
                    "ON CONFLICT(channel) DO UPDATE SET enabled=excluded.enabled, "
                    "enabled_at=CASE WHEN NOT excluded.enabled THEN NULL "
                    "WHEN ingestion_progress_controls.enabled THEN "
                    "ingestion_progress_controls.enabled_at "
                    "ELSE now() END"
                ),
                {"channel": self.channel, "enabled": enabled},
            )
