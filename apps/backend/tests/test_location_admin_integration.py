"""Owner location administration store integration tests."""

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text

from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.admin_ops import LocationStatusFilter
from wef_backend.features.admin.infrastructure.place_store import (
    SQLAlchemyLocationAdminStore,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

_DECIDED_AT = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))


async def _prepare() -> DatabaseResources:
    """Upgrade to head and clear all location/geocode state."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    async with database.session_factory() as session:
        for statement in (
            "DELETE FROM location_geocode_selections",
            "UPDATE locations SET selected_geocode_result_id = NULL",
            "DELETE FROM geocode_miss_claims",
            "DELETE FROM geocode_results",
            "DELETE FROM offer_sources",
            "DELETE FROM offers",
            "DELETE FROM locations",
        ):
            await session.execute(text(statement))
        await session.commit()
    return database


def _location_row(
    *,
    review_status: str,
    display_address: str,
    point: str | None = None,
) -> LocationRow:
    """Build one canonical location row; accepted rows must carry a point."""
    return LocationRow(
        id=uuid4(),
        display_name=display_address.split(",", maxsplit=1)[0].strip(),
        display_address=display_address,
        normalized_address=display_address.casefold(),
        normalized_address_hash=(uuid4().hex + uuid4().hex)[:64],
        selected_geocode_result_id=None,
        district="Śródmieście",
        city="Warszawa",
        country_code="PL",
        point=None if point is None else WKTElement(f"POINT({point})", srid=4326),
        precision="unknown" if point is None else "building",
        confidence=Decimal("0.30") if point is None else Decimal("0.90"),
        review_status=review_status,
        out_of_scope=False,
    )


def _geocode_result_row(
    *,
    longitude: str,
    latitude: str,
    confidence: str = "0.55",
    within_scope: bool = True,
    error_code: str | None = None,
    with_point: bool = True,
) -> GeocodeResultRow:
    """Build one provider-neutral geocode cache row."""
    return GeocodeResultRow(
        id=uuid4(),
        query_hash=(uuid4().hex + uuid4().hex)[:64],
        query_original="ul. Testowa 1",
        query_normalized="ul. testowa 1, warszawa, pl",
        normalizer_version="warsaw-address-v1",
        scope_version="warsaw-scope-v1",
        request_version="forward-geocode-v1",
        provider="fixture",
        provider_result_id="fixture-1",
        point=(None if not with_point else WKTElement(f"POINT({longitude} {latitude})", srid=4326)),
        display_name="ul. Testowa 1, Warszawa",
        precision="building",
        confidence=Decimal(confidence),
        within_scope=within_scope,
        response_json={},
        attribution_text="Synthetic no-network fixture",
        attempted_at=_DECIDED_AT,
        expires_at=None,
        error_code=error_code,
    )


def _selection_row(
    *,
    location_id: UUID,
    geocode_result_id: UUID | None,
    selection_version: int,
    reason_code: str,
) -> LocationGeocodeSelectionRow:
    """Build one pipeline-authored lineage row."""
    return LocationGeocodeSelectionRow(
        id=uuid4(),
        location_id=location_id,
        geocode_result_id=geocode_result_id,
        from_state="needs_review",
        to_state="needs_review",
        reason_code=reason_code,
        actor_type="system",
        actor_id=None,
        review_policy_version="warsaw-review-v1",
        selection_version=selection_version,
        decided_at=_DECIDED_AT,
    )


async def test_list_locations_filters_searches_and_orders() -> None:
    """The pending slice, explicit slices, search, and ordering all behave."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    accepted = _location_row(
        review_status="accepted",
        display_address="ul. Akceptowana 1",
        point="21.0000 52.2300",
    )
    pending = _location_row(review_status="needs_review", display_address="ul. Niepewna 2")
    ungeocoded = _location_row(review_status="ungeocoded", display_address="ul. Niepewna 10")
    candidate_result = _geocode_result_row(longitude="21.0122", latitude="52.2297")
    async with database.session_factory.begin() as session:
        session.add_all(
            [
                accepted,
                pending,
                ungeocoded,
                candidate_result,
                _selection_row(
                    location_id=pending.id,
                    geocode_result_id=candidate_result.id,
                    selection_version=1,
                    reason_code="low_confidence",
                ),
            ],
        )

    pending_rows = await store.list_locations(
        status=LocationStatusFilter.PENDING,
        search=None,
    )
    assert {row.id for row in pending_rows} == {pending.id, ungeocoded.id}
    assert {row.id for row in pending_rows if row.has_candidate} == {pending.id}
    assert {row.id for row in pending_rows if row.reason_code == "low_confidence"} == {
        pending.id,
    }

    searched = await store.list_locations(
        status=LocationStatusFilter.ALL,
        search="niepewna 10",
    )
    assert [row.id for row in searched] == [ungeocoded.id]

    escaped = await store.list_locations(
        status=LocationStatusFilter.ALL,
        search="%_",
    )
    assert escaped == ()

    await database.engine.dispose()


