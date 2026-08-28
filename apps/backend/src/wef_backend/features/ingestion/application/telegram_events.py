"""Live Telegram new/edit/delete event processing for E8-T3."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
    redacted_error_summary,
)
from wef_backend.features.ingestion.application.telegram_live import (
    live_message_to_raw,
    source_identity_from_channel,
    verify_channel_entity,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wef_backend.features.ingestion.application.persistence import IngestionPersistencePort
    from wef_backend.features.ingestion.application.telegram_live import (
        LiveTelegramMessage,
        TelegramLiveClientPort,
    )
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


class LiveTelegramEventKind(StrEnum):
    """Scoped live channel event kinds."""

    NEW = "new"
    EDIT = "edit"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class LiveTelegramEvent:
    """One channel-scoped live event (message payload or deleted ids)."""

    kind: LiveTelegramEventKind
    message: LiveTelegramMessage | None = None
    deleted_ids: tuple[int, ...] = ()
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Reject inconsistent new/edit/delete event shapes."""
        if self.kind in {LiveTelegramEventKind.NEW, LiveTelegramEventKind.EDIT}:
            if self.message is None:
                message = "new/edit events require a message payload"
                raise ValueError(message)
            if self.deleted_ids:
                message = "new/edit events must not carry deleted ids"
                raise ValueError(message)
        elif self.kind is LiveTelegramEventKind.DELETE:
            if self.message is not None:
                message = "delete events must not carry a message payload"
                raise ValueError(message)
            if not self.deleted_ids:
                message = "delete events require at least one message id"
                raise ValueError(message)


@dataclass(frozen=True, slots=True)
class LiveEventBatchResult:
    """Redacted reconciliation summary for one serialized event batch."""

    verified_channel_id: str
    events_seen: int
    messages_persisted: int
    created: int
    unchanged: int
    revised: int
    skipped_non_candidate: int
    deleted: int
    already_deleted: int
    missing_on_delete: int
    checkpoint_external_message_id: int
    offers_hidden: int


@dataclass(frozen=True, slots=True)
class LiveWorkerHealth:
    """Worker freshness only — never gates public API readiness."""

    connected: bool
    last_event_received_at: datetime | None
    last_event_committed_at: datetime | None
    last_error_category: str | None = None


class LiveEventHandlerError(RuntimeError):
    """Redacted event-adapter failure delivered to the supervised consumer."""

    def __init__(self, category: str) -> None:
        """Retain only a safe error category."""
        self.category = category
        super().__init__(f"Telegram event handler failed ({category})")


