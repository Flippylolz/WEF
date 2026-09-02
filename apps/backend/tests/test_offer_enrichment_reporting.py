"""Unit coverage for owner enrichment preview and batch detail read models."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.fakes import FakeOfferAiEnrichmentStore, active_ai_runtime
from tests.test_offer_enrichment import _revision, _snapshot
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    ItemState,
    OfferAiEnrichmentBatch,
    OfferAiEnrichmentItem,
    offer_input_fingerprint,
)
from wef_backend.features.admin.application.offer_enrichment_reporting import (
    GetOfferEnrichmentBatchDetail,
    ListOfferEnrichmentBatches,
    ListParserGapEvents,
    PreviewOfferEnrichmentBatch,
)

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_OWNER = UUID("11111111-1111-4111-8111-111111111111")
_OTHER = UUID("22222222-2222-4222-8222-222222222222")


def _batch(*, owner_id: UUID = _OWNER) -> OfferAiEnrichmentBatch:
    return OfferAiEnrichmentBatch(
        id=uuid4(),
        owner_user_id=owner_id,
        scope_json={"limit": 25},
        candidate_count=1,
        model="test-model",
        prompt_version="p1",
        schema_version="s1",
        state=BatchState.QUEUED,
        checkpoint_ordinal=0,
        processed_count=0,
        applied_count=0,
        skipped_count=0,
        failed_count=0,
        failure_category=None,
        created_at=_NOW,
        started_at=None,
        finished_at=None,
    )


async def test_preview_counts_missing_offers_and_pacing() -> None:
    """Preview reports candidate scope, queue depth, and free-tier estimates."""
    store = FakeOfferAiEnrichmentStore()
    offer_id = uuid4()
    store.snapshots[offer_id] = _snapshot(offer_id)
    preview = await PreviewOfferEnrichmentBatch(store, active_ai_runtime())(
        owner_id=_OWNER,
        limit=25,
    )
    assert preview.candidate_count == 1
    assert preview.preview_limit == 20
    assert preview.queued_items == 0
    assert preview.daily_limit == active_ai_runtime().daily_limit
    assert preview.estimated_days >= 1


async def test_preview_estimates_days_when_daily_budget_is_exhausted() -> None:
    """When today's budget is gone, pacing rolls work into future days."""
    store = FakeOfferAiEnrichmentStore()
    runtime = active_ai_runtime()
    today = datetime.now(UTC)
    batch_id = uuid4()
    store.batches[batch_id] = OfferAiEnrichmentBatch(
        id=batch_id,
        owner_user_id=_OWNER,
        scope_json={"limit": 20},
        candidate_count=20,
        model="test-model",
        prompt_version="p1",
        schema_version="s1",
        state=BatchState.COMPLETED,
        checkpoint_ordinal=20,
        processed_count=20,
        applied_count=0,
        skipped_count=0,
        failed_count=20,
        failure_category=None,
        created_at=_NOW,
        started_at=_NOW,
        finished_at=_NOW,
    )
    for ordinal in range(runtime.daily_limit):
        snapshot = _snapshot()
        revision = _revision()
        store.snapshots[snapshot.id] = snapshot
        item_id = uuid4()
        store.items[item_id] = OfferAiEnrichmentItem(
            id=item_id,
            batch_id=batch_id,
            offer_id=snapshot.id,
            ordinal=ordinal,
            input_fingerprint=offer_input_fingerprint(
                snapshot,
                (revision.revision_id,),
                (revision.checksum,),
            ),
            state=ItemState.FAILED,
            outcome=None,
            attempt_count=1,
            provider_called_at=today,
            created_at=today,
            processed_at=today,
        )
    extra_offer = _snapshot()
    store.snapshots[extra_offer.id] = extra_offer
    preview = await PreviewOfferEnrichmentBatch(store, runtime)(
        owner_id=_OWNER,
        limit=20,
    )
    assert preview.daily_used == runtime.daily_limit
    assert preview.estimated_days >= 1


async def test_batch_detail_returns_owner_batch() -> None:
    """Owners can load their own batch detail read model."""
    store = FakeOfferAiEnrichmentStore()
    batch = _batch()
    store.batches[batch.id] = batch
    detail = await GetOfferEnrichmentBatchDetail(store)(
        owner_id=_OWNER,
        batch_id=batch.id,
    )
    assert detail.batch.id == batch.id
    assert detail.items == ()
    assert detail.events == ()
    assert detail.active_origins == ()


async def test_list_batches_returns_recent_owner_batches() -> None:
    """Recent batches are returned newest-first for the owner."""
    store = FakeOfferAiEnrichmentStore()
    older = replace(_batch(), created_at=_NOW.replace(day=1))
    newer = replace(_batch(), created_at=_NOW.replace(day=2))
    store.batches[older.id] = older
    store.batches[newer.id] = newer
    batches = await ListOfferEnrichmentBatches(store)(owner_id=_OWNER, limit=10)
    assert [batch.id for batch in batches] == [newer.id, older.id]


async def test_list_parser_gap_events_returns_owner_events() -> None:
    """Parser-gap events are scoped to the requesting owner."""
    store = FakeOfferAiEnrichmentStore()
    events = await ListParserGapEvents(store)(owner_id=_OWNER, limit=10)
    assert events == ()


async def test_batch_detail_denies_foreign_owner() -> None:
    """Owners cannot load another owner's batch detail."""
    store = FakeOfferAiEnrichmentStore()
    batch = _batch(owner_id=_OTHER)
    store.batches[batch.id] = batch
    with pytest.raises(AdminDeniedError, match="batch not found"):
        await GetOfferEnrichmentBatchDetail(store)(
            owner_id=_OWNER,
            batch_id=batch.id,
        )
