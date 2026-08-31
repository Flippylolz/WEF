"""HTTP coverage for the owner Review with AI console."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from tests.fakes import (
    FakeChatCompletions,
    FakeClock,
    FakeLocationAdminStore,
    FakePlaceAiReviewStore,
    active_ai_runtime,
)
from tests.test_admin_api import _csrf_from_html, _owner_session, admin_client
from tests.test_admin_places_console import _detail, _summary
from wef_backend.features.admin.application.ai_review import (
    AiApplyStatus,
    LocationAiSnapshot,
    PlaceReviewVerdict,
    ProviderOutcome,
    SourceRevisionEvidence,
)

if TYPE_CHECKING:
    from httpx import AsyncClient, Response

_PLACES_PATH = "/admin/places"
_NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def _snapshot_for(
    summary_id: UUID, *, name: str, address: str, district: str
) -> LocationAiSnapshot:
    return LocationAiSnapshot(
        id=summary_id,
        display_name=name,
        display_address=address,
        district=district,
        review_status="needs_review",
        updated_at=_NOW,
        normalized_address_hash="a" * 64,
    )


def _revision(text: str = "Źródło: Osiedle Przykład ul. Nowa 2 Mokotów") -> SourceRevisionEvidence:
    return SourceRevisionEvidence(
        revision_id=uuid4(),
        checksum="b" * 64,
        published_at=_NOW,
        text_original=text,
    )


def _payload(
    revision_id: UUID,
    *,
    name: str = "Osiedle Przykład",
    warning: str = "low_confidence",
) -> dict[str, object]:
    evidence = [str(revision_id)]
    return {
        "verdict": PlaceReviewVerdict.CORRECTIONS_PROPOSED.value,
        "fields": [
            {
                "field_name": "display_name",
                "action": "correct",
                "current_value": "Marszałkowska 1",
                "proposed_value": name,
                "confidence": "high",
                "evidence_revision_ids": evidence,
                "rationale_code": "supported",
            },
            {
                "field_name": "display_address",
                "action": "correct",
                "current_value": "ul. Marszałkowska 1, Warszawa",
                "proposed_value": "ul. Nowa 2, Warszawa",
                "confidence": "medium",
                "evidence_revision_ids": evidence,
                "rationale_code": "supported",
            },
            {
                "field_name": "district",
                "action": "keep",
                "current_value": "Śródmieście",
                "proposed_value": None,
                "confidence": "high",
                "evidence_revision_ids": evidence,
                "rationale_code": "supported",
            },
        ],
        "warnings": [warning],
    }


async def _generate_review(
    client: AsyncClient,
    *,
    location_id: UUID,
    html: str,
) -> Response:
    token = _csrf_from_html(html)
    return await client.post(
        f"{_PLACES_PATH}/ai-review/generate",
        data={
            "location_id": str(location_id),
            "status": "pending",
            "search": "",
            "csrftoken": token,
        },
        follow_redirects=False,
    )


async def test_review_with_ai_absent_when_disabled() -> None:
    """The list still works and omits the AI action when the gate is closed."""
    summary = _summary()
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        page = await client.get(_PLACES_PATH)
        assert page.status_code == 200
        assert "ul. Marszałkowska 1" in page.text
        assert "Review with AI" not in page.text
        assert "ai-review" not in page.text


async def test_anonymous_cannot_reach_ai_review_routes() -> None:
    """Unauthenticated browsers never see generate or apply."""
    async with admin_client() as (client, _store):
        generate = await client.post(
            f"{_PLACES_PATH}/ai-review/generate",
            data={"location_id": str(uuid4())},
            follow_redirects=False,
        )
        review = await client.get(
            f"{_PLACES_PATH}/ai-review?run_id={uuid4()}",
            follow_redirects=False,
        )
        apply = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={"run_id": str(uuid4())},
            follow_redirects=False,
        )
        assert generate.status_code in {302, 303, 401, 403}
        assert review.status_code in {302, 303, 401, 403}
        assert apply.status_code in {302, 303, 401, 403}


async def test_generate_shows_coverage_diffs_and_unselected_fields() -> None:
    """Generate redirects to a result that never treats omitted sources as reviewed."""
    summary = _summary()
    revision = _revision()
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
        extra_source_count=2,
    )
    payload = _payload(revision.revision_id)
    places = FakeLocationAdminStore(summaries=[summary], details={summary.id: _detail(summary)})
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(payload=payload),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        assert "Review with AI" in listing.text
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        assert generated.status_code == 303
        location = generated.headers["location"]
        assert "/admin/places/ai-review?run_id=" in location
        page = await client.get(location)
        body = page.text
        assert page.status_code == 200
        assert "Reviewed 1 source description." in body
        assert "2 additional descriptions were omitted and were not reviewed." in body
        assert "low_confidence" in body
        assert "Osiedle Przykład" in body
        assert "ul. Nowa 2, Warszawa" in body
        assert "corrections_proposed" in body
        assert "name='selected_fields'" in body
        assert "checked" not in body.lower()
        assert "Apply selected fields" in body
        assert "Coordinates are not changed" in body
        assert "color-scheme:dark" in body
        assert "css/admin.css" in body
        assert "background:var(--wef-canvas)" in body
        assert "color-scheme:light" not in body


async def test_prompt_like_output_is_escaped() -> None:
    """Provider text cannot execute as HTML."""
    summary = _summary()
    revision = _revision()
    xss = "<script>alert(1)</script>"
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    payload = _payload(revision.revision_id, name=xss, warning="prompt_injection_ignored")
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(payload=payload),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        page = await client.get(generated.headers["location"])
        assert "<script>" not in page.text
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page.text


async def test_apply_requires_csrf_and_origin() -> None:
    """Apply is a separate owner POST with CSRF and origin checks."""
    summary = _summary()
    revision = _revision()
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(payload=_payload(revision.revision_id)),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        review_page = await client.get(generated.headers["location"])
        token = _csrf_from_html(review_page.text)
        run_id = next(iter(review_store.runs))
        missing = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={"run_id": str(run_id), "selected_fields": "display_name"},
            follow_redirects=False,
        )
        assert missing.status_code in {400, 403}
        cross = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            headers={"Origin": "https://evil.example"},
            data={
                "run_id": str(run_id),
                "selected_fields": "display_name",
                "csrftoken": token,
            },
            follow_redirects=False,
        )
        assert cross.status_code == 403


async def test_apply_selected_address_returns_to_review_and_links_point() -> None:
    """Applying a spatial field is a separate POST and points at E18 verification."""
    summary = _summary()
    revision = _revision()
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(payload=_payload(revision.revision_id)),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        review_page = await client.get(generated.headers["location"])
        token = _csrf_from_html(review_page.text)
        run_id = next(iter(review_store.runs))
        empty = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={"run_id": str(run_id), "status": "pending", "csrftoken": token},
            follow_redirects=False,
        )
        assert empty.status_code == 303
        empty_page = await client.get(empty.headers["location"])
        assert "Select at least one proposed correction" in empty_page.text
        applied = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={
                "run_id": str(run_id),
                "status": "pending",
                "selected_fields": "display_address",
                "csrftoken": token,
            },
            follow_redirects=False,
        )
        assert applied.status_code == 303
        result = await client.get(applied.headers["location"])
        assert "needs_review" in result.text
        assert f"/admin/places/set-point?location_id={summary.id}" in result.text
        assert "Apply selected fields" not in result.text
        duplicate = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={
                "run_id": str(run_id),
                "status": "pending",
                "selected_fields": "display_address",
                "csrftoken": token,
            },
            follow_redirects=False,
        )
        assert duplicate.status_code == 303
        repeated = await client.get(duplicate.headers["location"])
        assert "needs_review" in repeated.text


async def test_duplicate_generate_reuses_pending_review() -> None:
    """A second generate POST does not create another provider call."""
    summary = _summary()
    revision = _revision()
    provider = FakeChatCompletions(payload=_payload(revision.revision_id))
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=provider,
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        first = await _generate_review(client, location_id=summary.id, html=listing.text)
        second = await _generate_review(client, location_id=summary.id, html=listing.text)
        assert first.status_code == 303
        assert second.status_code == 303
        assert first.headers["location"] == second.headers["location"]
        assert len(provider.calls) == 1


async def test_provider_failure_and_collision_are_distinct() -> None:
    """Timeout and canonical collision surface as safe, distinct states."""
    summary = _summary()
    revision = _revision()
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(error=ProviderOutcome.TIMEOUT),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        failed = await _generate_review(client, location_id=summary.id, html=listing.text)
        page = await client.get(failed.headers["location"])
        assert "timed out" in page.text
        assert "Apply selected fields" not in page.text

    colliding = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
        apply_status=AiApplyStatus.COLLISION,
    )
    async with admin_client(
        places=places,
        review_store=colliding,
        provider=FakeChatCompletions(payload=_payload(revision.revision_id)),
        runtime=active_ai_runtime(),
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        review_page = await client.get(generated.headers["location"])
        token = _csrf_from_html(review_page.text)
        run_id = next(iter(colliding.runs))
        applied = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={
                "run_id": str(run_id),
                "selected_fields": "display_name",
                "csrftoken": token,
            },
            follow_redirects=False,
        )
        result = await client.get(applied.headers["location"])
        assert "collide with another place" in result.text


async def test_expired_review_cannot_apply() -> None:
    """An expired pending run is a distinct failure, not a silent write."""
    summary = _summary()
    revision = _revision()
    clock = FakeClock()
    review_store = FakePlaceAiReviewStore(
        snapshot=_snapshot_for(
            summary.id,
            name=summary.display_name,
            address=summary.display_address,
            district=summary.district or "Śródmieście",
        ),
        revisions=(revision,),
    )
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(
        places=places,
        review_store=review_store,
        provider=FakeChatCompletions(payload=_payload(revision.revision_id)),
        runtime=active_ai_runtime(),
        clock=clock,
    ) as (client, store):
        await _owner_session(client, store)
        listing = await client.get(_PLACES_PATH)
        generated = await _generate_review(client, location_id=summary.id, html=listing.text)
        review_page = await client.get(generated.headers["location"])
        token = _csrf_from_html(review_page.text)
        run_id = next(iter(review_store.runs))
        clock.advance(int(timedelta(hours=25).total_seconds()))
        applied = await client.post(
            f"{_PLACES_PATH}/ai-review/apply",
            data={
                "run_id": str(run_id),
                "selected_fields": "display_name",
                "csrftoken": token,
            },
            follow_redirects=False,
        )
        result = await client.get(applied.headers["location"])
        assert "expired or is no longer pending" in result.text
