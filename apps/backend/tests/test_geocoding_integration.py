"""Durable geocode cache, fencing, and selection integration tests."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text

from tests.test_geocode_address_accuracy import _feature, _mapped
from tests.test_geocoding import FakeTransport, _policy
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.catalog.application import SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.features.ingestion.application.geocoding import ClaimDisposition, ResolveGeocode
from wef_backend.features.ingestion.domain.address_evidence import AddressEvidence
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    NormalizedGeocodeQuery,
    normalize_geocode_query,
    review_geocode_result,
)
from wef_backend.features.ingestion.infrastructure.accept_pending_geocode_pins_adapter import (
    SQLAlchemyAcceptPendingGeocodePinsAdapter,
)
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    SQLAlchemyCompleteImportRepository,
)
from wef_backend.features.ingestion.infrastructure.geocode_store import (
    SQLAlchemyGeocodeStore,
    StaleGeocodeClaimError,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import (
    FixtureGeocoder,
    HostedGeocoder,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from wef_backend.features.catalog.application.seed_m1 import SeedLocation

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
NOW = datetime(2026, 8, 15, 6, 30, tzinfo=UTC)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))


async def _prepare() -> tuple[DatabaseResources, SeedLocation]:
    """Upgrade, clear prior fixture/cache state, and seed canonical locations."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    async with database.session_factory() as session:
        for statement in (
            "DELETE FROM location_geocode_selections",
            "UPDATE locations SET selected_geocode_result_id = NULL",
            "DELETE FROM geocode_miss_claims",
            "DELETE FROM geocode_results",
            "DELETE FROM offer_field_origins",
            "DELETE FROM offer_ai_field_events",
            "DELETE FROM offer_ai_enrichment_items",
            "DELETE FROM offer_ai_enrichment_batches",
            "DELETE FROM place_ai_review_runs",
            "DELETE FROM offer_sources",
            "DELETE FROM offers",
            "DELETE FROM locations",
        ):
            await session.execute(text(statement))
        await session.commit()
    locations, offers = m1_fixture()
    await SeedM1Catalog(SQLAlchemyCatalogSeedAdapter(database.session_factory), environment="test")(
        locations,
        offers,
    )
    return database, locations[0]


async def test_cross_process_claim_cache_and_selection_lineage() -> None:
    """Healthy racers get one owner and selection changes atomically with lineage."""
    database, location = await _prepare()
    store_one = SQLAlchemyGeocodeStore(database.session_factory)
    store_two = SQLAlchemyGeocodeStore(database.session_factory)
    query = normalize_geocode_query("ul. Marszałkowska 1")
    fixture_result = GeocodeResult(
        provider=GeocodeProvider.FIXTURE,
        provider_result_id="fixture-1",
        longitude=Decimal("21.0122"),
        latitude=Decimal("52.2297"),
        display_name="ul. Marszałkowska 1, Warszawa",
        precision=GeocodePrecision.BUILDING,
        confidence=Decimal("0.95"),
        within_scope=True,
        attribution_text="Synthetic no-network fixture",
        address=AddressEvidence(
            street="Marszałkowska",
            house_number="1",
            city="Warszawa",
            country_code="PL",
            result_type="building",
        ),
    )
    geocoder = FixtureGeocoder({query.normalized: fixture_result})
    resolution = await ResolveGeocode(store_one, geocoder, clock=lambda: NOW)(
        source_query=query.original,
        location_id=location.id,
    )
    assert not resolution.cache_hit
    replay = await ResolveGeocode(store_two, geocoder, clock=lambda: NOW)(
        source_query=query.original,
        location_id=location.id,
    )
    assert replay.cache_hit

    async with database.session_factory() as session:
        counts = (
            await session.execute(
                text(
                    "SELECT (SELECT count(*) FROM geocode_results), "
                    "(SELECT count(*) FROM location_geocode_selections)"
                ),
            )
        ).one()
        selected = (
            await session.execute(
                text(
                    "SELECT selected_geocode_result_id, ST_X(point), ST_Y(point), "
                    "review_status, precision, confidence, out_of_scope "
                    "FROM locations WHERE id = :id"
                ),
                {"id": location.id},
            )
        ).one()
        versions = (
            await session.execute(
                text(
                    "SELECT selection_version, from_state, to_state "
                    "FROM location_geocode_selections WHERE location_id = :id "
                    "ORDER BY selection_version"
                ),
                {"id": location.id},
            )
        ).all()
    assert tuple(counts) == (1, 2)
    assert selected.selected_geocode_result_id == resolution.cached.result_id
    assert (float(selected.st_x), float(selected.st_y)) == pytest.approx((21.0122, 52.2297))
    assert (selected.review_status, selected.precision, selected.out_of_scope) == (
        "accepted",
        "building",
        False,
    )
    assert [row.selection_version for row in versions] == [1, 2]
    assert versions[0].from_state == "accepted"
    assert versions[1].to_state == "accepted"
    await database.engine.dispose()


