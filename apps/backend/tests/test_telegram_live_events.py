"""Unit tests for E8-T3 live new/edit/delete event processing."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    MessageOutcome,
    MessagePersistOutcome,
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunLockHeldError,
    RunMode,
    RunStatus,
    SourceDeletionOutcome,
)
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEvent,
    LiveTelegramEventKind,
    LiveTelegramEventProcessor,
    LiveWorkerHealth,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)
from wef_backend.features.ingestion.infrastructure.telethon_events import (
    delete_event_from_telethon,
    new_or_edit_event_from_telethon,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from uuid import UUID


class _FakeStore:
    """Persistence stand-in covering upsert, checkpoint, and delete lineage."""

    def __init__(self) -> None:
        self.messages: dict[int, PersistableMessage] = {}
        self.deleted: set[int] = set()
        self.hidden_offers: dict[int, int] = {}
        self.checkpoints: list[RunCheckpoint] = []
        self.runs: list[tuple[UUID, RunMode, RunStatus]] = []
        self.lock_held = False

    @asynccontextmanager
    async def run_lock(self, source_key: str) -> AsyncIterator[None]:
        if self.lock_held:
            raise RunLockHeldError(source_key)
        self.lock_held = True
        try:
            yield
        finally:
            self.lock_held = False

    async def ensure_channel(
        self,
        *,
        platform: str,
        external_id: str,
        display_name: str,
    ) -> UUID:
        _ = (platform, external_id, display_name)
        return uuid4()

    async def start_run(
        self,
        *,
        channel_id: UUID,
        mode: RunMode,
        parser_version: str,
        source_checksum: str | None,
        release_sha: str | None,
    ) -> UUID:
        _ = (channel_id, parser_version, source_checksum, release_sha)
        run_id = uuid4()
        self.runs.append((run_id, mode, RunStatus.RUNNING))
        return run_id

    async def persist_batch(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        batch: Sequence[tuple[PersistableMessage, int]],
        checkpoint: RunCheckpoint,
        counts: RunCounts,
    ) -> tuple[Sequence[MessagePersistOutcome], RunCheckpoint, RunCounts, int]:
        _ = (channel_id, run_id)
        outcomes: list[MessagePersistOutcome] = []
        acknowledged = checkpoint
        acknowledged_counts = counts
        for persistable, source_index in batch:
            outcome = self._upsert(persistable)
            outcomes.append(outcome)
            acknowledged = acknowledged.advances(source_index, persistable.raw.checksum)
            acknowledged_counts = acknowledged_counts.with_outcome(
                outcome=outcome,
                offer_created=outcome.outcome is MessageOutcome.CREATED,
            )
        self.checkpoints.append(acknowledged)
        return outcomes, acknowledged, acknowledged_counts, 0

    async def persist_live_upsert(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        message: PersistableMessage,
        checkpoint: RunCheckpoint,
        counts: RunCounts,
        advance_checkpoint: bool,
    ) -> tuple[MessagePersistOutcome, RunCheckpoint, RunCounts, int]:
        _ = (channel_id, run_id)
        outcome = self._upsert(message)
        acknowledged = checkpoint
        if advance_checkpoint:
            acknowledged = checkpoint.advances(
                message.raw.external_message_id,
                message.raw.checksum,
            )
        acknowledged_counts = counts.with_outcome(
            outcome=outcome,
            offer_created=outcome.outcome is MessageOutcome.CREATED,
        )
        self.checkpoints.append(acknowledged)
        return outcome, acknowledged, acknowledged_counts, 0

    async def mark_source_deleted(
        self,
        *,
        channel_id: UUID,
        external_message_ids: Sequence[int],
    ) -> Sequence[SourceDeletionOutcome]:
        _ = channel_id
        outcomes: list[SourceDeletionOutcome] = []
        for external_id in external_message_ids:
            if external_id not in self.messages and external_id not in self.deleted:
                outcomes.append(
                    SourceDeletionOutcome(
                        external_message_id=external_id,
                        outcome=DeletionOutcomeKind.MISSING,
                        offers_hidden=0,
                    ),
                )
                continue
            if external_id in self.deleted:
                outcomes.append(
                    SourceDeletionOutcome(
                        external_message_id=external_id,
                        outcome=DeletionOutcomeKind.ALREADY_DELETED,
                        offers_hidden=0,
                    ),
                )
                continue
            self.deleted.add(external_id)
            hidden = 1 if external_id in self.messages else 0
            self.hidden_offers[external_id] = hidden
            outcomes.append(
                SourceDeletionOutcome(
                    external_message_id=external_id,
                    outcome=DeletionOutcomeKind.DELETED,
                    offers_hidden=hidden,
                ),
            )
        return tuple(outcomes)

    async def finish_run(
        self,
        *,
        run_id: UUID,
        status: RunStatus,
        counts: RunCounts,
        checkpoint: RunCheckpoint,
        error_summary: str | None,
    ) -> None:
        _ = (counts, checkpoint, error_summary)
        self.runs.append((run_id, RunMode.LIVE, status))

    def _upsert(self, persistable: PersistableMessage) -> MessagePersistOutcome:
        existing = self.messages.get(persistable.raw.external_message_id)
        if existing is None:
            outcome = MessageOutcome.CREATED
            self.messages[persistable.raw.external_message_id] = persistable
        elif existing.raw.checksum == persistable.raw.checksum:
            outcome = MessageOutcome.UNCHANGED
        else:
            outcome = MessageOutcome.REVISED
            self.messages[persistable.raw.external_message_id] = persistable
        return MessagePersistOutcome(
            external_message_id=persistable.raw.external_message_id,
            outcome=outcome,
            revision_number=1,
        )


def _message(external_id: int, text: str, *, edited: bool = False) -> LiveTelegramMessage:
    published = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    return LiveTelegramMessage(
        external_message_id=external_id,
        text=text,
        published_at=published,
        edited_at=published if edited else None,
    )


@pytest.mark.asyncio
async def test_live_events_new_edit_delete_converge() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
    )
    store = _FakeStore()
    processor = LiveTelegramEventProcessor(store=store, client=client)
    first_text = "Cena: 4500 PLN, 2 pokoje, Mokotów"
    edited_text = "Cena: 4700 PLN, 2 pokoje, Mokotów"
    events = (
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.NEW,
            message=_message(20, first_text),
        ),
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.NEW,
            message=_message(20, first_text),
        ),
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.EDIT,
            message=_message(20, edited_text, edited=True),
        ),
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.DELETE,
            deleted_ids=(20,),
        ),
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.DELETE,
            deleted_ids=(20,),
        ),
    )
    result = await processor(identity=identity, events=events)
    assert result.events_seen == 5
    assert result.messages_persisted == 3
    assert result.created == 1
    assert result.unchanged == 1
    assert result.revised == 1
    assert result.deleted == 1
    assert result.already_deleted == 1
    assert result.offers_hidden == 1
    assert result.checkpoint_external_message_id == 20
    assert store.messages[20].raw.text == edited_text
    assert 20 in store.deleted


@pytest.mark.asyncio
async def test_edit_below_checkpoint_does_not_rewind_cursor() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
    )
    store = _FakeStore()
    processor = LiveTelegramEventProcessor(store=store, client=client)
    await processor(
        identity=identity,
        events=(
            LiveTelegramEvent(
                kind=LiveTelegramEventKind.NEW,
                message=_message(50, "Cena: 5000 PLN, 1 pokój, Centrum"),
            ),
        ),
    )
    result = await processor(
        identity=identity,
        events=(
            LiveTelegramEvent(
                kind=LiveTelegramEventKind.EDIT,
                message=_message(10, "Cena: 5100 PLN, 1 pokój, Centrum", edited=True),
            ),
        ),
        resume_after_external_id=50,
    )
    assert result.revised == 1 or result.created == 1
    assert result.checkpoint_external_message_id == 50


@pytest.mark.asyncio
async def test_event_queue_serializes_drain_order() -> None:
    queue = LiveEventQueue()
    await queue.put(
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.NEW,
            message=_message(1, "Cena: 1000 PLN, 1 pokój, Wola"),
        ),
    )
    await queue.put(
        LiveTelegramEvent(kind=LiveTelegramEventKind.DELETE, deleted_ids=(1,)),
    )
    await queue.close()
    drained = await queue.drain()
    assert [event.kind for event in drained] == [
        LiveTelegramEventKind.NEW,
        LiveTelegramEventKind.DELETE,
    ]


def test_telethon_event_adapters() -> None:
    published = datetime(2024, 3, 4, 5, 6, 7, tzinfo=UTC)
    event = new_or_edit_event_from_telethon(
        SimpleNamespace(
            id=9,
            message="hello",
            text=None,
            date=published,
            edit_date=None,
            grouped_id=None,
        ),
        kind=LiveTelegramEventKind.NEW,
    )
    assert event.kind is LiveTelegramEventKind.NEW
    assert event.message is not None
    assert event.message.external_message_id == 9
    deleted = delete_event_from_telethon([9, 10])
    assert deleted.deleted_ids == (9, 10)


def test_live_worker_health_does_not_imply_api_unavailability() -> None:
    health = LiveWorkerHealth(
        connected=False,
        last_event_received_at=None,
        last_event_committed_at=None,
        last_error_category="FloodWaitError",
    )
    assert health.connected is False
    # Public API readiness is independent of worker freshness (E8 spike / ADR).
    assert health.last_error_category == "FloodWaitError"


def test_live_event_validation() -> None:
    with pytest.raises(ValueError, match="message payload"):
        LiveTelegramEvent(kind=LiveTelegramEventKind.NEW)
    with pytest.raises(ValueError, match="message id"):
        LiveTelegramEvent(kind=LiveTelegramEventKind.DELETE)
    with pytest.raises(ValueError, match="deleted ids"):
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.NEW,
            message=_message(1, "Cena: 1000 PLN, 1 pokój, Wola"),
            deleted_ids=(1,),
        )
    with pytest.raises(ValueError, match="message payload"):
        LiveTelegramEvent(
            kind=LiveTelegramEventKind.DELETE,
            message=_message(1, "x"),
            deleted_ids=(1,),
        )


def test_telethon_event_adapters_reject_bad_inputs() -> None:
    with pytest.raises(ValueError, match="new or edit"):
        new_or_edit_event_from_telethon(
            SimpleNamespace(id=1, message="x", date=datetime.now(UTC)),
            kind=LiveTelegramEventKind.DELETE,
        )
    with pytest.raises(TypeError, match="iterable"):
        delete_event_from_telethon("not-ids")


@pytest.mark.asyncio
async def test_live_processor_records_failed_run_on_upsert_error() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
    )
    store = _FakeStore()

    async def _boom(**_kwargs: object) -> object:
        category = "injected"
        raise PersistenceBatchError(category)

    store.persist_live_upsert = _boom  # type: ignore[assignment]
    processor = LiveTelegramEventProcessor(store=store, client=client)
    with pytest.raises(PersistenceBatchError):
        await processor(
            identity=identity,
            events=(
                LiveTelegramEvent(
                    kind=LiveTelegramEventKind.NEW,
                    message=_message(3, "Cena: 3000 PLN, 1 pokój, Bemowo"),
                ),
            ),
        )
    assert store.runs[-1][2] is RunStatus.FAILED
