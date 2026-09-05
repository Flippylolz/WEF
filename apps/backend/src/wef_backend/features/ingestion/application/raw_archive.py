"""Bounded original-event draining with truthful terminal progress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Sequence
    from datetime import datetime

    from wef_backend.features.ingestion.application.archive_processing import ArchiveResolution
    from wef_backend.features.ingestion.application.telegram_events import (
        RawEventArchivePort,
        RawEventRecord,
    )
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


MAX_ARCHIVE_BATCH = 25


class ArchiveProcessorPort(Protocol):
    """Process an original archived record under canonical serialization."""

    async def __call__(
        self,
        *,
        record: RawEventRecord,
        identity: TelegramChannelIdentity,
        release_sha: str | None = None,
    ) -> ArchiveResolution:
        """Return the original event's durable canonical receipt."""
        ...


class ArchiveRecoveryPort(Protocol):
    """Durable bounded canary, scheduling and pause boundary."""

    async def claim_batch(self, channel_external_id: str, limit: int) -> Sequence[RawEventRecord]:
        """Return eligible records only if the recovery state permits a batch."""
        ...

    async def finish_batch(self, channel_external_id: str, *, failed: bool) -> None:
        """Verify the canary before expansion or persist its failure pause."""
        ...


@dataclass(frozen=True, slots=True)
class ArchiveDrainResult:
    """Separate attempts from new durable terminal transitions."""

    selected: int = 0
    attempted: int = 0
    newly_terminal: int = 0
    failed: int = 0
    unchanged_terminal: int = 0
    last_committed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RawEventDrainer:
    """Process original UUIDs; acknowledge only verified committed outcomes."""

    archive: RawEventArchivePort
    processor: ArchiveProcessorPort
    identity: TelegramChannelIdentity
    batch_size: int = 25
    recovery: ArchiveRecoveryPort | None = None

    def __post_init__(self) -> None:
        """Keep background recovery bounded."""
        if not 1 <= self.batch_size <= MAX_ARCHIVE_BATCH:
            msg = "archive batch size must be between 1 and 25"
            raise ValueError(msg)

    async def drain_once(
        self, *, release_sha: str | None = None, processing_lock: asyncio.Lock | None = None
    ) -> ArchiveDrainResult:
        """Replay pending evidence; cancellation remains pending and propagates."""
        channel = self.identity.channel_id
        records = (
            await self.recovery.claim_batch(channel, self.batch_size)
            if self.recovery is not None
            else await self.archive.unprocessed_batch(self.batch_size, channel_external_id=channel)
        )
        completed = failed = repeated = 0
        latest = None
        for record in records:
            try:
                if processing_lock is None:
                    receipt = await self.processor(
                        record=record, identity=self.identity, release_sha=release_sha
                    )
                else:
                    async with processing_lock:
                        receipt = await self.processor(
                            record=record, identity=self.identity, release_sha=release_sha
                        )
                if receipt.event_id != record.id:
                    msg = "archive processor returned a different event identity"
                    raise ValueError(msg)  # noqa: TRY301 - reject mismatched processor proof
                changed = await self.archive.mark_attempt(
                    record.id,
                    outcome=(
                        "skipped_non_candidate"
                        if receipt.disposition == "non_candidate"
                        else "processed"
                    ),
                    completed_at=receipt.committed_at,
                )
                completed += int(changed)
                repeated += int(not changed)
                if changed:
                    latest = max(latest, receipt.committed_at) if latest else receipt.committed_at
            except Exception as error:  # noqa: BLE001 - isolate malformed records
                failed += 1
                try:
                    await self.archive.mark_attempt(
                        record.id, outcome="failed", error_category=safe_error_category(error)
                    )
                except Exception as ledger_error:
                    raise error from ledger_error
        if self.recovery is not None and records:
            await self.recovery.finish_batch(channel, failed=failed > 0)
        return ArchiveDrainResult(len(records), len(records), completed, failed, repeated, latest)
