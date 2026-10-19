"""Owner console lifecycle, redacted exports and invalid form boundaries."""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeChatCompletions,
    FakeClock,
    FakeLocationAdminStore,
    FakeOfferAiEnrichmentStore,
    active_ai_runtime,
)
from tests.test_admin_api import _csrf_from_html, _owner_session, admin_client
from tests.test_admin_places_console import _detail, _summary
from tests.test_offer_enrichment import _NOW, _field, _process, _revision, _snapshot, _start
from wef_backend.features.admin.application.offer_enrichment import BatchState

_ENRICHMENT = "/admin/offer-enrichment"
_PLACES = "/admin/places"


@pytest.mark.parametrize("state", list(BatchState))
async def test_batch_detail_controls_follow_persisted_lifecycle(state: BatchState) -> None:
    """Only applicable process, pause, resume and revert actions are rendered."""
    snapshot = _snapshot()
    enrichment = FakeOfferAiEnrichmentStore(snapshots={snapshot.id: snapshot})
    async with admin_client(
        enrichment_store=enrichment, runtime=active_ai_runtime(), clock=FakeClock(_NOW)
    ) as (client, identity):
        await _owner_session(client, identity)
        owner = next(account.id for account in identity.accounts.values())
        empty = await client.get(_ENRICHMENT)
        assert "No batches yet" in empty.text
        batch = await _start(enrichment, owner_id=owner)
        enrichment.batches[batch.id] = replace(batch, state=state)
        home = await client.get(_ENRICHMENT)
        assert str(batch.id) in home.text
        detail = await client.get(f"{_ENRICHMENT}/batch?batch_id={batch.id}")
        assert detail.status_code == 200
        body = detail.text
        assert ("Process next batch" in body) == (
            state in {BatchState.QUEUED, BatchState.RUNNING, BatchState.PAUSED}
        )
        assert (">Pause</button>" in body) == (state in {BatchState.QUEUED, BatchState.RUNNING})
        assert (">Resume</button>" in body) == (state is BatchState.PAUSED)
        assert (">Revert" in body) == (
            state in {BatchState.COMPLETED, BatchState.PAUSED, BatchState.FAILED}
        )


