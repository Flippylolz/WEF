"""Unit coverage for owner enrichment preview and batch detail read models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.fakes import FakeOfferAiEnrichmentStore, active_ai_runtime
from tests.test_offer_enrichment import _snapshot
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    OfferAiEnrichmentBatch,
)
from wef_backend.features.admin.application.offer_enrichment_reporting import (
    GetOfferEnrichmentBatchDetail,
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
