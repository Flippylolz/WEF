"""HTTP coverage for the owner offer enrichment console."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from tests.fakes import (
    FakeClock,
    FakeOfferAiEnrichmentStore,
    active_ai_runtime,
)
from tests.test_admin_api import _csrf_from_html, _owner_session, admin_client
from tests.test_offer_enrichment import _revision, _snapshot
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    FieldEventOutcome,
    OfferAiEnrichmentBatch,
    OfferAiFieldEvent,
)

_PATH = "/admin/offer-enrichment"
_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_SOURCE = "Piętro 4 przy metrze."
_PHONE = "+48111222333"


async def test_anonymous_user_cannot_open_offer_enrichment() -> None:
    """Non-owner sessions are redirected away from enrichment routes."""
    async with admin_client(runtime=active_ai_runtime()) as (client, _):
        response = await client.get(_PATH, follow_redirects=False)
    assert response.status_code in {302, 303, 401, 403}


async def test_disabled_runtime_shows_feature_gate() -> None:
    """Owners see a disable notice when AI curation is inactive."""
    async with admin_client() as (client, store):
        await _owner_session(client, store)
        response = await client.get(_PATH)
    assert response.status_code == 200
    assert b"AI curation is disabled in this environment" in response.content


async def test_preview_warns_before_start_batch() -> None:
    """Preview shows immutable scope and the single Start confirmation."""
    enrichment = FakeOfferAiEnrichmentStore()
    offer_id = uuid4()
    enrichment.snapshots[offer_id] = _snapshot(offer_id)
    enrichment.sources[offer_id] = (_revision(_SOURCE),)
    async with admin_client(
        enrichment_store=enrichment,
        runtime=active_ai_runtime(),
        clock=FakeClock(moment=_NOW),
    ) as (client, store):
        await _owner_session(client, store)
        response = await client.get(f"{_PATH}/preview")
    assert response.status_code == 200
    assert b"Start batch" in response.content
    assert b"only confirmation" in response.content
    assert b"Eligible offers in preview: 1" in response.content


async def test_owner_can_start_batch_with_csrf() -> None:
    """Start batch creates one owner-owned cohort and redirects to detail."""
    enrichment = FakeOfferAiEnrichmentStore()
    offer_id = uuid4()
    enrichment.snapshots[offer_id] = _snapshot(offer_id)
    enrichment.sources[offer_id] = (_revision(_SOURCE),)
    async with admin_client(
        enrichment_store=enrichment,
        runtime=active_ai_runtime(),
        clock=FakeClock(moment=_NOW),
    ) as (client, store):
        await _owner_session(client, store)
        preview = await client.get(f"{_PATH}/preview")
        start = await client.post(
            f"{_PATH}/start",
            data={
                "csrftoken": _csrf_from_html(preview.text),
                "limit": "25",
            },
            follow_redirects=False,
        )
        assert start.status_code == 303
        detail = await client.get(start.headers["location"])
    assert detail.status_code == 200
    assert b"State:" in detail.content
    assert str(offer_id).encode() in detail.content


async def test_parser_gap_export_is_redacted() -> None:
    """JSON export includes typed metadata but no raw source or contacts."""
    enrichment = FakeOfferAiEnrichmentStore()
    batch_id = uuid4()
    item_id = uuid4()
    offer_id = uuid4()
    revision_id = uuid4()
    owner_id = uuid4()
    enrichment.batches[batch_id] = OfferAiEnrichmentBatch(
        id=batch_id,
        owner_user_id=owner_id,
        scope_json={},
        candidate_count=1,
        model="test-model",
        prompt_version="p1",
        schema_version="s1",
        state=BatchState.COMPLETED,
        checkpoint_ordinal=1,
        processed_count=1,
        applied_count=1,
        skipped_count=0,
        failed_count=0,
        failure_category=None,
        created_at=_NOW,
        started_at=_NOW,
        finished_at=_NOW,
    )
    enrichment.events.append(
        OfferAiFieldEvent(
            id=uuid4(),
            batch_id=batch_id,
            batch_item_id=item_id,
            offer_id=offer_id,
            field_name="floor_label",
            proposed_value="4",
            applied_value="4",
            outcome=FieldEventOutcome.APPLIED,
            reason="applied",
            source_message_revision_id=revision_id,
            source_start=0,
            source_end=8,
            source_fingerprint="f" * 64,
            parser_version="parser-test",
            model="test-model",
            prompt_version="p1",
            schema_version="s1",
            confidence="high",
            provider_request_id="req-1",
            token_input=100,
            token_output=20,
            latency_ms=50,
            actor_id="owner",
            created_at=_NOW,
        ),
    )
    async with admin_client(
        enrichment_store=enrichment,
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        owner_id = next(account.id for account in store.accounts.values())
        enrichment.batches[batch_id] = OfferAiEnrichmentBatch(
            id=batch_id,
            owner_user_id=owner_id,
            scope_json={},
            candidate_count=1,
            model="test-model",
            prompt_version="p1",
            schema_version="s1",
            state=BatchState.COMPLETED,
            checkpoint_ordinal=1,
            processed_count=1,
            applied_count=1,
            skipped_count=0,
            failed_count=0,
            failure_category=None,
            created_at=_NOW,
            started_at=_NOW,
            finished_at=_NOW,
        )
        response = await client.get(f"{_PATH}/parser-gaps/export.json")
    assert response.status_code == 200
    payload = json.loads(response.text)
    assert payload[0]["field_name"] == "floor_label"
    assert payload[0]["typed_value"] == "4"
    assert _PHONE not in response.text
    assert _SOURCE not in response.text
    assert "text_original" not in response.text