async def test_get_edit_detail_returns_candidate_and_offers() -> None:
    """The detail view exposes the latest in-scope candidate point."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    location = _location_row(review_status="needs_review", display_address="ul. Testowa 1")
    result = _geocode_result_row(longitude="21.0122", latitude="52.2297")
    async with database.session_factory.begin() as session:
        session.add_all(
            [
                location,
                result,
                _selection_row(
                    location_id=location.id,
                    geocode_result_id=result.id,
                    selection_version=1,
                    reason_code="low_confidence",
                ),
            ],
        )

    detail = await store.get_edit_detail(location.id)
    assert detail is not None
    assert detail.summary.review_status == "needs_review"
    assert detail.summary.reason_code == "low_confidence"
    assert detail.summary.offer_count == 0
    assert detail.longitude is None
    assert detail.latitude is None
    assert detail.candidate is not None
    assert detail.candidate.longitude == Decimal("21.0122")
    assert detail.candidate.latitude == Decimal("52.2297")
    assert detail.candidate.provider == "fixture"
    assert detail.offers == ()

    missing = await store.get_edit_detail(uuid4())
    assert missing is None
    await database.engine.dispose()


async def test_accept_candidate_promotes_point_and_lineage() -> None:
    """Accepting copies the candidate onto the location with operator lineage."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    location = _location_row(review_status="needs_review", display_address="ul. Testowa 1")
    result = _geocode_result_row(longitude="21.0122", latitude="52.2297", confidence="0.55")
    async with database.session_factory.begin() as session:
        session.add_all(
            [
                location,
                result,
                _selection_row(
                    location_id=location.id,
                    geocode_result_id=result.id,
                    selection_version=1,
                    reason_code="low_confidence",
                ),
            ],
        )

    applied = await store.apply_accept_candidate(
        location_id=location.id,
        actor_id=str(uuid4()),
        decided_at=_DECIDED_AT,
    )
    assert applied is True

    async with database.session_factory() as session:
        row = await session.get(LocationRow, location.id)
        selections = (
            await session.scalars(
                select(LocationGeocodeSelectionRow).order_by(
                    LocationGeocodeSelectionRow.selection_version,
                ),
            )
        ).all()
        longitude, latitude = (
            await session.execute(
                select(func.ST_X(LocationRow.point), func.ST_Y(LocationRow.point)).where(
                    LocationRow.id == location.id,
                ),
            )
        ).one()
    assert row is not None
    assert row.review_status == "accepted"
    assert row.selected_geocode_result_id == result.id
    assert row.out_of_scope is False
    assert row.precision == "building"
    assert longitude == pytest.approx(21.0122)
    assert latitude == pytest.approx(52.2297)
    assert [item.selection_version for item in selections] == [1, 2]
    assert selections[-1].to_state == "accepted"
    assert selections[-1].reason_code == "manual_accept"
    assert selections[-1].actor_type == "operator"
    assert selections[-1].geocode_result_id == result.id
    await database.engine.dispose()


