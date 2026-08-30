"""HTTP tests for the owner Locations console page and map picker."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from tests.fakes import FakeLocationAdminStore
from tests.test_admin_api import _csrf_from_html, _owner_session, admin_client
from wef_backend.features.admin.application.admin_ops import (
    GeocodeCandidateSummary,
    LocationAdminSummary,
    LocationEditDetail,
    OfferContextSummary,
)

_PLACES_PATH = "/admin/places"


def _summary(
    *,
    review_status: str = "needs_review",
    display_address: str = "ul. Marszałkowska 1, Warszawa",
    has_point: bool = False,
    has_candidate: bool = False,
    reason_code: str | None = "low_confidence",
) -> LocationAdminSummary:
    """Build one owner-facing summary with test defaults."""
    return LocationAdminSummary(
        id=uuid4(),
        display_name="Marszałkowska 1",
        display_address=display_address,
        district="Śródmieście",
        city="Warszawa",
        review_status=review_status,
        precision="unknown",
        confidence=Decimal("0.42"),
        has_point=has_point,
        out_of_scope=False,
        reason_code=reason_code,
        has_candidate=has_candidate,
        offer_count=1,
        updated_at=datetime(2026, 8, 30, tzinfo=UTC),
    )


def _detail(summary: LocationAdminSummary) -> LocationEditDetail:
    """Build the edit detail behind one summary, with one offer."""
    offer = OfferContextSummary(
        id=uuid4(),
        content_type="unit",
        market_type="secondary",
        visibility="visible",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
        currency="PLN",
        price_min_minor=85_000_00,
        price_max_minor=95_000_00,
        area_min_sqm=Decimal("42.00"),
        area_max_sqm=Decimal("48.00"),
        rooms_min=2,
        rooms_max=3,
        source_text_excerpt="Продам 2к 42м2 ул. Маршалковская 1",
    )
    return LocationEditDetail(
        summary=summary,
        normalized_address="ul. marszałkowska 1, warszawa, pl",
        longitude=None,
        latitude=None,
        candidate=GeocodeCandidateSummary(
            longitude=Decimal("21.0122"),
            latitude=Decimal("52.2297"),
            precision="building",
            confidence=Decimal("0.5500"),
            provider="geoapify",
            display_name="ul. Marszałkowska 1, Warszawa",
        ),
        offers=(offer,),
    )


async def test_owner_sees_pending_locations_and_filters() -> None:
    """The list defaults to the pending slice and honors the status filter."""
    pending = _summary()
    decided = _summary(
        review_status="accepted",
        display_address="ul. Rozpatrzona 8, Warszawa",
        has_point=True,
        has_candidate=False,
        reason_code="manual_accept",
    )
    places = FakeLocationAdminStore(summaries=[pending, decided])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        page = await client.get(_PLACES_PATH)
        body = page.text
        assert page.status_code == 200
        assert "ul. Marszałkowska 1" in body
        assert "ul. Rozpatrzona 8" not in body
        assert "Accept candidate" not in body

        filtered = await client.get(f"{_PLACES_PATH}?status=accepted")
        assert "ul. Rozpatrzona 8" in filtered.text
        assert "ul. Marszałkowska 1" not in filtered.text

        everything = await client.get(f"{_PLACES_PATH}?status=all")
        assert "ul. Marszałkowska 1" in everything.text
        assert "ul. Rozpatrzona 8" in everything.text


async def test_owner_searches_locations_by_address() -> None:
    """The search box narrows the listing case-insensitively."""
    first = _summary()
    second = _summary(display_address="ul. Puławska 12, Warszawa")
    places = FakeLocationAdminStore(summaries=[first, second])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        page = await client.get(f"{_PLACES_PATH}?search=pu%C5%82awska")
        assert "ul. Puławska 12" in page.text
        assert "ul. Marszałkowska 1" not in page.text


async def test_set_point_page_renders_offer_evidence_and_form() -> None:
    """The picker shows the offer evidence, candidate, map, and CSRF form."""
    summary = _summary(has_candidate=True)
    places = FakeLocationAdminStore(details={summary.id: _detail(summary)})
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        page = await client.get(f"{_PLACES_PATH}/set-point?location_id={summary.id}")
        body = page.text
        assert page.status_code == 200
        assert "ul. Marszałkowska 1, Warszawa" in body
        assert "Продам 2к 42м2 ул. Маршалковская 1" in body
        assert "85 000" in body
        assert "geoapify" in body
        assert "place_picker.js" in body
        assert 'name="csrftoken"' in body or "csrftoken" in body
        assert f'value="{summary.id}"' in body or f"value='{summary.id}'" in body


async def test_set_point_page_redirects_unknown_location() -> None:
    """Unknown location ids return to the list instead of failing."""
    places = FakeLocationAdminStore()
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        response = await client.get(
            f"{_PLACES_PATH}/set-point?location_id={uuid4()}",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith(_PLACES_PATH)


async def test_owner_saves_manual_point() -> None:
    """An in-scope manual point applies and returns to the list."""
    summary = _summary()
    places = FakeLocationAdminStore(details={summary.id: _detail(summary)})
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        picker = await client.get(f"{_PLACES_PATH}/set-point?location_id={summary.id}")
        response = await client.post(
            f"{_PLACES_PATH}/set-point",
            data={
                "location_id": str(summary.id),
                "latitude": "52.2297",
                "longitude": "21.0122",
                "csrftoken": _csrf_from_html(picker.text),
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"{_PLACES_PATH}?status=pending"
        assert places.applied == ["set_point"]


async def test_manual_point_out_of_scope_returns_with_error() -> None:
    """Out-of-scope coordinates bounce back to the picker with a banner."""
    summary = _summary()
    places = FakeLocationAdminStore(details={summary.id: _detail(summary)})
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        picker = await client.get(f"{_PLACES_PATH}/set-point?location_id={summary.id}")
        response = await client.post(
            f"{_PLACES_PATH}/set-point",
            data={
                "location_id": str(summary.id),
                "latitude": "60.0000",
                "longitude": "21.0122",
                "csrftoken": _csrf_from_html(picker.text),
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        assert places.applied == []
        follow_up = await client.get(response.headers["location"])
        assert "Warsaw scope" in follow_up.text


async def test_manual_point_rejects_non_numeric_coordinates() -> None:
    """Non-numeric coordinates bounce back without applying anything."""
    summary = _summary()
    places = FakeLocationAdminStore(details={summary.id: _detail(summary)})
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        picker = await client.get(f"{_PLACES_PATH}/set-point?location_id={summary.id}")
        response = await client.post(
            f"{_PLACES_PATH}/set-point",
            data={
                "location_id": str(summary.id),
                "latitude": "north",
                "longitude": "21.0122",
                "csrftoken": _csrf_from_html(picker.text),
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        assert places.applied == []


async def test_owner_runs_accept_and_reject_actions() -> None:
    """Row decisions post through, preserving the filter slice."""
    with_candidate = _summary(has_candidate=True)
    rejectable = _summary(display_address="ul. Odrzucona 3, Warszawa")
    places = FakeLocationAdminStore(summaries=[with_candidate, rejectable])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        list_page = await client.get(_PLACES_PATH)
        assert "Accept candidate" in list_page.text
        token = _csrf_from_html(list_page.text)
        accepted = await client.post(
            f"{_PLACES_PATH}/accept",
            data={
                "location_id": str(with_candidate.id),
                "status": "pending",
                "csrftoken": token,
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        assert accepted.headers["location"] == f"{_PLACES_PATH}?status=pending"

        rejected = await client.post(
            f"{_PLACES_PATH}/reject",
            data={
                "location_id": str(rejectable.id),
                "status": "pending",
                "csrftoken": token,
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert rejected.status_code == 303
        assert places.applied == ["accept", "reject"]


async def test_unresolve_action_targets_decided_locations() -> None:
    """Unresolve is offered for decided locations and posts through."""
    decided = _summary(
        review_status="accepted",
        has_point=True,
        has_candidate=False,
        reason_code="manual_accept",
    )
    places = FakeLocationAdminStore(summaries=[decided])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        list_page = await client.get(f"{_PLACES_PATH}?status=accepted")
        assert "Unresolve" in list_page.text
        response = await client.post(
            f"{_PLACES_PATH}/unresolve",
            data={
                "location_id": str(decided.id),
                "status": "accepted",
                "csrftoken": _csrf_from_html(list_page.text),
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert places.applied == ["unresolve"]


async def test_place_mutations_require_csrf_and_origin() -> None:
    """Missing CSRF token or cross-origin posts are refused by the guard."""
    summary = _summary()
    places = FakeLocationAdminStore(summaries=[summary])
    async with admin_client(places=places) as (client, store):
        await _owner_session(client, store)
        list_page = await client.get(_PLACES_PATH)
        token = _csrf_from_html(list_page.text)
        missing_csrf = await client.post(
            f"{_PLACES_PATH}/accept",
            data={"location_id": str(summary.id)},
            headers={"Origin": "http://testserver"},
        )
        assert missing_csrf.status_code in {400, 403}
        cross_origin = await client.post(
            f"{_PLACES_PATH}/accept",
            data={"location_id": str(summary.id), "csrftoken": token},
            headers={"Origin": "http://evil.example"},
        )
        assert cross_origin.status_code == 403
        assert places.applied == []


async def test_non_owner_cannot_open_locations_page() -> None:
    """Only owner sessions reach the console surface."""
    places = FakeLocationAdminStore(summaries=[_summary()])
    async with admin_client(places=places) as (client, _store):
        response = await client.get(_PLACES_PATH, follow_redirects=False)
        assert response.status_code in {302, 303, 401, 403}
