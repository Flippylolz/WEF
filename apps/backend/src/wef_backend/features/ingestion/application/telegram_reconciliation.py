"""Checkpoint-driven completeness loop for the live Telegram worker."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import CriticalStageStatus

MAX_RECONCILIATION_BATCH_SIZE = 100
MAX_RECONCILIATION_MESSAGES = 500

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wef_backend.features.ingestion.application.telegram_events import (
        LiveEventBatchResult,
    )
    from wef_backend.features.ingestion.application.telegram_live import (
        TelegramLiveClientPort,
    )
    from wef_backend.features.ingestion.application.telegram_worker_liveness import (
        WorkerRuntimeState,
    )
    from wef_backend.features.ingestion.domain.telegram_channel import (
        TelegramChannelIdentity,
    )


class TelegramCheckpointStore(Protocol):
    """Read the durable live cursor and persisted fallback boundary."""

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


async def read_durable_telegram_checkpoint(
    store: TelegramCheckpointStore,
    *,
    channel_external_id: str,
) -> int:
    """Prefer the live cursor and fall back to persisted history on first run."""
    checkpoint, _ = await store.latest_live_checkpoint(
        channel_external_id=channel_external_id,
    )
    if checkpoint is not None:
        return checkpoint
    return await store.max_external_message_id(channel_external_id=channel_external_id)


@dataclass(frozen=True, slots=True)
class TelegramCheckpointReconciler:
    """Poll forward and converge through the serialized live processor."""

    store: TelegramCheckpointStore
    client: TelegramLiveClientPort
    processor: LiveReconciliationProcessor
    processing_lock: asyncio.Lock

    async def __call__(
        self,
        request: TelegramReconciliationRequest,
    ) -> TelegramReconciliationResult:
        """Run one bounded cycle while excluding passive-event persistence."""
        async with self.processing_lock:
            starting_checkpoint = await read_durable_telegram_checkpoint(
                self.store,
                channel_external_id=request.identity.channel_id,
            )
            remote_head = await self.client.latest_message_id(request.identity.username)
            min_id = max(0, starting_checkpoint - request.overlap)
            messages = [
                message
                async for message in self.client.iter_messages(
                    username=request.identity.username,
                    min_id=min_id,
                    reverse=True,
                    limit=request.max_messages,
                )
                if message.external_message_id > min_id
            ]
            messages.sort(key=lambda message: message.external_message_id)
            checkpoint = starting_checkpoint
            batches = 0
            for offset in range(0, len(messages), request.batch_size):
                batch = messages[offset : offset + request.batch_size]
                result = await self.processor(
                    identity=request.identity,
                    events=tuple(
                        LiveTelegramEvent(
                            kind=(
                                LiveTelegramEventKind.EDIT
                                if message.edited_at is not None
                                else LiveTelegramEventKind.NEW
                            ),
                            message=message,
                        )
                        for message in batch
                    ),
                    resume_after_external_id=checkpoint,
                    release_sha=request.release_sha,
                    manage_connection=False,
                )
                checkpoint = max(checkpoint, result.checkpoint_external_message_id)
                batches += 1
            remote_gap = remote_head > checkpoint
            return TelegramReconciliationResult(
                starting_checkpoint_external_id=starting_checkpoint,
                checkpoint_external_id=checkpoint,
                remote_head_external_id=remote_head,
                messages_fetched=len(messages),
                batches_processed=batches,
                remote_gap=remote_gap,
                cycle_limited=(len(messages) >= request.max_messages and remote_gap),
            )


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
            state.last_reconciliation_at = datetime.now(UTC)
            state.remote_head_external_id = result.remote_head_external_id
            state.local_checkpoint_external_id = result.checkpoint_external_id
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