async def test_accept_candidate_refuses_result_without_usable_point() -> None:
    """Provider errors and out-of-scope results are never promotable."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    errored_location = _location_row(review_status="ungeocoded", display_address="ul. Błąd 1")
    errored_result = _geocode_result_row(
        longitude="0",
        latitude="0",
        error_code="timeout",
        with_point=False,
    )
    out_of_scope_location = _location_row(
        review_status="needs_review",
        display_address="ul. Poza 1",
    )
    out_of_scope_result = _geocode_result_row(
        longitude="30.0000",
        latitude="52.2297",
        within_scope=False,
    )
    async with database.session_factory.begin() as session:
        session.add_all(
            [
                errored_location,
                errored_result,
                _selection_row(
                    location_id=errored_location.id,
                    geocode_result_id=errored_result.id,
                    selection_version=1,
                    reason_code="provider_error",
                ),
                out_of_scope_location,
                out_of_scope_result,
                _selection_row(
                    location_id=out_of_scope_location.id,
                    geocode_result_id=out_of_scope_result.id,
                    selection_version=1,
                    reason_code="out_of_scope",
                ),
            ],
        )

    assert (
        await store.apply_accept_candidate(
            location_id=errored_location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )
    assert (
        await store.apply_accept_candidate(
            location_id=out_of_scope_location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )
    assert (
        await store.apply_accept_candidate(
            location_id=uuid4(),
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )
    await database.engine.dispose()


async def test_out_of_bbox_candidate_is_never_surfaced() -> None:
    """A provider 'in-scope' flag cannot smuggle coordinates outside Warsaw."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    location = _location_row(review_status="needs_review", display_address="ul. Dziwna 1")
    junk_result = _geocode_result_row(
        longitude="46.545114",
        latitude="13.198879",
        within_scope=True,
    )
    async with database.session_factory.begin() as session:
        session.add_all(
            [
                location,
                junk_result,
                _selection_row(
                    location_id=location.id,
                    geocode_result_id=junk_result.id,
                    selection_version=1,
                    reason_code="low_confidence",
                ),
            ],
        )

    rows = await store.list_locations(status=LocationStatusFilter.ALL, search=None)
    assert [row.has_candidate for row in rows] == [False]

    detail = await store.get_edit_detail(location.id)
    assert detail is not None
    assert detail.candidate is None

    assert (
        await store.apply_accept_candidate(
            location_id=location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )

    async with database.session_factory() as session:
        row = await session.get(LocationRow, location.id)
        assert row is not None
        assert row.review_status == "needs_review"
    await database.engine.dispose()


async def test_set_point_reject_and_unresolve_transitions() -> None:
    """Manual points, rejection, and re-opening interleave on one lineage."""
    database = await _prepare()
    store = SQLAlchemyLocationAdminStore(database.session_factory)
    location = _location_row(review_status="needs_review", display_address="ul. Ręczna 1")
    decided = _location_row(
        review_status="accepted",
        display_address="ul. Rozpatrzona 1",
        point="21.0200 52.2400",
    )
    async with database.session_factory.begin() as session:
        session.add_all([location, decided])

    assert (
        await store.apply_set_point(
            location_id=location.id,
            longitude=Decimal("21.0100"),
            latitude=Decimal("52.2300"),
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is True
    )
    assert (
        await store.apply_reject(
            location_id=location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is True
    )
    assert (
        await store.apply_unresolve(
            location_id=location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is True
    )
    assert (
        await store.apply_unresolve(
            location_id=location.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )
    assert (
        await store.apply_reject(
            location_id=uuid4(),
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is False
    )

    async with database.session_factory() as session:
        row = await session.get(LocationRow, location.id)
        selections = (
            await session.scalars(
                select(LocationGeocodeSelectionRow)
                .where(LocationGeocodeSelectionRow.location_id == location.id)
                .order_by(LocationGeocodeSelectionRow.selection_version),
            )
        ).all()
        longitude, latitude = (
            await session.execute(
                select(func.ST_X(LocationRow.point), func.ST_Y(LocationRow.point)).where(
                    LocationRow.id == location.id,
                ),
            )
        ).one()
    assert row is not None
    assert row.review_status == "needs_review"
    assert row.precision == "building"
    assert row.confidence == Decimal("1.00")
    assert row.selected_geocode_result_id is None
    assert longitude == pytest.approx(21.0100)
    assert latitude == pytest.approx(52.2300)
    assert [item.selection_version for item in selections] == [1, 2, 3]
    assert [item.to_state for item in selections] == [
        "accepted",
        "rejected",
        "needs_review",
    ]
    assert [item.reason_code for item in selections] == [
        "manual_accept",
        "manual_reject",
        "manual_unresolve",
    ]
    assert all(item.geocode_result_id is None for item in selections)

    assert (
        await store.apply_unresolve(
            location_id=decided.id,
            actor_id="owner",
            decided_at=_DECIDED_AT,
        )
        is True
    )
    async with database.session_factory() as session:
        decided_row = await session.get(LocationRow, decided.id)
        assert decided_row is not None
        assert decided_row.review_status == "needs_review"
    await database.engine.dispose()
