"""Owner read models for offer enrichment controls and parser-gap reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.offer_enrichment import (
    DEFAULT_BATCH_LIMIT,
    MAX_QUEUED_ITEMS,
    OfferAiEnrichmentBatch,
    OfferAiEnrichmentItem,
    OfferAiFieldEvent,
    OfferFieldOrigin,
)

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.features.admin.application.ai_review import AiCurationRuntime


@dataclass(frozen=True, slots=True)
class OfferEnrichmentPreview:
    """Candidate scope before the owner confirms Start batch."""

    candidate_count: int
    preview_limit: int
    queued_items: int
    daily_limit: int
    daily_used: int
    estimated_days: int


@dataclass(frozen=True, slots=True)
class OfferEnrichmentBatchDetail:
    """One batch with item and field-event projections."""

    batch: OfferAiEnrichmentBatch
    items: tuple[OfferAiEnrichmentItem, ...]
    events: tuple[OfferAiFieldEvent, ...]
    active_origins: tuple[OfferFieldOrigin, ...]


class OfferEnrichmentReportingStore(Protocol):
    """Read-only enrichment queries for owner consoles."""

    async def count_owner_queued_items(self, owner_id: UUID) -> int:
        """Count items in queued/running/paused batches for this owner."""
        ...

    async def count_owner_provider_calls_since(self, owner_id: UUID, *, since: datetime) -> int:
        """Count this owner's enrichment provider calls at or after ``since``."""
        ...

    async def list_missing_offer_ids(self, *, limit: int) -> tuple[UUID, ...]:
        """Return offers that still have at least one missing allowlisted field."""
        ...

    async def list_owner_batches(
        self,
        owner_id: UUID,
        *,
        limit: int = 20,
    ) -> tuple[OfferAiEnrichmentBatch, ...]:
        """Return recent enrichment batches for one owner."""
        ...

    async def get_batch(self, batch_id: UUID) -> OfferAiEnrichmentBatch | None:
        """Return one batch by id."""
        ...

    async def list_batch_items(self, batch_id: UUID) -> tuple[OfferAiEnrichmentItem, ...]:
        """Return all items for one batch in ordinal order."""
        ...

    async def list_batch_field_events(self, batch_id: UUID) -> tuple[OfferAiFieldEvent, ...]:
        """Return append-only field events for one batch."""
        ...

    async def list_owner_parser_gap_events(
        self,
        owner_id: UUID,
        *,
        limit: int = 500,
    ) -> tuple[OfferAiFieldEvent, ...]:
        """Return redacted parser-gap events across an owner's batches."""
        ...

    async def list_active_ai_origins(self, offer_id: UUID) -> tuple[OfferFieldOrigin, ...]:
        """Return active AI origins for one offer."""
        ...


class PreviewOfferEnrichmentBatch:
    """Estimate scope and free-tier pacing before starting a batch."""

    def __init__(
        self,
        store: OfferEnrichmentReportingStore,
        runtime: AiCurationRuntime,
    ) -> None:
        """Initialize collaborators."""
        self._store = store
        self._runtime = runtime

    async def __call__(
        self,
        *,
        owner_id: UUID,
        limit: int = DEFAULT_BATCH_LIMIT,
    ) -> OfferEnrichmentPreview:
        """Return candidate counts and pacing estimates for the owner."""
        preview_limit = min(limit, DEFAULT_BATCH_LIMIT)
        candidates = await self._store.list_missing_offer_ids(limit=preview_limit)
        queued = await self._store.count_owner_queued_items(owner_id)
        since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        used = await self._store.count_owner_provider_calls_since(owner_id, since=since)
        remaining_today = max(self._runtime.daily_limit - used, 0)
        effective = min(len(candidates), preview_limit, max(MAX_QUEUED_ITEMS - queued, 0))
        if remaining_today <= 0:
            estimated_days = max(
                (effective + self._runtime.daily_limit - 1) // self._runtime.daily_limit,
                1,
            )
        else:
            overflow = max(effective - remaining_today, 0)
            estimated_days = 1 + (
                (overflow + self._runtime.daily_limit - 1) // self._runtime.daily_limit
                if overflow
                else 0
            )
        return OfferEnrichmentPreview(
            candidate_count=len(candidates),
            preview_limit=preview_limit,
            queued_items=queued,
            daily_limit=self._runtime.daily_limit,
            daily_used=used,
            estimated_days=estimated_days,
        )


class ListOfferEnrichmentBatches:
    """List recent owner batches."""

    def __init__(self, store: OfferEnrichmentReportingStore) -> None:
        """Initialize the store."""
        self._store = store

    async def __call__(
        self,
        *,
        owner_id: UUID,
        limit: int = 20,
    ) -> tuple[OfferAiEnrichmentBatch, ...]:
        """Return recent batches newest-first."""
        return await self._store.list_owner_batches(owner_id, limit=limit)


class GetOfferEnrichmentBatchDetail:
    """Load one batch with items, events, and active origins."""

    def __init__(self, store: OfferEnrichmentReportingStore) -> None:
        """Initialize the store."""
        self._store = store

    async def __call__(
        self,
        *,
        owner_id: UUID,
        batch_id: UUID,
    ) -> OfferEnrichmentBatchDetail:
        """Return one owner-owned batch detail or deny."""
        batch = await self._store.get_batch(batch_id)
        if batch is None or batch.owner_user_id != owner_id:
            message = "batch not found"
            raise AdminDeniedError(message)
        items = await self._store.list_batch_items(batch_id)
        events = await self._store.list_batch_field_events(batch_id)
        origins: list[OfferFieldOrigin] = []
        for item in items:
            origins.extend(await self._store.list_active_ai_origins(item.offer_id))
        deduped = {(origin.offer_id, origin.field_name): origin for origin in origins}
        return OfferEnrichmentBatchDetail(
            batch=batch,
            items=items,
            events=events,
            active_origins=tuple(deduped.values()),
        )


class ListParserGapEvents:
    """Return bounded parser-gap field events for reporting/export."""

    def __init__(self, store: OfferEnrichmentReportingStore) -> None:
        """Initialize the store."""
        self._store = store

    async def __call__(
        self,
        *,
        owner_id: UUID,
        limit: int = 500,
    ) -> tuple[OfferAiFieldEvent, ...]:
        """Return newest parser-gap events for the owner."""
        return await self._store.list_owner_parser_gap_events(owner_id, limit=limit)
