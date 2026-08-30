"""Owner location administration interactor tests."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAdminAuditStore,
    FakeClock,
    FakeLocationAdminStore,
)
from wef_backend.features.admin.application.admin_ops import (
    AcceptPlaceCandidate,
    AdminDeniedError,
    AdminOutcome,
    GetLocationForEdit,
    ListLocations,
    LocationAdminSummary,
    LocationStatusFilter,
    RejectPlace,
    SetPlacePoint,
    UnresolvePlace,
)


def _summary(
    *,
    review_status: str,
    display_address: str = "ul. Marszałkowska 1, Warszawa",
) -> LocationAdminSummary:
    """Build one owner-facing location summary."""
    return LocationAdminSummary(
        id=uuid4(),
        display_name="Marszałkowska 1",
        display_address=display_address,
        district="Śródmieście",
        city="Warszawa",
        review_status=review_status,
        precision="building",
        confidence=Decimal("0.42"),
        has_point=False,
        out_of_scope=False,
        reason_code="low_confidence",
        offer_count=2,
        updated_at=FakeClock().now(),
    )


async def test_list_locations_defaults_to_pending_slice_and_cleans_search() -> None:
    """The default slice hides decided locations and search terms are trimmed."""
    store = FakeLocationAdminStore(
        summaries=[
            _summary(review_status="needs_review"),
            _summary(
                review_status="accepted",
                display_address="ul. Puławska 10, Warszawa",
            ),
            _summary(
                review_status="ungeocoded",
                display_address="ul. Puławska 12, Warszawa",
            ),
        ],
    )
    listing = ListLocations(store)

    pending = await listing()
    assert [summary.review_status for summary in pending] == [
        "needs_review",
        "ungeocoded",
    ]

    searched = await listing(search="  puławska 12  ")
    assert [summary.display_address for summary in searched] == [
        "ul. Puławska 12, Warszawa",
    ]

    everything = await listing(status=LocationStatusFilter.ALL)
    assert len(everything) == 3


async def test_get_location_for_edit_denies_unknown_location() -> None:
    """Unknown location ids are refused."""
    store = FakeLocationAdminStore()
    with pytest.raises(AdminDeniedError, match="location not found"):
        await GetLocationForEdit(store)(location_id=uuid4())


async def test_accept_place_candidate_records_allowed_audit() -> None:
    """A successful candidate promotion records an allowed audit event."""
    store = FakeLocationAdminStore()
    audits = FakeAdminAuditStore()
    owner_id = uuid4()
    request_id = uuid4()

    await AcceptPlaceCandidate(store, audits, FakeClock())(
        owner_id=owner_id,
        location_id=uuid4(),
        request_id=request_id,
    )

    assert store.applied == ["accept"]
    assert [event.outcome for event in audits.events] == [AdminOutcome.ALLOWED]
    event = audits.events[0]
    assert event.action == "accept_place"
    assert event.target_type == "location"
    assert event.owner_user_id == owner_id
    assert event.request_id == request_id


async def test_accept_place_candidate_denies_without_candidate() -> None:
    """A refused promotion records a denied audit event and raises."""
    store = FakeLocationAdminStore(denied_actions={"accept"})
    audits = FakeAdminAuditStore()
    location_id = uuid4()

    with pytest.raises(AdminDeniedError, match="no in-scope candidate"):
        await AcceptPlaceCandidate(store, audits, FakeClock())(
            owner_id=uuid4(),
            location_id=location_id,
            request_id=uuid4(),
        )

    assert audits.events[-1].outcome is AdminOutcome.DENIED
    assert audits.events[-1].target_id == str(location_id)


async def test_reject_place_allowed_and_denied_paths() -> None:
    """Reject records allowed or denied audits mirroring the store outcome."""
    location_id = uuid4()
    allowed_store = FakeLocationAdminStore()
    allowed_audits = FakeAdminAuditStore()
    await RejectPlace(allowed_store, allowed_audits, FakeClock())(
        owner_id=uuid4(),
        location_id=location_id,
        request_id=uuid4(),
    )
    assert allowed_store.applied == ["reject"]
    assert allowed_audits.events[-1].outcome is AdminOutcome.ALLOWED

    denied_store = FakeLocationAdminStore(denied_actions={"reject"})
    denied_audits = FakeAdminAuditStore()
    with pytest.raises(AdminDeniedError, match="already rejected"):
        await RejectPlace(denied_store, denied_audits, FakeClock())(
            owner_id=uuid4(),
            location_id=location_id,
            request_id=uuid4(),
        )
    assert denied_audits.events[-1].outcome is AdminOutcome.DENIED


async def test_unresolve_place_allowed_and_denied_paths() -> None:
    """Unresolve records allowed or denied audits mirroring the store outcome."""
    allowed_store = FakeLocationAdminStore()
    allowed_audits = FakeAdminAuditStore()
    await UnresolvePlace(allowed_store, allowed_audits, FakeClock())(
        owner_id=uuid4(),
        location_id=uuid4(),
        request_id=uuid4(),
    )
    assert allowed_audits.events[-1].action == "unresolve_place"
    assert allowed_audits.events[-1].outcome is AdminOutcome.ALLOWED

    denied_store = FakeLocationAdminStore(denied_actions={"unresolve"})
    denied_audits = FakeAdminAuditStore()
    with pytest.raises(AdminDeniedError, match="unresolved"):
        await UnresolvePlace(denied_store, denied_audits, FakeClock())(
            owner_id=uuid4(),
            location_id=uuid4(),
            request_id=uuid4(),
        )
    assert denied_audits.events[-1].outcome is AdminOutcome.DENIED


async def test_set_place_point_places_in_scope_point() -> None:
    """An in-scope manual point is applied and audited as allowed."""
    store = FakeLocationAdminStore()
    audits = FakeAdminAuditStore()
    location_id = uuid4()

    await SetPlacePoint(store, audits, FakeClock())(
        owner_id=uuid4(),
        location_id=location_id,
        longitude=Decimal("21.0122"),
        latitude=Decimal("52.2297"),
        request_id=uuid4(),
    )

    assert store.applied == ["set_point"]
    assert audits.events[-1].action == "set_place_point"
    assert audits.events[-1].outcome is AdminOutcome.ALLOWED


async def test_set_place_point_refuses_out_of_scope_coordinates() -> None:
    """Out-of-scope manual points never reach the store and are audited."""
    store = FakeLocationAdminStore()
    audits = FakeAdminAuditStore()

    with pytest.raises(AdminDeniedError, match="Warsaw scope"):
        await SetPlacePoint(store, audits, FakeClock())(
            owner_id=uuid4(),
            location_id=uuid4(),
            longitude=Decimal("30.0000"),
            latitude=Decimal("52.2297"),
            request_id=uuid4(),
        )

    assert store.applied == []
    assert [event.outcome for event in audits.events] == [AdminOutcome.DENIED]
