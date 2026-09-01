"""Tests for bounded checkpoint-driven Telegram reconciliation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventBatchResult,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointReconciler,
    TelegramReconciliationRequest,
    maintain_checkpoint_reconciliation,
    read_durable_telegram_checkpoint,
)
from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    WorkerRuntimeState,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import CriticalStageStatus
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wef_backend.features.ingestion.application.telegram_events import LiveTelegramEvent
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


@dataclass
class _CheckpointStore:
    checkpoint: int | None
    max_id: int

    async def max_external_message_id(self, *, channel_external_id: str) -> int:
        assert channel_external_id == default_live_channel_identity().channel_id
        return self.max_id

    async def latest_live_checkpoint(
        self,
        *,
        channel_external_id: str,
    ) -> tuple[int | None, datetime | None]:
        assert channel_external_id == default_live_channel_identity().channel_id
        return self.checkpoint, datetime.now(UTC) if self.checkpoint is not None else None


@dataclass
class _Processor:
    calls: list[tuple[tuple[int, ...], tuple[LiveTelegramEventKind, ...], int]] = field(
        default_factory=list,
    )

    async def __call__(
        self,
        *,
        identity: TelegramChannelIdentity,
        events: Sequence[LiveTelegramEvent],
        resume_after_external_id: int = 0,
        release_sha: str | None = None,
        manage_connection: bool = True,
    ) -> LiveEventBatchResult:
        _ = (identity, release_sha)
        assert manage_connection is False
        message_ids = tuple(
            event.message.external_message_id for event in events if event.message is not None
        )
        kinds = tuple(event.kind for event in events)
        self.calls.append((message_ids, kinds, resume_after_external_id))
        checkpoint = max((resume_after_external_id, *message_ids))
        return LiveEventBatchResult(
            verified_channel_id=identity.channel_id,
            events_seen=len(events),
            messages_persisted=len(message_ids),
            created=len(message_ids),
            unchanged=0,
            revised=0,
            skipped_non_candidate=0,
            deleted=0,
            already_deleted=0,
            missing_on_delete=0,
            checkpoint_external_message_id=checkpoint,
            offers_hidden=0,
        )


def _message(message_id: int, *, edited: bool = False) -> LiveTelegramMessage:
    published_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC) + timedelta(
        seconds=message_id,
    )
    return LiveTelegramMessage(
        external_message_id=message_id,
        text=f"synthetic-{message_id}",
        published_at=published_at,
        edited_at=published_at + timedelta(minutes=1) if edited else None,
    )


def _client(messages: Sequence[LiveTelegramMessage]) -> FakeTelegramLiveClient:
    identity = default_live_channel_identity()
    return FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        messages=messages,
        connected=True,
    )


@pytest.mark.asyncio
async def test_reconciler_closes_observed_55_message_incident_gap() -> None:
    processor = _Processor()
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=29_202, max_id=29_202),
        client=_client(tuple(_message(item) for item in range(29_203, 29_258))),
        processor=processor,
        processing_lock=asyncio.Lock(),
    )

    result = await reconciler(
        TelegramReconciliationRequest(identity=default_live_channel_identity()),
    )

    assert result.starting_checkpoint_external_id == 29_202
    assert result.remote_head_external_id == 29_257
    assert result.messages_fetched == 55
    assert result.checkpoint_external_id == 29_257
    assert result.remote_gap is False
    assert processor.calls[0][0] == tuple(range(29_203, 29_258))


@pytest.mark.asyncio
async def test_reconciler_is_bounded_and_reports_remaining_remote_gap() -> None:
    processor = _Processor()
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=0, max_id=0),
        client=_client(tuple(_message(item) for item in range(1, 601))),
        processor=processor,
        processing_lock=asyncio.Lock(),
    )

    result = await reconciler(
        TelegramReconciliationRequest(identity=default_live_channel_identity()),
    )

    assert [len(call[0]) for call in processor.calls] == [100, 100, 100, 100, 100]
    assert result.messages_fetched == 500
    assert result.checkpoint_external_id == 500
    assert result.remote_head_external_id == 600
    assert result.remote_gap is True
    assert result.cycle_limited is True


@pytest.mark.asyncio
async def test_reconciler_waits_for_shared_event_processing_lock() -> None:
    processor = _Processor()
    processing_lock = asyncio.Lock()
    await processing_lock.acquire()
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=0, max_id=0),
        client=_client((_message(1),)),
        processor=processor,
        processing_lock=processing_lock,
    )
    task = asyncio.create_task(
        reconciler(TelegramReconciliationRequest(identity=default_live_channel_identity())),
    )
    await asyncio.sleep(0)
    assert processor.calls == []
    processing_lock.release()
    result = await task
    assert result.checkpoint_external_id == 1


@pytest.mark.asyncio
async def test_reconciler_replays_overlap_and_classifies_edits() -> None:
    processor = _Processor()
    messages = tuple(_message(item, edited=item == 95) for item in range(91, 106))
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=100, max_id=100),
        client=_client(messages),
        processor=processor,
        processing_lock=asyncio.Lock(),
    )

    result = await reconciler(
        TelegramReconciliationRequest(
            identity=default_live_channel_identity(),
            overlap=10,
        ),
    )

    ids, kinds, resume = processor.calls[0]
    assert ids == tuple(range(91, 106))
    assert kinds[ids.index(95)] is LiveTelegramEventKind.EDIT
    assert resume == 100
    assert result.checkpoint_external_id == 105


@pytest.mark.asyncio
async def test_reconciler_invokes_prepare_cycle_before_overlap_replay() -> None:
    resets: list[str] = []
    processor = _Processor()
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=100, max_id=100),
        client=_client(tuple(_message(item) for item in range(91, 106))),
        processor=processor,
        processing_lock=asyncio.Lock(),
        prepare_cycle=lambda: resets.append("reset"),
    )

    await reconciler(
        TelegramReconciliationRequest(
            identity=default_live_channel_identity(),
            overlap=10,
        ),
    )

    assert resets == ["reset"]


@pytest.mark.asyncio
async def test_checkpoint_falls_back_to_persisted_max_on_first_live_run() -> None:
    checkpoint = await read_durable_telegram_checkpoint(
        _CheckpointStore(checkpoint=None, max_id=42),
        channel_external_id=default_live_channel_identity().channel_id,
    )
    assert checkpoint == 42


@pytest.mark.asyncio
async def test_reconciliation_stage_records_safe_failure_and_propagates() -> None:
    class _FailingClient(FakeTelegramLiveClient):
        async def latest_message_id(self, username: str) -> int:
            _ = username
            message = "listing text and password=secret"
            raise RuntimeError(message)

    identity = default_live_channel_identity()
    client = _FailingClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        connected=True,
    )
    reconciler = TelegramCheckpointReconciler(
        store=_CheckpointStore(checkpoint=42, max_id=42),
        client=client,
        processor=_Processor(),
        processing_lock=asyncio.Lock(),
    )
    state = WorkerRuntimeState(transport_connected=True, consumer_running=True)

    with pytest.raises(RuntimeError, match="password=secret"):
        await maintain_checkpoint_reconciliation(
            reconciler,
            TelegramReconciliationRequest(identity=identity),
            state=state,
            stop=asyncio.Event(),
            interval=60,
        )

    assert state.reconciliation_status is CriticalStageStatus.FAILED
    assert state.last_error_category == "RuntimeError"


@pytest.mark.asyncio
async def test_reconciliation_runs_immediately_and_periodically_until_stopped() -> None:
    stop = asyncio.Event()

    class _CountingClient(FakeTelegramLiveClient):
        observations = 0

        async def latest_message_id(self, username: str) -> int:
            self.observations += 1
            if self.observations == 2:
                stop.set()
            return await super().latest_message_id(username)

    identity = default_live_channel_identity()
    client = _CountingClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        connected=True,
    )
    state = WorkerRuntimeState(transport_connected=True, consumer_running=True)
    await maintain_checkpoint_reconciliation(
        TelegramCheckpointReconciler(
            store=_CheckpointStore(checkpoint=0, max_id=0),
            client=client,
            processor=_Processor(),
            processing_lock=asyncio.Lock(),
        ),
        TelegramReconciliationRequest(identity=identity),
        state=state,
        stop=stop,
        interval=0.01,
    )
    assert client.observations == 2
    assert state.reconciliation_status is CriticalStageStatus.RUNNING
    assert state.last_reconciliation_at is not None


@pytest.mark.asyncio
async def test_reconciliation_cancellation_is_not_misreported_as_failure() -> None:
    started = asyncio.Event()

    class _BlockingClient(FakeTelegramLiveClient):
        async def latest_message_id(self, username: str) -> int:
            _ = username
            started.set()
            await asyncio.Event().wait()
            return 0

    identity = default_live_channel_identity()
    client = _BlockingClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        connected=True,
    )
    state = WorkerRuntimeState(transport_connected=True, consumer_running=True)
    task = asyncio.create_task(
        maintain_checkpoint_reconciliation(
            TelegramCheckpointReconciler(
                store=_CheckpointStore(checkpoint=0, max_id=0),
                client=client,
                processor=_Processor(),
                processing_lock=asyncio.Lock(),
            ),
            TelegramReconciliationRequest(identity=identity),
            state=state,
            stop=asyncio.Event(),
            interval=60,
        ),
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state.reconciliation_status is CriticalStageStatus.RUNNING
    assert state.last_error_category is None


def test_reconciliation_request_rejects_unbounded_settings() -> None:
    identity = default_live_channel_identity()
    with pytest.raises(ValueError, match="batch size"):
        TelegramReconciliationRequest(identity=identity, batch_size=101)
    with pytest.raises(ValueError, match="max messages"):
        TelegramReconciliationRequest(identity=identity, max_messages=501)
    with pytest.raises(ValueError, match="overlap"):
        TelegramReconciliationRequest(identity=identity, overlap=-1)
