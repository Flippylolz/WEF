"""Distinct progress and bounded source-history observation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.ingestion.application.telegram_live import LiveTelegramMessage


@dataclass(frozen=True, slots=True)
class ChannelProgress:
    """High-water is applied evidence, polling is traversal, and history can remain unknown."""

    applied_high_water_id: int = 0
    polled_through_id: int = 0
    history_limited: bool = True
    source_retry_at: datetime | None = None
    last_applied_at: datetime | None = None
    last_polled_at: datetime | None = None
    last_sweep_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """Only explicit source evidence distinguishes deletion from unavailable history."""

    external_message_id: int
    disposition: Literal["present", "deleted", "unknown"]
    message: LiveTelegramMessage | None = None


@dataclass(frozen=True, slots=True)
class SweepBatch:
    """Lease token prevents a delayed observation from advancing a later sweep."""

    ids: tuple[int, ...] = ()
    token: UUID | None = None


class TelegramSweepStore(Protocol):
    """Durable old-known-ID continuation and per-source backoff."""

    async def channel_progress(self, *, channel_external_id: str) -> ChannelProgress:
        """Read committed traversal and applied meanings together."""
        ...

    async def sweep_batch(self, channel_external_id: str, limit: int) -> SweepBatch:
        """Snapshot a bounded known-ID sweep, then return its next page."""
        ...

    async def finish_sweep_batch(
        self, channel_external_id: str, batch: SweepBatch, *, unknown: int
    ) -> None:
        """Advance only after each observation has a durable classified outcome."""
        ...

    async def defer_source(self, channel_external_id: str, *, seconds: float) -> None:
        """Persist source backoff outside processing locks."""
        ...
