"""Checkpoint-driven completeness loop for the live Telegram worker."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.application.archive_retry import (
    classify_archive_failure,
    retry_delay,
)
from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
    RawEventArchivePort,
    land_live_event,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import CriticalStageStatus

MAX_RECONCILIATION_BATCH_SIZE = 100
MAX_RECONCILIATION_MESSAGES = 500

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from wef_backend.features.ingestion.application.telegram_events import LiveEventBatchResult
    from wef_backend.features.ingestion.application.telegram_live import (
        TelegramLiveClientPort,
    )
    from wef_backend.features.ingestion.application.telegram_progress import TelegramSweepStore
    from wef_backend.features.ingestion.application.telegram_worker_liveness import (
        WorkerRuntimeState,
    )
    from wef_backend.features.ingestion.domain.telegram_channel import (
        TelegramChannelIdentity,
    )


class TelegramCheckpointStore(Protocol):
    """Read and advance durable polling coverage."""

    async def advance_live_checkpoint(self, *, channel_external_id: str, external_id: int) -> int:
        """Advance only a fetched range whose items have durable classified outcomes."""
        ...

    async def max_external_message_id(self, *, channel_external_id: str) -> int:
        """Return the largest persisted external id for the channel."""
        ...

    async def latest_live_checkpoint(
        self,
        *,
        channel_external_id: str,
    ) -> tuple[int | None, datetime | None]:
        """Return the latest live cursor and completion timestamp."""
        ...


class LiveReconciliationProcessor(Protocol):
    """Process one ordered polled batch through canonical live persistence."""

    async def __call__(
        self,
        *,
        identity: TelegramChannelIdentity,
        events: Sequence[LiveTelegramEvent],
        resume_after_external_id: int = 0,
        release_sha: str | None = None,
        manage_connection: bool = True,
    ) -> LiveEventBatchResult:
        """Persist one idempotent batch and return its durable cursor."""
        ...


@dataclass(frozen=True, slots=True)
class TelegramReconciliationRequest:
    """Bounded settings for one reconciliation cycle."""

    identity: TelegramChannelIdentity
    overlap: int = 20
    batch_size: int = 100
    max_messages: int = 500
    release_sha: str | None = None

    def __post_init__(self) -> None:
        """Reject unbounded or invalid cycle settings."""
        if self.overlap < 0:
            message = "reconciliation overlap must be non-negative"
            raise ValueError(message)
        if not 1 <= self.batch_size <= MAX_RECONCILIATION_BATCH_SIZE:
            message = "reconciliation batch size must be between 1 and 100"
            raise ValueError(message)
        if not 1 <= self.max_messages <= MAX_RECONCILIATION_MESSAGES:
            message = "reconciliation max messages must be between 1 and 500"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class TelegramReconciliationResult:
    """Privacy-safe outcome for one source observation/catch-up cycle."""

    starting_checkpoint_external_id: int
    checkpoint_external_id: int
    remote_head_external_id: int
    messages_fetched: int
    batches_processed: int
    remote_gap: bool
    cycle_limited: bool
    source_deferred: bool = False


async def read_durable_telegram_checkpoint(
    store: TelegramCheckpointStore,
    *,
    channel_external_id: str,
) -> int:
    """Read certified polling coverage; unverified history starts at zero."""
    checkpoint, _ = await store.latest_live_checkpoint(
        channel_external_id=channel_external_id,
    )
    if checkpoint is not None:
        return checkpoint
    return 0


@dataclass(frozen=True, slots=True)
class TelegramCheckpointReconciler:
    """Poll forward and converge through the serialized live processor."""

    store: TelegramCheckpointStore
    client: TelegramLiveClientPort
    processor: LiveReconciliationProcessor
    processing_lock: asyncio.Lock
    prepare_cycle: Callable[[], None] | None = None
    archive: RawEventArchivePort | None = None
    sweep_store: TelegramSweepStore | None = None

    async def __call__(
        self,
        request: TelegramReconciliationRequest,
    ) -> TelegramReconciliationResult:
        """Fetch outside the processing lock and serialize only canonical work."""
        channel = request.identity.channel_id
        if self.sweep_store is not None:
            progress = await self.sweep_store.channel_progress(channel_external_id=channel)
            if progress.source_retry_at is not None and progress.source_retry_at > datetime.now(
                UTC
            ):
                return TelegramReconciliationResult(
                    progress.polled_through_id,
                    progress.polled_through_id,
                    progress.polled_through_id,
                    0,
                    0,
                    remote_gap=False,
                    cycle_limited=True,
                    source_deferred=True,
                )
        try:
            return await self._reconcile(request)
        except Exception as error:
            failure = classify_archive_failure(error)
            if failure.kind != "deferred" or self.sweep_store is None:
                if failure.kind == "systemic" and self.sweep_store is not None:
                    await self.sweep_store.defer_source(channel, seconds=5)
                raise
            await self.sweep_store.defer_source(
                channel, seconds=retry_delay(1, 0, failure.retry_after_seconds)
            )
            checkpoint = await read_durable_telegram_checkpoint(
                self.store, channel_external_id=channel
            )
            return TelegramReconciliationResult(
                checkpoint,
                checkpoint,
                checkpoint,
                0,
                0,
                remote_gap=False,
                cycle_limited=True,
                source_deferred=True,
            )

    async def _process_events(
        self,
        request: TelegramReconciliationRequest,
        events: Sequence[LiveTelegramEvent],
        checkpoint: int,
    ) -> None:
        if self.archive is None:
            async with self.processing_lock:
                current = await read_durable_telegram_checkpoint(
                    self.store, channel_external_id=request.identity.channel_id
                )
                await self.processor(
                    identity=request.identity,
                    events=events,
                    resume_after_external_id=max(checkpoint, current),
                    release_sha=request.release_sha,
                    manage_connection=False,
                )
            return
        for event in events:
            landed = await land_live_event(
                self.archive, channel_external_id=request.identity.channel_id, event=event
            )
            eligible = [await self.archive.can_attempt(event_id) for event_id, _ in landed]
            if not any(eligible):
                continue
            try:
                async with self.processing_lock:
                    current = await read_durable_telegram_checkpoint(
                        self.store, channel_external_id=request.identity.channel_id
                    )
                    await self.processor(
                        identity=request.identity,
                        events=(event,),
                        resume_after_external_id=current,
                        release_sha=request.release_sha,
                        manage_connection=False,
                    )
            except Exception as error:
                failure = classify_archive_failure(error)
                for event_id, _ in landed:
                    await self.archive.record_failure(event_id, failure)
                if failure.kind == "systemic":
                    raise

    async def _reconcile(
        self, request: TelegramReconciliationRequest
    ) -> TelegramReconciliationResult:
        if self.prepare_cycle is not None:
            self.prepare_cycle()
        starting = await read_durable_telegram_checkpoint(
            self.store, channel_external_id=request.identity.channel_id
        )
        remote_head = await self.client.latest_message_id(request.identity.username)
        min_id = max(0, starting - request.overlap)
        forward_limit = (
            min(request.max_messages, 400) if self.sweep_store is not None else request.max_messages
        )
        checkpoint = starting
        batches = 0
        fetched = 0
        previous_id = min_id
        async for message in self.client.iter_messages(
            username=request.identity.username,
            min_id=min_id,
            reverse=True,
            limit=forward_limit,
        ):
            try:
                if message.external_message_id <= min_id:
                    continue
                if message.external_message_id <= previous_id:
                    error_message = "forward source response is not ordered"
                    raise ValueError(error_message)
                previous_id = message.external_message_id
                event = LiveTelegramEvent(
                    kind=LiveTelegramEventKind.EDIT
                    if message.edited_at is not None
                    else LiveTelegramEventKind.NEW,
                    message=message,
                )
                await self._process_events(request, (event,), checkpoint)
                checkpoint = await self.store.advance_live_checkpoint(
                    channel_external_id=request.identity.channel_id,
                    external_id=max(checkpoint, message.external_message_id),
                )
                fetched += 1
                batches += 1
            finally:
                if message.media_lease is not None:
                    message.media_lease.release()
            if fetched >= forward_limit:
                break
        # A fully exhausted response can certify empty numeric intervals, never a partial page.
        if fetched < forward_limit:
            checkpoint = await self.store.advance_live_checkpoint(
                channel_external_id=request.identity.channel_id,
                external_id=max(checkpoint, remote_head),
            )
        if self.sweep_store is not None:
            await self._sweep(request, max(0, min(100, request.max_messages - fetched)))
        gap = remote_head > checkpoint
        return TelegramReconciliationResult(
            starting,
            checkpoint,
            remote_head,
            fetched,
            batches,
            gap,
            fetched >= forward_limit and gap,
        )

    async def _sweep(self, request: TelegramReconciliationRequest, budget: int) -> None:
        store = self.sweep_store
        if store is None or budget == 0:
            return
        channel = request.identity.channel_id
        batch = await store.sweep_batch(channel, budget)
        ids = batch.ids
        if not ids:
            return
        observations = await self.client.observe_messages(
            username=request.identity.username, ids=ids
        )
        by_id = {
            item.external_message_id: item
            for item in observations
            if item.external_message_id in ids
        }
        unknown = 0
        for external_id in ids:
            observed = by_id.get(external_id)
            if observed is None or observed.disposition == "unknown":
                unknown += 1
                continue
            if observed.disposition == "deleted":
                event = LiveTelegramEvent(
                    kind=LiveTelegramEventKind.DELETE,
                    deleted_ids=(external_id,),
                    metadata_only=True,
                )
            elif (
                observed.message is not None and observed.message.external_message_id == external_id
            ):
                event = LiveTelegramEvent(
                    kind=LiveTelegramEventKind.EDIT, message=observed.message, metadata_only=True
                )
            else:
                unknown += 1
                continue
            await self._process_events(request, (event,), 0)
        await store.finish_sweep_batch(channel, batch, unknown=unknown)


async def maintain_checkpoint_reconciliation(
    reconciler: TelegramCheckpointReconciler,
    request: TelegramReconciliationRequest,
    *,
    state: WorkerRuntimeState,
    stop: asyncio.Event,
    interval: float,
) -> None:
    """Reconcile immediately, then periodically; fail the supervised stage on error."""
    state.reconciliation_status = CriticalStageStatus.RUNNING
    try:
        while not stop.is_set():
            result = await reconciler(request)
            if not result.source_deferred:
                state.last_reconciliation_at = datetime.now(UTC)
                state.remote_head_external_id = result.remote_head_external_id
            state.local_checkpoint_external_id = result.checkpoint_external_id
            if reconciler.sweep_store is not None:
                progress = await reconciler.sweep_store.channel_progress(
                    channel_external_id=request.identity.channel_id
                )
                state.applied_high_water_id = progress.applied_high_water_id
                state.history_limited = progress.history_limited
            state.last_error_category = None
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                continue
    except asyncio.CancelledError:
        raise
    except Exception as error:
        state.reconciliation_status = CriticalStageStatus.FAILED
        state.record_failure(error)
        raise