@dataclass(frozen=True, slots=True)
class LiveTelegramEventProcessor:
    """Serialize new/edit/delete through the shared persistence port."""

    store: IngestionPersistencePort
    client: TelegramLiveClientPort

    async def __call__(
        self,
        *,
        identity: TelegramChannelIdentity,
        events: Sequence[LiveTelegramEvent],
        resume_after_external_id: int = 0,
        release_sha: str | None = None,
        manage_connection: bool = True,
    ) -> LiveEventBatchResult:
        """Process events in arrival order under the channel advisory lock."""
        if manage_connection:
            await self.client.connect()
        try:
            return await self._process_connected(
                identity=identity,
                events=events,
                resume_after_external_id=resume_after_external_id,
                release_sha=release_sha,
            )
        finally:
            if manage_connection:
                await self.client.disconnect()

    async def _process_connected(
        self,
        *,
        identity: TelegramChannelIdentity,
        events: Sequence[LiveTelegramEvent],
        resume_after_external_id: int,
        release_sha: str | None,
    ) -> LiveEventBatchResult:
        """Process one batch while the client connection is already open."""
        entity = await self.client.resolve_channel(identity.username)
        verify_channel_entity(identity, entity)
        channel = source_identity_from_channel(identity)
        source_key = f"{channel.platform.value}:{channel.channel_id}"
        async with self.store.run_lock(source_key):
            channel_id = await self.store.ensure_channel(
                platform=channel.platform.value,
                external_id=channel.channel_id,
                display_name=channel.channel_name,
            )
            run_id = await self.store.start_run(
                channel_id=channel_id,
                mode=RunMode.LIVE,
                parser_version=PARSER_VERSION,
                source_checksum=None,
                release_sha=release_sha,
            )
            checkpoint = RunCheckpoint(
                last_source_index=resume_after_external_id if resume_after_external_id > 0 else -1,
            )
            counts = RunCounts()
            deleted = 0
            already_deleted = 0
            missing_on_delete = 0
            offers_hidden = 0
            messages_persisted = 0
            try:
                for event in events:
                    if event.kind is LiveTelegramEventKind.DELETE:
                        outcomes = await self.store.mark_source_deleted(
                            channel_id=channel_id,
                            external_message_ids=event.deleted_ids,
                        )
                        for outcome in outcomes:
                            if outcome.outcome is DeletionOutcomeKind.DELETED:
                                deleted += 1
                            elif outcome.outcome is DeletionOutcomeKind.ALREADY_DELETED:
                                already_deleted += 1
                            else:
                                missing_on_delete += 1
                            offers_hidden += outcome.offers_hidden
                        continue
                    if event.message is None:
                        message = "new/edit events require a message payload"
                        raise RuntimeError(message)
                    raw = live_message_to_raw(event.message, identity=channel)
                    message_id = event.message.external_message_id
                    advance = message_id > checkpoint.last_source_index
                    _, checkpoint, counts, _ = await self.store.persist_live_upsert(
                        channel_id=channel_id,
                        run_id=run_id,
                        message=PersistableMessage(
                            raw=raw,
                            extraction=extract_listing(raw),
                        ),
                        checkpoint=checkpoint,
                        counts=counts,
                        advance_checkpoint=advance,
                    )
                    messages_persisted += 1
            except PersistenceBatchError as error:
                await self.store.finish_run(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    counts=counts,
                    checkpoint=checkpoint,
                    error_summary=redacted_error_summary(error),
                )
                raise
            await self.store.finish_run(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                counts=counts,
                checkpoint=checkpoint,
                error_summary=None,
            )
            return LiveEventBatchResult(
                verified_channel_id=entity.channel_id,
                events_seen=len(events),
                messages_persisted=messages_persisted,
                created=counts.created,
                unchanged=counts.unchanged,
                revised=counts.revised,
                skipped_non_candidate=counts.skipped_non_candidate,
                deleted=deleted,
                already_deleted=already_deleted,
                missing_on_delete=missing_on_delete,
                checkpoint_external_message_id=max(
                    checkpoint.last_source_index,
                    resume_after_external_id,
                    0,
                ),
                offers_hidden=offers_hidden,
            )


@dataclass
class LiveEventQueue:
    """Single-consumer queue so Telethon callbacks cannot race persistence."""

    _queue: asyncio.Queue[LiveTelegramEvent | LiveEventHandlerError | None] = field(
        default_factory=asyncio.Queue,
    )

    async def put(self, event: LiveTelegramEvent) -> None:
        """Enqueue one event for serialized processing."""
        await self._queue.put(event)

    async def fail(self, error: BaseException) -> None:
        """Deliver only the exception category to the supervised consumer."""
        await self._queue.put(LiveEventHandlerError(safe_error_category(error)))

    async def get(self) -> LiveTelegramEvent | None:
        """Return the next event, or None after close()."""
        item = await self._queue.get()
        if isinstance(item, LiveEventHandlerError):
            raise item
        return item

    async def close(self) -> None:
        """Signal the consumer to stop after draining."""
        await self._queue.put(None)

    async def drain(self) -> list[LiveTelegramEvent]:
        """Drain queued events until close sentinel (for bounded tests)."""
        items: list[LiveTelegramEvent] = []
        while True:
            item = await self.get()
            if item is None:
                break
            items.append(item)
        return items
