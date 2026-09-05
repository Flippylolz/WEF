"""Unit tests for E8-T3 live new/edit/delete event processing."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from wef_backend.features.ingestion.application.archive_processing import ArchiveResolution
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
from wef_backend.features.ingestion.application.raw_archive import (
    RawEventDrainer,
)
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventHandlerError,
    LiveEventQueue,
    LiveTelegramEvent,
    LiveTelegramEventKind,
    LiveTelegramEventProcessor,
    LiveWorkerHealth,
    RawArchiveKind,
    RawArchiveOutcome,
    RawEventArchivePort,
    RawEventRecord,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramChannelIdentity,
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
    from collections.abc import AsyncIterator, Mapping, Sequence
    from uuid import UUID

    from wef_backend.features.ingestion.domain.extraction import ListingCandidate


class _FakeStore:
    """Persistence stand-in covering upsert, checkpoint, and delete lineage."""

    def __init__(self) -> None:
        self.messages: dict[int, PersistableMessage] = {}
        self.deleted: set[int] = set()
        self.hidden_offers: dict[int, int] = {}
        self.checkpoints: list[RunCheckpoint] = []
        self.runs: list[tuple[UUID, RunMode, RunStatus]] = []
        self.lock_held = False
        self.convert_non_candidates = False

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
        archive_event_ids: dict[int, UUID] | None = None,  # noqa: ARG002 - protocol parity
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

    async def persist_owner_ai_listing(
        self,
        *,
        source_message_revision_id: UUID,
        listing: ListingCandidate,
        run_id: UUID | None = None,  # noqa: ARG002 - protocol correlation used by SQL adapter
    ) -> UUID:
        """Stub owner AI listing persistence for protocol conformance."""
        _ = (source_message_revision_id, listing)
        return uuid4()

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
            if self.convert_non_candidates and (
                persistable.extraction is None or persistable.extraction.listing is None
            ):
                outcome = MessageOutcome.SKIPPED_NON_CANDIDATE
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
async def test_unchanged_replay_skips_live_media_pipeline() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
    )
    store = _FakeStore()
    media_pipeline = AsyncMock()
    media_pipeline.process_message = AsyncMock(return_value=0)
    processor = LiveTelegramEventProcessor(
        store=store,
        client=client,
        media_pipeline=media_pipeline,
    )
    text = "Cena: 4500 PLN, 2 pokoje, Mokotów"
    message = LiveTelegramMessage(
        external_message_id=20,
        text=text,
        published_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        edited_at=None,
        media=(
            MediaDescriptor(
                kind=MediaKind.PHOTO,
                path="20/0.jpg",
                mime_type="image/jpeg",
            ),
        ),
    )
    await processor(
        identity=identity,
        events=(LiveTelegramEvent(kind=LiveTelegramEventKind.NEW, message=message),),
    )
    media_pipeline.process_message.assert_awaited_once()
    media_pipeline.process_message.reset_mock()
    await processor(
        identity=identity,
        events=(LiveTelegramEvent(kind=LiveTelegramEventKind.NEW, message=message),),
    )
    media_pipeline.process_message.assert_not_awaited()


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


@pytest.mark.asyncio
async def test_event_queue_redacts_handler_failure() -> None:
    queue = LiveEventQueue()
    await queue.fail(RuntimeError("password=secret source listing text"))
    with pytest.raises(LiveEventHandlerError) as captured:
        await queue.get()
    assert captured.value.category == "RuntimeError"
    assert "secret" not in str(captured.value)
    assert "listing" not in str(captured.value)


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


_ENTITY = TelegramChannelEntity(
    username=default_live_channel_identity().username,
    channel_id=default_live_channel_identity().channel_id,
    title=default_live_channel_identity().channel_title,
)


class _FakeArchive(RawEventArchivePort):
    """Landing/outcome ledger stand-in recording call order."""

    def __init__(self) -> None:
        self.landed: list[tuple[str, int, Mapping[str, object]]] = []
        self.marked: list[tuple[UUID, str, str | None]] = []
        self.pending: list[RawEventRecord] = []
        self._ids = iter(uuid4() for _ in range(99))

    async def land(
        self,
        *,
        event_kind: RawArchiveKind,
        channel_external_id: str,  # noqa: ARG002 - contract parity
        external_message_id: int,
        payload: Mapping[str, object],
        checksum: str,  # noqa: ARG002 - contract parity
    ) -> UUID:
        self.landed.append((str(event_kind), external_message_id, payload))
        return next(self._ids)

    async def unprocessed_batch(
        self,
        limit: int,
        *,
        channel_external_id: str | None = None,
    ) -> Sequence[RawEventRecord]:
        return [
            record
            for record in self.pending
            if channel_external_id is None or record.channel_external_id == channel_external_id
        ][:limit]

    async def mark_attempt(
        self,
        event_id: UUID,
        *,
        outcome: RawArchiveOutcome,
        error_category: str | None = None,
        completed_at: datetime | None = None,  # noqa: ARG002 - contract parity
    ) -> bool:
        self.marked.append((event_id, str(outcome), error_category))
        return True


async def test_processor_lands_events_verbatim_before_processing() -> None:
    """New and delete events land first; rows receive the real outcomes."""
    identity = default_live_channel_identity()
    store = _FakeStore()
    client = FakeTelegramLiveClient(_ENTITY)
    archive = _FakeArchive()
    processor = LiveTelegramEventProcessor(store=store, client=client, archive=archive)
    message = LiveTelegramMessage(
        external_message_id=50,
        text="Покупка | Квартира\nЦена: 500 000 PLN",  # noqa: RUF001
        published_at=datetime(2026, 8, 29, tzinfo=UTC),
        edited_at=None,
    )
    delete = LiveTelegramEvent(
        kind=LiveTelegramEventKind.DELETE,
        deleted_ids=(50,),
    )
    new_event = LiveTelegramEvent(kind=LiveTelegramEventKind.NEW, message=message)

    await processor(identity=identity, events=(new_event, delete), manage_connection=False)

    assert [kind for kind, _, _ in archive.landed] == ["new", "delete"]
    assert [message_id for _, message_id, _ in archive.landed] == [50, 50]
    assert archive.landed[0][2]["text"] == message.text
    assert {outcome for _, outcome, _ in archive.marked} == {"processed"}


async def test_processor_marks_skipped_non_candidate_and_delete_missing() -> None:
    """Non-candidates and missing deletions get distinct ledger outcomes."""
    identity = default_live_channel_identity()
    store = _FakeStore()
    client = FakeTelegramLiveClient(_ENTITY)
    archive = _FakeArchive()
    store.convert_non_candidates = True
    processor = LiveTelegramEventProcessor(store=store, client=client, archive=archive)
    message = LiveTelegramMessage(
        external_message_id=7,
        text="no listing evidence here",
        published_at=datetime(2026, 8, 29, tzinfo=UTC),
        edited_at=None,
    )

    await processor(
        identity=identity,
        events=(
            LiveTelegramEvent(kind=LiveTelegramEventKind.NEW, message=message),
            LiveTelegramEvent(kind=LiveTelegramEventKind.DELETE, deleted_ids=(99,)),
        ),
        manage_connection=False,
    )

    outcomes = [outcome for _, outcome, _ in archive.marked]
    assert outcomes == ["skipped_non_candidate", "skipped_non_candidate"]


class _OriginalProcessor:
    def __init__(self) -> None:
        self.records: list[RawEventRecord] = []

    async def __call__(
        self,
        *,
        record: RawEventRecord,
        identity: TelegramChannelIdentity,
        release_sha: str | None = None,
    ) -> ArchiveResolution:
        _ = identity, release_sha
        self.records.append(record)
        if "date_unixtime" not in record.payload:
            msg = "malformed archived record"
            raise ValueError(msg)
        return ArchiveResolution(record.id, "applied", datetime(2026, 9, 5, tzinfo=UTC))


async def test_drainer_reprocesses_pending_records_and_marks_failures() -> None:
    """Pending records flow through the processor; poisoned events fail bounded."""
    identity = default_live_channel_identity()
    record = RawEventRecord(
        id=uuid4(),
        event_kind="new",
        channel_external_id=identity.channel_id,
        external_message_id=601,
        payload={
            "id": 601,
            "type": "message",
            "date_unixtime": "1770000000",
            "text": "Покупка | Квартира\nЦена: 1 200 000 PLN",  # noqa: RUF001
            "from_live": True,
        },
        received_at=datetime(2026, 8, 29, tzinfo=UTC),
        attempts=0,
    )

    archive = _FakeArchive()
    archive.pending = [record]
    processor = _OriginalProcessor()
    drainer = RawEventDrainer(archive=archive, processor=processor, identity=identity)

    drained = await drainer.drain_once(release_sha="test-sha")

    assert drained.newly_terminal == 1
    assert processor.records[0] is record
    assert archive.landed == []
    assert archive.marked[0][0] == record.id
    assert ("processed" in {outcome for _, outcome, _ in archive.marked}) is True


async def test_drainer_marks_failed_without_blocking_the_batch() -> None:
    """A poisoned event is marked failed with a safe category; others continue."""
    identity = default_live_channel_identity()
    poisoned = RawEventRecord(
        id=uuid4(),
        event_kind="new",
        channel_external_id=identity.channel_id,
        external_message_id=1,
        payload={"id": "not-a-number", "type": "message"},
        received_at=datetime(2026, 8, 29, tzinfo=UTC),
        attempts=0,
    )
    healthy = RawEventRecord(
        id=uuid4(),
        event_kind="new",
        channel_external_id=identity.channel_id,
        external_message_id=2,
        payload={
            "id": 2,
            "type": "message",
            "date_unixtime": "1770000000",
            "text": "Покупка | Квартира\nЦена: 10 PLN",  # noqa: RUF001
            "from_live": True,
        },
        received_at=datetime(2026, 8, 29, tzinfo=UTC),
        attempts=0,
    )
    archive = _FakeArchive()
    archive.pending = [poisoned, healthy]
    processor = _OriginalProcessor()
    drainer = RawEventDrainer(archive=archive, processor=processor, identity=identity)

    drained = await drainer.drain_once()

    assert drained.selected == 2
    assert drained.newly_terminal == 1
    assert drained.failed == 1
    failures = [(eid, err) for eid, outcome, err in archive.marked if outcome == "failed"]
    assert len(failures) == 1
    assert failures[0][0] == poisoned.id
    assert failures[0][1] == "ValueError"
    assert any(outcome == "processed" for _, outcome, _ in archive.marked)
