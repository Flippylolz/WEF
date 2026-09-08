"""Nearby source identity reaches the real public map through normal selection."""

import pytest
from sqlalchemy import select

from tests.test_current_offer_templates import HOUSE
from tests.test_geocoding import FakeTransport, _policy
from tests.test_listing_extraction import _message
from tests.test_nearby_localities import SOURCE, _locality_feature
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge, _settings
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import BoundingBox, MapFilters, QueryMapLocations
from wef_backend.features.catalog.infrastructure import SQLAlchemyMapQueryAdapter
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.catalog.infrastructure.promote_public_catalog_adapter import (
    SQLAlchemyPromotePublicCatalogAdapter,
)
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import HostedGeocoder
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]


async def test_nearby_house_replay_persists_city_and_publishes_coarse_map_point() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        raw = _message(HOUSE.replace("Miejscowość Testowa, гмина Testowa", SOURCE))
        persist = PersistHistoricalIngestion(
            SQLAlchemyIngestionPersistence(database.session_factory)
        )
        for _ in range(2):
            await persist(
                channel=raw.source,
                messages=[PersistableMessage(raw, extract_listing(raw))],
                metadata=RunMetadata(parser_version=PARSER_VERSION),
            )
        async with database.session_factory() as session:
            offer = (await session.scalars(select(OfferRow))).one()
            location = (await session.scalars(select(LocationRow))).one()
            assert offer.location_id == location.id
            assert location.city == "Miejscowość Testowa"
            assert location.display_name == "Miejscowość Testowa, gmina Przykładowa"
            assert location.point is None
            location_id = location.id
        resolver = ResolveGeocode(
            SQLAlchemyGeocodeStore(database.session_factory),
            HostedGeocoder(
                GeocodeProvider.GEOAPIFY,
                FakeTransport([{"features": [_locality_feature()]}]),
                _policy(),
                api_key="fixture",
            ),
        )
        resolution = await resolver(source_query=SOURCE, location_id=location_id)
        assert resolution.decision.select_result
        assert (
            await SQLAlchemyPromotePublicCatalogAdapter(
                database.session_factory
            ).promote_map_ready_offers()
            == 1
        )
        public_map = QueryMapLocations(SQLAlchemyMapQueryAdapter(database.session_factory))
        result = await public_map(MapFilters(bbox=BoundingBox.parse("20.7,52.0,21.4,52.6")))
        assert len(result.records) == 1
        assert result.records[0].id == location_id
        async with database.session_factory() as session:
            selected = await session.get(LocationRow, location_id)
            assert selected is not None
            assert selected.precision == "city"
            assert selected.review_status == "accepted"
    finally:
        await database.engine.dispose()
        await _purge()