async def test_claim_lease_takeover_fences_stale_owner() -> None:
    """Only expired ownership is replaced and the older fence cannot complete."""
    database, _ = await _prepare()
    first = SQLAlchemyGeocodeStore(database.session_factory)
    second = SQLAlchemyGeocodeStore(database.session_factory)
    query = normalize_geocode_query("ul. Testowa 1")
    key = GeocodeCacheKey(GeocodeProvider.FIXTURE, query.normalized)
    claim_one = await first.claim_miss(
        key,
        owner_id="owner-one",
        now=NOW,
        lease_expires_at=NOW + timedelta(seconds=10),
    )
    waiting = await second.claim_miss(
        key,
        owner_id="owner-two",
        now=NOW + timedelta(seconds=5),
        lease_expires_at=NOW + timedelta(seconds=15),
    )
    takeover = await second.claim_miss(
        key,
        owner_id="owner-two",
        now=NOW + timedelta(seconds=11),
        lease_expires_at=NOW + timedelta(seconds=21),
    )
    assert claim_one.disposition is ClaimDisposition.OWNER
    assert waiting.disposition is ClaimDisposition.WAIT
    assert takeover.disposition is ClaimDisposition.OWNER
    assert takeover.fencing_token == claim_one.fencing_token + 1
    result = GeocodeResult(
        provider=GeocodeProvider.FIXTURE,
        provider_result_id=None,
        longitude=None,
        latitude=None,
        display_name=None,
        precision=GeocodePrecision.UNKNOWN,
        confidence=Decimal(0),
        within_scope=None,
        attribution_text="Synthetic no-network fixture",
        error_code=GeocodeErrorCode.NO_RESULT,
    )
    with pytest.raises(StaleGeocodeClaimError):
        await first.complete_miss(
            key,
            claim=claim_one,
            query=query,
            result=result,
            attempted_at=NOW,
            expires_at=NOW + timedelta(hours=24),
        )
    await second.complete_miss(
        key,
        claim=takeover,
        query=query,
        result=result,
        attempted_at=NOW,
        expires_at=NOW + timedelta(hours=24),
    )
    assert await first.get_cached(key) is not None
    reclaimed = await second.claim_miss(
        key,
        owner_id="owner-three",
        now=NOW + timedelta(seconds=12),
        lease_expires_at=NOW + timedelta(seconds=22),
    )
    assert reclaimed.disposition is ClaimDisposition.OWNER
    await database.engine.dispose()


async def test_abandoned_claim_can_be_reclaimed_before_original_expiry() -> None:
    """A controlled provider pause releases its miss without a lease delay."""
    database, _ = await _prepare()
    first = SQLAlchemyGeocodeStore(database.session_factory)
    second = SQLAlchemyGeocodeStore(database.session_factory)
    query = normalize_geocode_query("ul. Wstrzymana 1")
    key = GeocodeCacheKey(GeocodeProvider.FIXTURE, query.normalized)
    original = await first.claim_miss(
        key,
        owner_id="owner-one",
        now=NOW,
        lease_expires_at=NOW + timedelta(minutes=5),
    )
    await first.abandon_miss(key, claim=original, now=NOW + timedelta(seconds=1))
    reclaimed = await second.claim_miss(
        key,
        owner_id="owner-two",
        now=NOW + timedelta(seconds=1),
        lease_expires_at=NOW + timedelta(minutes=5),
    )
    assert reclaimed.disposition is ClaimDisposition.OWNER
    assert reclaimed.fencing_token == original.fencing_token + 1
    await database.engine.dispose()


