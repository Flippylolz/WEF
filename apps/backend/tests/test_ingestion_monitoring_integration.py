"""Real transaction proofs for durable progress, accounting and incident lifecycle."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.test_archive_recovery_integration import (
    RecoveryDB,
    payload,
)
from tests.test_archive_recovery_integration import (
    recovery_db as _recovery_db,
)
from wef_backend.features.ingestion.infrastructure.ingestion_observation_counters import (
    record_observation,
)
from wef_backend.features.ingestion.infrastructure.ingestion_progress_store import (
    SQLAlchemyIngestionProgressStore,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)

recovery_db = _recovery_db
pytestmark = pytest.mark.integration


@pytest.fixture
async def progress(recovery_db: RecoveryDB) -> SQLAlchemyIngestionProgressStore:
    async with recovery_db.factory() as session, session.begin():
        await session.execute(
            text(
                "TRUNCATE ingestion_progress_controls, ingestion_progress_checkpoints, "
                "ingestion_progress_samples, ingestion_progress_incidents, "
                "ingestion_observation_counters"
            )
        )
    return SQLAlchemyIngestionProgressStore(recovery_db.factory, recovery_db.identity.channel_id)


async def test_observations_deduplicate_identity_and_rollback(
    recovery_db: RecoveryDB, progress: SQLAlchemyIngestionProgressStore
) -> None:
    db = recovery_db
    first = await db.land(payload(101))
    assert await db.land(payload(101)) == first
    async with db.factory() as session, session.begin():
        await record_observation(session, db.identity.channel_id, "fetched_archivable")
        await session.rollback()
    await progress.sample()
    status = await progress.status()
    evidence = status["snapshot"]["evidence"]
    assert evidence["observations_since_instrumentation"]["fetched_archivable"]["value"] == 2
    assert evidence["legacy_fetched"] is None
    assert status["snapshot"]["stages"]["archive"]["total"] == 1


async def test_incident_deduplicates_and_closes_after_recovery(
    recovery_db: RecoveryDB, progress: SQLAlchemyIngestionProgressStore
) -> None:
    db = recovery_db
    event = await db.land(payload(101))
    now = datetime.now(UTC)
    # Test incident classification independently of the separately tested activation gate.
    async with db.factory() as session, session.begin():
        await session.execute(
            text("INSERT INTO ingestion_progress_controls(channel,enabled) VALUES (:channel,true)"),
            {"channel": db.identity.channel_id},
        )
    events = []
    for minute in range(8):
        events.extend(await progress.sample(now + timedelta(minutes=minute)))
    assert events == [
        {"stage": "archive", "transition": "opened", "reason": "eligible_without_unique_progress"}
    ]
    assert len((await progress.status())["incidents"]) == 1
    await db.archive.mark_attempt(event.id, outcome="processed", completed_at=now)
    assert await progress.sample(now + timedelta(minutes=8)) == []
    reopened = SQLAlchemyIngestionProgressStore(db.factory, db.identity.channel_id)
    closed = await reopened.sample(now + timedelta(minutes=9))
    assert closed == [
        {"stage": "archive", "transition": "closed", "reason": "eligible_without_unique_progress"}
    ]
    assert (await reopened.status())["incidents"] == []
    assert not await db.archive.mark_attempt(event.id, outcome="processed", completed_at=now)
    await progress.sample(now + timedelta(minutes=10))
    assert (await progress.status())["snapshot"]["evidence"]["observations_since_instrumentation"][
        "terminal_replays"
    ]["value"] == 1


async def test_observation_gate_then_enable_and_disable(
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    with pytest.raises(ValueError, match="15-minute"):
        await progress.control(enabled=True)
    now = datetime.now(UTC) - timedelta(minutes=16)
    for minute in range(17):
        await progress.sample(now + timedelta(minutes=minute))
    await progress.control(enabled=True)
    assert (await progress.status())["incidents_enabled"]
    await progress.control(enabled=False)
    assert not (await progress.status())["incidents_enabled"]


async def test_gap_cannot_pass_activation(progress: SQLAlchemyIngestionProgressStore) -> None:
    now = datetime.now(UTC) - timedelta(minutes=17)
    for minute in range(18):
        if minute != 8:
            await progress.sample(now + timedelta(minutes=minute))
    # A two-minute interval is the maximum tolerated cadence; exceed it explicitly.
    async with progress.factory() as session, session.begin():
        await session.execute(
            text(
                "DELETE FROM ingestion_progress_samples WHERE channel=:channel AND sampled_at=:at"
            ),
            {"channel": progress.channel, "at": now + timedelta(minutes=9)},
        )
    with pytest.raises(ValueError, match="15-minute"):
        await progress.control(enabled=True)


async def test_competing_monitors_and_minute_deduplication(
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    now = datetime.now(UTC)
    await progress.sample(now)
    outcomes = await asyncio.gather(
        progress.sample(now + timedelta(minutes=1)),
        progress.sample(now + timedelta(minutes=1)),
        return_exceptions=True,
    )
    assert all(value == [] or isinstance(value, DBAPIError) for value in outcomes)
    async with progress.factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM ingestion_progress_samples")) == 2
    assert await progress.sample(now) == []


async def test_retention_and_missing_status(progress: SQLAlchemyIngestionProgressStore) -> None:
    assert (await progress.status())["snapshot"] is None
    now = datetime.now(UTC)
    await progress.sample(now - timedelta(hours=49))
    await progress.sample(now)
    async with progress.factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM ingestion_progress_samples")) == 1


async def test_discovery_has_no_double_count_and_reports_reuse_separately(
    recovery_db: RecoveryDB, progress: SQLAlchemyIngestionProgressStore
) -> None:
    db = recovery_db
    await db.canonical(payload(101))
    await progress.sample()
    snapshot = (await progress.status())["snapshot"]
    assert snapshot["stages"]["media_discovery"]["eligible"] == 1
    media = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await media.discover()
    await progress.sample(datetime.now(UTC) + timedelta(minutes=1))
    snapshot = (await progress.status())["snapshot"]
    assert snapshot["stages"]["media_discovery"]["eligible"] == 0
    assert snapshot["evidence"]["successful_variant_attempts"] == 0
    assert snapshot["evidence"]["public_associations"] == 0


async def test_provider_pause_preserves_archive_progress(
    recovery_db: RecoveryDB, progress: SQLAlchemyIngestionProgressStore
) -> None:
    db = recovery_db
    await db.canonical(payload(101))
    media = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await media.discover()
    await media.pause("OSError")
    now = datetime.now(UTC)
    await progress.sample(now)
    event = await db.land(payload(102))
    await db.archive.mark_attempt(event.id, outcome="processed", completed_at=now)
    await progress.sample(now + timedelta(minutes=1))
    stages = (await progress.status())["snapshot"]["stages"]
    assert stages["media"]["reason"] == "systemic_pause"
    assert stages["archive"]["terminal"] == 1


async def test_receipted_exhausted_original_is_still_eligible(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    db = recovery_db
    event = await db.land(payload(101))
    await db.processor()(record=event, identity=db.identity)
    async with db.factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE telegram_raw_events SET "
                "data_failure_count=5,next_attempt_at=now()+interval '1 day' WHERE id=:id"
            ),
            {"id": event.id},
        )
    await progress.sample()
    stages = (await progress.status())["snapshot"]["stages"]
    assert stages["archive"]["eligible"] == 1
    assert stages["archive"]["quarantined"] == 0
    assert stages["archive"]["delayed"] == 0


async def test_policy_reevaluation_is_eligible_not_hidden_quarantine(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    db = recovery_db
    event = await db.land(payload(101))
    async with db.factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE telegram_raw_events SET "
                "data_failure_count=5,retry_policy_version='old',next_attempt_at=now()+interval "
                "'1 day' WHERE id=:id"
            ),
            {"id": event.id},
        )
    await progress.sample()
    stage = (await progress.status())["snapshot"]["stages"]["archive"]
    assert stage["total"] == stage["eligible"] == 1


async def test_query_timeout_does_not_block_landing(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.ingestion_progress_queries.ARCHIVE",
        "SELECT pg_sleep(6)",
    )
    sampling = asyncio.create_task(progress.sample())
    await asyncio.sleep(0.1)
    event = await asyncio.wait_for(recovery_db.land(payload(101)), timeout=2)
    assert event.id is not None
    with pytest.raises(DBAPIError):
        await sampling
    assert (await progress.status())["snapshot"] is None


async def test_configured_poll_interval_is_waiting_not_stalled(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    db = recovery_db
    await db.canonical(payload(101))
    now = datetime.now(UTC)
    async with db.factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO "
                "telegram_channel_progress(source_channel_id,applied_high_water_id,"
                "polled_through_id,last_polled_at) "
                "SELECT id,101,101,:now FROM source_channels WHERE external_id=:channel "
                "ON CONFLICT(source_channel_id) DO UPDATE SET "
                "last_polled_at=excluded.last_polled_at"
            ),
            {"channel": progress.channel, "now": now},
        )
    monitor = SQLAlchemyIngestionProgressStore(
        db.factory, progress.channel, traversal_interval_seconds=3600
    )
    for minute in range(7):
        await monitor.sample(now + timedelta(minutes=minute))
    stage = (await monitor.status())["snapshot"]["stages"]["traversal"]
    assert stage["status"] == "waiting"
    assert stage["eligible"] == 0
    assert stage["delayed"] == 1
