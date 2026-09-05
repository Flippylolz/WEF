"""Live Telegram new/edit/delete event processing for E8-T3."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    MessageOutcome,
    PersistableMessage,
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
    SourceDeletionOutcome,
    redacted_error_summary,
)
from wef_backend.features.ingestion.application.telegram_live import (
    live_message_payload,
    live_message_to_raw,
    source_identity_from_channel,
    verify_channel_entity,
)
from wef_backend.features.ingestion.domain.model import canonical_json_checksum
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from wef_backend.features.ingestion.application.live_media import LiveMediaPipeline
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


RawArchiveOutcome = Literal["processed", "failed", "skipped_non_candidate"]
RawArchiveKind = Literal["new", "edit", "delete"]


class RawEventArchivePort(Protocol):
    """Verbatim landing and outcome ledger owned by persistence."""

    async def land(
        self,
        *,
        event_kind: RawArchiveKind,
        channel_external_id: str,
        external_message_id: int,
        payload: Mapping[str, object],
        checksum: str,
    ) -> UUID:
        """Land one verbatim event idempotently and return its stable row id."""
        ...

    async def unprocessed_batch(
        self,
        limit: int,
        *,
        channel_external_id: str | None = None,
    ) -> Sequence[RawEventRecord]:
        """Return the oldest events still awaiting a terminal outcome."""
        ...

    async def mark_attempt(
        self,
        event_id: UUID,
        *,
        outcome: RawArchiveOutcome,
        error_category: str | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """Record one processing attempt with bounded retry on failure."""
        ...


@dataclass(frozen=True, slots=True)
class RawEventRecord:
    """One landed verbatim event with its current ledger state."""

    id: UUID
    event_kind: RawArchiveKind
    channel_external_id: str
    external_message_id: int
    payload: Mapping[str, object]
    received_at: datetime
    attempts: int
    checksum: str = ""


async def land_live_event(
    archive: RawEventArchivePort,
    *,
    channel_external_id: str,
    event: LiveTelegramEvent,
) -> list[tuple[UUID, int]]:
    """Land one event verbatim before any canonical processing; return row ids."""
    if event.kind is LiveTelegramEventKind.DELETE:
        landed: list[tuple[UUID, int]] = []
        for deleted_id in event.deleted_ids:
            payload: dict[str, object] = {
                "id": deleted_id,
                "type": "deleted_message",
                "from_live": True,
            }
            row_id = await archive.land(
                event_kind="delete",
                channel_external_id=channel_external_id,
                external_message_id=deleted_id,
                payload=payload,
                checksum=canonical_json_checksum(payload),
            )
            landed.append((row_id, deleted_id))
        return landed
    if event.message is None:
        message = "new/edit events require a message payload"
        raise ValueError(message)
    payload = live_message_payload(event.message)
    row_id = await archive.land(
        event_kind="new" if event.kind is LiveTelegramEventKind.NEW else "edit",
        channel_external_id=channel_external_id,
        external_message_id=event.message.external_message_id,
        payload=payload,
        checksum=canonical_json_checksum(payload),
    )
    return [(row_id, event.message.external_message_id)]


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
    archive: RawEventArchivePort | None = None
    media_pipeline: LiveMediaPipeline | None = None

    @staticmethod
    def _delete_totals(
        outcomes: Sequence[SourceDeletionOutcome],
    ) -> tuple[int, int, int, int]:
        """Fold per-id deletion outcomes into redacted counters."""
        deleted = 0
        already_deleted = 0
        missing = 0
        offers_hidden = 0
        for outcome in outcomes:
            if outcome.outcome is DeletionOutcomeKind.DELETED:
                deleted += 1
            elif outcome.outcome is DeletionOutcomeKind.ALREADY_DELETED:
                already_deleted += 1
            else:
                missing += 1
            offers_hidden += outcome.offers_hidden
        return deleted, already_deleted, missing, offers_hidden

    async def _mark_delete_outcomes(
        self,
        landed: Sequence[tuple[UUID, int]],
        outcomes: Sequence[SourceDeletionOutcome],
    ) -> None:
        """Correlate per-id deletion results onto their landed archive rows."""
        outcome_by_id = {outcome.external_message_id: outcome.outcome for outcome in outcomes}
        archive = self.archive
        if archive is None:
            return
        for row_id, deleted_id in landed:
            kind = outcome_by_id.get(deleted_id)
            await archive.mark_attempt(
                row_id,
                outcome=(
                    "skipped_non_candidate" if kind is DeletionOutcomeKind.MISSING else "processed"
                ),
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
                    landed: list[tuple[UUID, int]] = []
                    if self.archive is not None:
                        landed = await land_live_event(
                            self.archive,
                            channel_external_id=identity.channel_id,
                            event=event,
                        )
                    if event.kind is LiveTelegramEventKind.DELETE:
                        outcomes = await self.store.mark_source_deleted(
                            channel_id=channel_id,
                            external_message_ids=event.deleted_ids,
                            archive_event_ids={
                                external_id: row_id for row_id, external_id in landed
                            },
                        )
                        if self.archive is not None:
                            await self._mark_delete_outcomes(landed, outcomes)
                        deleted_delta, already_delta, missing_delta, hidden_delta = (
                            self._delete_totals(outcomes)
                        )
                        deleted += deleted_delta
                        already_deleted += already_delta
                        missing_on_delete += missing_delta
                        offers_hidden += hidden_delta
                        continue
                    if event.message is None:
                        message = "new/edit events require a message payload"
                        raise RuntimeError(message)  # noqa: TRY301 - invalid event boundary
                    raw = live_message_to_raw(event.message, identity=channel)
                    message_id = event.message.external_message_id
                    advance = message_id > checkpoint.last_source_index
                    persist_outcome, checkpoint, counts, _ = await self.store.persist_live_upsert(
                        channel_id=channel_id,
                        run_id=run_id,
                        message=PersistableMessage(
                            raw=raw,
                            extraction=extract_listing(raw),
                            archive_event_id=landed[0][0] if landed else None,
                        ),
                        checkpoint=checkpoint,
                        counts=counts,
                        advance_checkpoint=advance,
                    )
                    if self.archive is not None and landed:
                        await self.archive.mark_attempt(
                            landed[0][0],
                            outcome=(
                                "skipped_non_candidate"
                                if persist_outcome.outcome is MessageOutcome.SKIPPED_NON_CANDIDATE
                                else "processed"
                            ),
                        )
                    if (
                        self.media_pipeline is not None
                        and raw.media
                        and persist_outcome.outcome is not MessageOutcome.UNCHANGED
                    ):
                        await self.media_pipeline.process_message(channel=channel, raw=raw)
                    messages_persisted += 1
            except BaseException as error:
                await self.store.finish_run(
                    run_id=run_id,
                    status=(
                        RunStatus.CANCELLED
                        if isinstance(error, asyncio.CancelledError)
                        else RunStatus.FAILED
                    ),
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

    @property
    def has_ready_work(self) -> bool:
        """Let bounded maintenance yield before live ingestion work."""
        return not self._queue.empty()

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
