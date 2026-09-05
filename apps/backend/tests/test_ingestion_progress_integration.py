"""Durable cursor, retry fairness and source-observation recovery proofs."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from tests.test_archive_recovery_integration import NOW, RecoveryDB
from tests.test_archive_recovery_integration import payload as historical_payload
from tests.test_archive_recovery_integration import recovery_db as _recovery_db
from wef_backend.features.ingestion.application.archive_retry import (
    RETRY_POLICY_VERSION,
    ArchiveFailure,
    classify_archive_failure,
    retry_delay,
)
from wef_backend.features.ingestion.application.persistence import RunLockHeldError
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventBatchResult,
    LiveTelegramEvent,
    LiveTelegramEventProcessor,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.application.telegram_progress import (
    SourceObservation,
    SweepBatch,
)
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointReconciler,
    TelegramReconciliationRequest,
)
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramSecretError
from wef_backend.features.ingestion.infrastructure.archive_recovery import SQLAlchemyArchiveRecovery
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)
from wef_backend.features.ingestion.infrastructure.models import (
    SourceMessageRow,
    TelegramArchiveExceptionRow,
    TelegramArchiveRecoveryRow,
    TelegramChannelProgressRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import (
    TelegramSourceDeferredError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


def payload(message_id: int) -> dict[str, object]:
    result = historical_payload(message_id)
    result.pop("reply_to_message_id")
    return result


recovery_db = _recovery_db
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TEST_DATABASE_URL") is None, reason="TEST_DATABASE_URL is not configured"
    ),
]


async def test_contended_record_survives_restarts_and_later_work_advances(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    first = await db.land(payload(11))
    for _ in range(8):
        assert await db.archive.record_failure(
            first.id, classify_archive_failure(RunLockHeldError())
        )
    assert not await db.archive.can_attempt(first.id)
    await db.land(payload(12))
    result = await db.drainer().drain_once()
    assert result.newly_terminal == 1
    async with db.factory() as session, session.begin():
        row = await session.get(TelegramRawEventRow, first.id)
        assert row is not None
        assert (row.data_failure_count, row.deferral_count, row.attempts) == (0, 8, 8)
        assert await session.get(TelegramArchiveExceptionRow, first.id) is None
        row.next_attempt_at = NOW - timedelta(days=1)
    assert (await db.drainer().drain_once()).newly_terminal == 1
    assert not await db.archive.record_failure(first.id, ArchiveFailure("data", "ValueError"))


async def test_poison_quarantine_is_unique_fair_and_policy_scoped(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    poison = await db.land(payload(21))
    for _ in range(6):
        await db.archive.record_failure(poison.id, ArchiveFailure("data", "ValueError"))
    await db.land(payload(22))
    assert [item.external_message_id for item in await db.archive.unprocessed_batch(25)] == [22]
    assert not await db.archive.can_attempt(poison.id)
    async with db.factory() as session, session.begin():
        issue = await session.get(TelegramArchiveExceptionRow, poison.id)
        assert issue is not None
        assert issue.state == "quarantined"
        assert issue.reason == "ValueError"
        row = await session.get(TelegramRawEventRow, poison.id)
        assert row is not None
        row.retry_policy_version = "previous-relevant-policy"
    assert poison.id in [item.id for item in await db.archive.unprocessed_batch(25)]
    async with db.factory() as session:
        row = await session.get(TelegramRawEventRow, poison.id)
        issue = await session.get(TelegramArchiveExceptionRow, poison.id)
        assert row is not None
        assert row.data_failure_count == 0
        assert row.attempts == 6
        assert issue is not None
        assert issue.state == "retrying"
    assert (await db.drainer().drain_once()).newly_terminal == 2
    async with db.factory() as session:
        issue = await session.get(TelegramArchiveExceptionRow, poison.id)
        assert issue is not None
        assert issue.state == "resolved"


async def test_legacy_retry_classification_is_bounded_and_preserves_attempts(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    lock = await db.land(payload(31))
    data = await db.land(payload(32))
    async with db.factory() as session, session.begin():
        await session.execute(
            update(TelegramRawEventRow).values(
                retry_policy_version="", attempts=9, outcome="failed", last_error="ValueError"
            )
        )
        await session.execute(
            update(TelegramRawEventRow)
            .where(TelegramRawEventRow.id == lock.id)
            .values(last_error="RunLockHeldError")
        )
    selected = await db.archive.unprocessed_batch(25)
    assert [item.id for item in selected] == [lock.id]
    async with db.factory() as session:
        row = await session.get(TelegramRawEventRow, lock.id)
        assert row is not None
        assert row.attempts == 9
        assert row.data_failure_count == 0
        assert row.retry_policy_version == RETRY_POLICY_VERSION
        issue = await session.get(TelegramArchiveExceptionRow, data.id)
        assert issue is not None


async def test_polling_and_applied_boundaries_are_independent_and_monotonic(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    channel = db.identity.channel_id
    assert (await store.channel_progress(channel_external_id=channel)).polled_through_id == 0
    await db.canonical(payload(1000))
    progress = await store.channel_progress(channel_external_id=channel)
    assert (progress.applied_high_water_id, progress.polled_through_id) == (1000, 0)
    assert progress.history_limited
    await asyncio.gather(
        *[
            store.advance_live_checkpoint(channel_external_id=channel, external_id=i)
            for i in (900, 300, 1200, 100)
        ]
    )
    await db.canonical(payload(10))
    progress = await store.channel_progress(channel_external_id=channel)
    assert (progress.applied_high_water_id, progress.polled_through_id) == (1000, 1200)
    assert (await store.latest_live_checkpoint(channel_external_id=channel))[0] == 1200


async def test_sweep_resumes_fixed_range_and_rejects_expired_observer(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    channel = db.identity.channel_id
    for number in (1, 2, 3):
        await db.canonical(payload(number))
    batch = await store.sweep_batch(channel, 2)
    assert batch.ids == (1, 2)
    assert not (await store.sweep_batch(channel, 2)).ids
    await store.finish_sweep_batch(channel, SweepBatch(batch.ids, uuid4()), unknown=0)
    assert not (await store.sweep_batch(channel, 2)).ids
    await store.finish_sweep_batch(channel, batch, unknown=1)
    await db.canonical(payload(4))
    tail = await store.sweep_batch(channel, 2)
    assert tail.ids == (3,)
    await store.finish_sweep_batch(channel, tail, unknown=0)
    assert (await store.channel_progress(channel_external_id=channel)).history_limited
    restart = await store.sweep_batch(channel, 1000)
    assert restart.ids == (1, 2, 3, 4)
    async with db.factory() as session, session.begin():
        await session.execute(
            update(TelegramChannelProgressRow).values(sweep_lease_until=NOW - timedelta(days=1))
        )
    renewed = await store.sweep_batch(channel, 100)
    assert renewed.ids == restart.ids
    assert renewed.token != restart.token
    await store.finish_sweep_batch(channel, restart, unknown=0)
    assert not (await store.sweep_batch(channel, 100)).ids
    await store.advance_live_checkpoint(channel_external_id=channel, external_id=4)
    await store.finish_sweep_batch(channel, renewed, unknown=0)
    assert not (await store.channel_progress(channel_external_id=channel)).history_limited


async def test_source_retry_is_durable_even_before_first_message(recovery_db: RecoveryDB) -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(recovery_db.factory)
    channel = recovery_db.identity.channel_id
    before = datetime.now(UTC)
    await store.defer_source(channel, seconds=900)
    first = await store.channel_progress(channel_external_id=channel)
    assert first.source_retry_at is not None
    assert first.source_retry_at >= before + timedelta(seconds=900)
    await store.defer_source(channel, seconds=5)
    second = await store.channel_progress(channel_external_id=channel)
    assert second.source_retry_at == first.source_retry_at
    assert second.history_limited
    assert second.polled_through_id == 0


def test_wrapped_transport_failures_and_provider_delays_preserve_data_budget() -> None:
    error = ValueError("synthetic wrapper")
    error.__cause__ = OSError("synthetic transport")
    assert classify_archive_failure(error).kind == "deferred"
    assert classify_archive_failure(ValueError()).kind == "data"
    assert retry_delay(1000000, 1) == 300
    assert retry_delay(1, 0) == 5
    assert retry_delay(1, 1, 900) == 900


async def test_polling_archives_failed_item_then_advances_and_sweeps_old_deletion(
    recovery_db: RecoveryDB,
) -> None:

    db = recovery_db
    await db.canonical(payload(1))
    await db.canonical(payload(2))
    await db.canonical(payload(3))
    identity = db.identity
    lock = asyncio.Lock()

    class Client(FakeTelegramLiveClient):
        async def observe_messages(
            self, *, username: str, ids: Sequence[int]
        ) -> Sequence[SourceObservation]:
            assert username == identity.username
            assert not lock.locked()
            return tuple(
                SourceObservation(
                    3,
                    "present",
                    LiveTelegramMessage(
                        external_message_id=3,
                        text="synthetic edited",
                        published_at=NOW,
                        edited_at=NOW + timedelta(seconds=60),
                    ),
                )
                if number == 3
                else SourceObservation(number, "deleted" if number == 1 else "unknown")
                for number in ids
            )

    client = Client(
        entity=TelegramChannelEntity(
            username=identity.username, channel_id=identity.channel_id, title=identity.channel_title
        ),
        messages=tuple(
            LiveTelegramMessage(
                external_message_id=i, text="synthetic", published_at=NOW, edited_at=None
            )
            for i in (10, 11)
        ),
        connected=True,
    )
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    processor = LiveTelegramEventProcessor(store=db.store, client=client, archive=db.archive)

    async def failing(
        *,
        identity: TelegramChannelIdentity,
        events: Sequence[LiveTelegramEvent],
        resume_after_external_id: int = 0,
        release_sha: str | None = None,
        manage_connection: bool = True,
    ) -> LiveEventBatchResult:
        if events[0].message is not None and events[0].message.external_message_id == 10:
            msg = "synthetic poison"
            raise ValueError(msg)
        return await processor(
            identity=identity,
            events=events,
            resume_after_external_id=resume_after_external_id,
            release_sha=release_sha,
            manage_connection=manage_connection,
        )

    reconciler = TelegramCheckpointReconciler(
        store, client, failing, lock, archive=db.archive, sweep_store=store
    )
    result = await reconciler(TelegramReconciliationRequest(identity))
    assert result.checkpoint_external_id == 11
    assert not result.remote_gap

    async with db.factory() as session:
        rows = list(
            await session.scalars(
                select(SourceMessageRow).order_by(SourceMessageRow.external_message_id)
            )
        )
        assert [row.external_message_id for row in rows] == [1, 2, 3, 11]
        assert rows[0].deleted_at is not None
        assert rows[1].deleted_at is None
        assert isinstance(rows[2].raw_payload_json, dict)
        assert rows[2].raw_payload_json["text"] == "synthetic edited"
        pending = await session.scalar(
            select(TelegramRawEventRow).where(TelegramRawEventRow.external_message_id == 10)
        )
        assert pending is not None
        assert pending.data_failure_count == 1
    assert (await store.channel_progress(channel_external_id=identity.channel_id)).history_limited
    await replace(reconciler, processor=processor)(TelegramReconciliationRequest(identity))
    async with db.factory() as session:
        pending = await session.scalar(
            select(TelegramRawEventRow).where(TelegramRawEventRow.external_message_id == 10)
        )
        assert pending is not None
        assert pending.data_failure_count == 1


async def test_source_outage_releases_lock_and_does_not_certify_progress(
    recovery_db: RecoveryDB,
) -> None:

    db = recovery_db
    identity = db.identity
    lock = asyncio.Lock()
    calls = []

    class Client(FakeTelegramLiveClient):
        async def latest_message_id(self, username: str) -> int:
            assert not lock.locked()
            calls.append(username)
            raise TelegramSourceDeferredError(600)

    client = Client(
        entity=TelegramChannelEntity(
            username=identity.username, channel_id=identity.channel_id, title=identity.channel_title
        ),
        connected=True,
    )
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    reconciler = TelegramCheckpointReconciler(
        store,
        client,
        LiveTelegramEventProcessor(store=db.store, client=client, archive=db.archive),
        lock,
        archive=db.archive,
        sweep_store=store,
    )
    for _ in range(2):
        result = await reconciler(TelegramReconciliationRequest(identity))
        assert result.source_deferred
        assert result.cycle_limited
        assert result.checkpoint_external_id == 0
    assert len(calls) == 1
    progress = await store.channel_progress(channel_external_id=identity.channel_id)
    assert progress.last_polled_at is None


async def test_two_transactions_cannot_replace_committed_high_water_with_old_work(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    await db.canonical(payload(50))
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    channel = db.identity.channel_id
    old_waiting = asyncio.Event()

    async def old_work() -> None:
        old_waiting.set()
        await store.advance_live_checkpoint(channel_external_id=channel, external_id=20)

    async with db.factory() as session, session.begin():
        await session.execute(update(TelegramChannelProgressRow).values(polled_through_id=500))
        delayed = asyncio.create_task(old_work())
        await old_waiting.wait()
        assert not delayed.done()
    await delayed
    assert (await store.channel_progress(channel_external_id=channel)).polled_through_id == 500


async def test_systemic_failure_pauses_recovery_and_missing_work_is_ignored(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    event = await db.land(payload(61))
    recovery = SQLAlchemyArchiveRecovery(db.factory)
    await recovery.claim_batch(db.identity.channel_id, 25)
    assert not await db.archive.record_failure(uuid4(), ArchiveFailure("data", "ValueError"))
    assert not await db.archive.can_attempt(uuid4())
    await db.archive.record_failure(
        event.id, ArchiveFailure("systemic", "TelegramEntityMismatchError")
    )
    async with db.factory() as session:
        state = await session.get(TelegramArchiveRecoveryRow, db.identity.channel_id)
        assert state is not None
        assert state.phase == "paused"
        assert state.pause_reason == "TelegramEntityMismatchError"
    assert not await recovery.claim_batch(db.identity.channel_id, 25)


async def test_source_access_loss_invalidates_previous_complete_coverage(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    identity = db.identity
    await db.canonical(payload(77))
    store = SQLAlchemyTelegramWorkerStatusStore(db.factory)
    await store.advance_live_checkpoint(channel_external_id=identity.channel_id, external_id=77)
    batch = await store.sweep_batch(identity.channel_id, 100)
    await store.finish_sweep_batch(identity.channel_id, batch, unknown=0)
    assert not (
        await store.channel_progress(channel_external_id=identity.channel_id)
    ).history_limited

    class Client(FakeTelegramLiveClient):
        async def latest_message_id(self, username: str) -> int:
            assert username == identity.username
            message = "synthetic authorization loss"
            raise TelegramSecretError(message)

    client = Client(
        entity=TelegramChannelEntity(
            username=identity.username, channel_id=identity.channel_id, title=identity.channel_title
        ),
        connected=True,
    )
    reconciler = TelegramCheckpointReconciler(
        store,
        client,
        LiveTelegramEventProcessor(store=db.store, client=client),
        asyncio.Lock(),
        archive=db.archive,
        sweep_store=store,
    )
    with pytest.raises(TelegramSecretError):
        await reconciler(TelegramReconciliationRequest(identity))
    assert (await store.channel_progress(channel_external_id=identity.channel_id)).history_limited