@pytest.mark.parametrize("operation", ["process", "pause", "resume", "revert"])
@pytest.mark.parametrize("owned", [False, True])
async def test_batch_mutations_redirect_after_owned_success_or_missing_batch(
    operation: str, *, owned: bool
) -> None:
    """Owner actions have stable redirects and never reveal a missing batch body."""
    snapshot, revision = _snapshot(), _revision("Piętro 4 przy metrze.")
    enrichment = FakeOfferAiEnrichmentStore(
        snapshots={snapshot.id: snapshot}, sources={snapshot.id: (revision,)}
    )
    async with admin_client(
        enrichment_store=enrichment,
        runtime=active_ai_runtime(),
        clock=FakeClock(_NOW),
        provider=FakeChatCompletions(payload={"fields": [_field(revision.revision_id)]}),
    ) as (client, identity):
        await _owner_session(client, identity)
        owner = next(account.id for account in identity.accounts.values())
        batch = await _start(enrichment, owner_id=owner)
        if operation == "resume":
            enrichment.batches[batch.id] = replace(batch, state=BatchState.PAUSED)
        preview = await client.get(f"{_ENRICHMENT}/preview")
        selected = batch.id if owned else uuid4()
        response = await client.post(
            f"{_ENRICHMENT}/{operation}",
            data={"batch_id": str(selected), "csrftoken": _csrf_from_html(preview.text)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"{_ENRICHMENT}/batch?batch_id={selected}"
        if not owned:
            assert enrichment.batches[batch.id].processed_count == 0


async def test_enrichment_missing_and_foreign_details_and_empty_start_are_bounded() -> None:
    """Missing identifiers and an empty cohort return to a safe owner page."""
    enrichment = FakeOfferAiEnrichmentStore()
    async with admin_client(enrichment_store=enrichment, runtime=active_ai_runtime()) as (
        client,
        identity,
    ):
        await _owner_session(client, identity)
        for path in ("/batch", f"/batch?batch_id={uuid4()}"):
            response = await client.get(_ENRICHMENT + path, follow_redirects=False)
            assert response.status_code == 303
            assert response.headers["location"] == _ENRICHMENT
        preview = await client.get(f"{_ENRICHMENT}/preview")
        response = await client.post(
            f"{_ENRICHMENT}/start",
            data={"csrftoken": _csrf_from_html(preview.text), "limit": "20"},
            follow_redirects=False,
        )
        assert response.headers["location"] == f"{_ENRICHMENT}/preview?error=denied"
    assert not enrichment.batches


async def test_disabled_enrichment_preview_redirects() -> None:
    """Disabled environments cannot open the start form via a direct preview link."""
    async with admin_client() as (client, identity):
        await _owner_session(client, identity)
        response = await client.get(f"{_ENRICHMENT}/preview", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == _ENRICHMENT


async def test_parser_gap_html_and_csv_preserve_metadata_without_source_text() -> None:
    """Empty and populated exports share the typed redacted reporting contract."""
    snapshot, revision = _snapshot(), _revision("Piętro 4 przy metrze. private source context")
    enrichment = FakeOfferAiEnrichmentStore(
        snapshots={snapshot.id: snapshot}, sources={snapshot.id: (revision,)}
    )
    async with admin_client(
        enrichment_store=enrichment, runtime=active_ai_runtime(), clock=FakeClock(_NOW)
    ) as (client, identity):
        await _owner_session(client, identity)
        empty = await client.get(f"{_ENRICHMENT}/parser-gaps/export.csv")
        assert list(csv.DictReader(io.StringIO(empty.text))) == []
        empty_page = await client.get(f"{_ENRICHMENT}/parser-gaps")
        assert "No parser-gap events" in empty_page.text
        owner = next(account.id for account in identity.accounts.values())
        batch = await _start(enrichment, owner_id=owner)
        await _process(
            enrichment,
            FakeChatCompletions(payload={"fields": [_field(revision.revision_id)]}),
            owner_id=owner,
            batch_id=batch.id,
        )
        assert enrichment.events
        page = await client.get(f"{_ENRICHMENT}/parser-gaps")
        assert "floor_label" in page.text
        assert revision.text_original not in page.text
        report = await client.get(f"{_ENRICHMENT}/parser-gaps/export.csv")
        rows = list(csv.DictReader(io.StringIO(report.text)))
        assert len(rows) == 1
        assert rows[0]["field_name"] == "floor_label"
        assert rows[0]["typed_value"] == "4"
        assert "private source context" not in report.text
        assert "attachment" in report.headers["content-disposition"]


@pytest.mark.parametrize("path", ["/set-point", "/ai-review"])
@pytest.mark.parametrize("identifier", ["", "invalid", "00000000-0000-0000-0000-000000000000"])
async def test_location_pages_redirect_for_invalid_or_missing_records(
    path: str, identifier: str
) -> None:
    """A stale or malformed owner link retains the selected list search/filter."""
    field = "location_id" if path == "/set-point" else "run_id"
    async with admin_client() as (client, identity):
        await _owner_session(client, identity)
        response = await client.get(
            f"{_PLACES}{path}?{field}={identifier}&status=all&search=synthetic",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "status=all" in response.headers["location"]
        assert "search=synthetic" in response.headers["location"]


@pytest.mark.parametrize("path", ["/ai-review/generate", "/ai-review/apply"])
async def test_ai_review_forms_refuse_invalid_identity_and_status(path: str) -> None:
    """Malformed form identifiers and enum filters safely return to pending."""
    summary = _summary()
    places = FakeLocationAdminStore(summaries=[summary], details={summary.id: _detail(summary)})
    async with admin_client(places=places) as (client, identity):
        await _owner_session(client, identity)
        page = await client.get(_PLACES + "?status=unknown")
        assert "status=pending" in page.text
        response = await client.post(
            _PLACES + path,
            data={
                "location_id": "invalid",
                "run_id": "invalid",
                "status": "invalid",
                "csrftoken": _csrf_from_html(page.text),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == _PLACES + "?status=pending"


@pytest.mark.parametrize("mode", ["manual", "no_candidate", "no_price", "rejected"])
async def test_location_picker_handles_optional_evidence_and_decided_rows(mode: str) -> None:
    """Manual coordinates, absent candidates/prices and rejected rows render correctly."""
    summary = _summary(review_status="rejected" if mode == "rejected" else "needs_review")
    detail = _detail(summary)
    if mode == "manual":
        detail = replace(detail, latitude=Decimal("52.25"), longitude=Decimal("21.02"))
    elif mode == "no_candidate":
        detail = replace(detail, candidate=None)
    elif mode == "no_price":
        detail = replace(
            detail, offers=(replace(detail.offers[0], price_min_minor=None, price_max_minor=None),)
        )
    places = FakeLocationAdminStore(summaries=[summary], details={summary.id: detail})
    async with admin_client(places=places) as (client, identity):
        await _owner_session(client, identity)
        listing = await client.get(_PLACES + "?status=all")
        if mode == "rejected":
            assert "Unresolve" in listing.text
        picker = await client.get(f"{_PLACES}/set-point?location_id={summary.id}&search=synthetic")
        assert picker.status_code == 200
        if mode == "no_candidate":
            assert "None retained" in picker.text
        if mode == "manual":
            assert "52.25" in picker.text
            assert "21.02" in picker.text
        response = await client.post(
            _PLACES + "/set-point",
            data={
                "location_id": str(summary.id),
                "longitude": "invalid",
                "latitude": "52.2",
                "search": "synthetic",
                "csrftoken": _csrf_from_html(picker.text),
            },
            follow_redirects=False,
        )
        assert "search=synthetic" in response.headers["location"]
