"""Reported extraction gaps preserve source units through public projections."""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from tests.parser_benchmark import FIXTURE
from tests.test_listing_extraction import _message
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge, _settings
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import BoundingBox, MapFilters
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogBrowseAdapter
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]


@pytest.mark.asyncio
async def test_reported_prices_persist_in_minor_units_and_filter_correctly() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        cases = [
            case
            for case in json.loads(FIXTURE.read_text())["cases"]
            if case["stratum"] == "audit-regression"
        ]
        service = PersistHistoricalIngestion(
            store=SQLAlchemyIngestionPersistence(database.session_factory)
        )
        for index, case in enumerate(cases):
            raw = replace(_message(case["text"]), external_message_id=600 + index)
            await service(
                channel=raw.source,
                messages=[PersistableMessage(raw, extract_listing(raw))],
                metadata=RunMetadata(parser_version=PARSER_VERSION),
            )
        async with database.session_factory() as session, session.begin():
            offers = (
                await session.scalars(select(OfferRow).order_by(OfferRow.price_min_minor))
            ).all()
            assert len(offers) == 2
            first, second = offers
            assert first.price_min_minor == first.price_max_minor == 78000000
            assert first.area_min_sqm == Decimal("37.50")
            assert first.storage_included_in_price is True
            assert second.price_min_minor == second.price_max_minor == 139900000
            assert second.parking_price_min_minor == second.parking_price_max_minor == 3900000
            assert all(offer.currency == "PLN" for offer in offers)
            location_id = first.location_id
            await session.execute(text("UPDATE offers SET visibility='visible'"))
            await session.execute(
                text(
                    "UPDATE locations SET review_status='accepted', out_of_scope=false, "
                    "point=ST_SetSRID(ST_MakePoint(21.01,52.23),4326)"
                )
            )
        adapter = SQLAlchemyCatalogBrowseAdapter(database.session_factory)
        page = await adapter.query_location_offers(
            location_id=location_id,
            filters=MapFilters(
                bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"),
                price_min=78000000,
                price_max=78000000,
            ),
            include_non_matching=False,
            cursor=None,
            limit=10,
        )
        assert page.matching_count == 1
        assert page.records[0].price_min_minor == 78000000
        assert page.records[0].storage_included_in_price is True
        assert page.records[0].area_min_sqm == Decimal("37.50")
    finally:
        await database.engine.dispose()
        await _purge()