@pytest.mark.parametrize(
    ("actor_type", "actor_id", "preserved"),
    [
        ("operator", "owner-id", True),
        ("operator", "unknown-legacy-actor", True),
        ("operator", "ad-034-accept-pending-pins", False),
        ("automatic_policy", None, False),
    ],
)
async def test_address_policy_preserves_owner_lineage_during_provider_io(
    actor_type: str,
    actor_id: str | None,
    *,
    preserved: bool,
) -> None:
    """The selection transaction rechecks current protection after network work."""
    database, location = await _prepare()
    transport = FakeTransport([{"features": [_feature("Grochowska", result_type="amenity")]}] * 2)
    hosted = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="fake")

    class EditingGeocoder:
        provider = GeocodeProvider.GEOAPIFY

        async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
            async with database.session_factory() as session:
                await session.execute(
                    text(
                        "INSERT INTO location_geocode_selections "
                        "(id, location_id, from_state, to_state, reason_code, actor_type, "
                        "actor_id, review_policy_version, selection_version, decided_at) "
                        "SELECT :id, :location, 'accepted', 'accepted', 'manual_accept', "
                        ":actor_type, :actor_id, 'warsaw-review-v1', 1, now() "
                        "WHERE NOT EXISTS (SELECT 1 FROM location_geocode_selections "
                        "WHERE location_id = :location)"
                    ),
                    {
                        "id": uuid4(),
                        "location": location.id,
                        "actor_type": actor_type,
                        "actor_id": actor_id,
                    },
                )
                await session.commit()
            return await hosted.geocode(query)

    resolution = await ResolveGeocode(
        SQLAlchemyGeocodeStore(database.session_factory), EditingGeocoder()
    )(
        source_query="ul. Jugosłowiańska",
        location_id=location.id,
    )
    assert not resolution.decision.select_result
    async with database.session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT review_status, point IS NOT NULL AS has_point "
                    "FROM locations WHERE id = :id"
                ),
                {"id": location.id},
            )
        ).one()
        selections = (
            await session.execute(
                text(
                    "SELECT actor_type, reason_code FROM location_geocode_selections "
                    "WHERE location_id = :id ORDER BY selection_version"
                ),
                {"id": location.id},
            )
        ).all()
    assert row.has_point is preserved
    assert len(selections) == (1 if preserved else 2)
    if not preserved:
        assert tuple(selections[-1]) == ("automatic_policy", "address_mismatch")
    await database.engine.dispose()


async def test_pending_pin_command_cannot_reaccept_coarse_or_legacy_evidence() -> None:
    """Both cached missing evidence and area centroids remain unpinned in PostGIS."""
    database, location = await _prepare()
    store = SQLAlchemyGeocodeStore(database.session_factory)
    query = normalize_geocode_query("ul. Jugosłowiańska")
    precise = await _mapped(_feature())
    for result in [
        replace(precise, address=None),
        replace(precise, precision=GeocodePrecision.DISTRICT),
    ]:
        # Different request versions preserve each independent historical fixture.
        key = GeocodeCacheKey(
            GeocodeProvider.GEOAPIFY,
            query.normalized,
            request_version=str(result.precision) + str(result.address is None),
        )
        claim = await store.claim_miss(
            key, owner_id="fixture", now=NOW, lease_expires_at=NOW + timedelta(seconds=30)
        )
        cached = await store.complete_miss(
            key, claim=claim, query=query, result=result, attempted_at=NOW, expires_at=None
        )

        decision = review_geocode_result(result, query=query)
        await store.select_for_location(
            location_id=location.id,
            cached=cached,
            decision=decision,
            actor_type="automatic_policy",
            actor_id=None,
        )
        adapter = SQLAlchemyAcceptPendingGeocodePinsAdapter(database.session_factory)
        assert await adapter.accept_in_scope_pending_pins() == 0
        async with database.session_factory() as session:
            assert await session.scalar(
                text("SELECT point IS NULL FROM locations WHERE id = :id"), {"id": location.id}
            )
    await database.engine.dispose()


async def test_two_form_exhaustion_is_durable_and_removed_from_pending_work() -> None:
    """Restarted resolvers use persisted evidence without spending or queue churn."""
    database, location = await _prepare()
    source = "Warszawa | ul. Ostrzycka"
    transport = FakeTransport([{"features": [_feature("Inna")]}, {"features": []}])
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="fixture")
    for _ in range(2):
        result = await ResolveGeocode(SQLAlchemyGeocodeStore(database.session_factory), geocoder)(
            source_query=source, location_id=location.id
        )
        assert not result.decision.select_result
    assert len(transport.calls) == 2
    pending = await SQLAlchemyCompleteImportRepository(database.session_factory).pending_locations()
    assert location.id not in {item.location_id for item in pending}
    async with database.session_factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM geocode_results")) == 2
    await database.engine.dispose()
