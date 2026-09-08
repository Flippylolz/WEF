"""Reported extraction gaps preserve source units through public projections."""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from tests.parser_benchmark import FIXTURE
from tests.test_current_offer_templates import APARTMENT
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
    RunMode,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]


@pytest.mark.asyncio
async def test_current_template_replay_creates_one_offer_without_rewriting_source() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        raw = _message(APARTMENT)
        extraction = extract_listing(raw)
        old_miss = replace(
            extraction,
            listing=None,
            decision=replace(
                extraction.decision,
                parser_version="e2-v15",
                is_candidate=False,
                score=0,
                signals=(),
                content_type=None,
            ),
        )
        service = PersistHistoricalIngestion(
            store=SQLAlchemyIngestionPersistence(database.session_factory)
        )
        await service(
            channel=raw.source,
            messages=[PersistableMessage(raw, old_miss)],
            metadata=RunMetadata(parser_version="e2-v15"),
        )
        async with database.session_factory() as session:
            assert await session.scalar(text("SELECT count(*) FROM offers")) == 0
        for _ in range(2):
            await service(
                channel=raw.source,
                messages=[PersistableMessage(raw, extraction)],
                metadata=RunMetadata(parser_version=PARSER_VERSION, mode=RunMode.REPROCESS),
            )
        async with database.session_factory() as session:
            offers = (await session.scalars(select(OfferRow))).all()
            assert len(offers) == 1
            offer = offers[0]
            assert offer.price_min_minor == offer.price_max_minor == 81200000
            assert offer.parking_price_min_minor == offer.parking_price_max_minor == 4200000
            assert offer.storage_price_min_minor == offer.storage_price_max_minor == 2300000
            assert offer.area_min_sqm == Decimal("38.60")
            assert offer.rooms_min == offer.rooms_max == 2
            assert offer.currency == "PLN"
            assert offer.parser_version == PARSER_VERSION
            assert offer.visibility == "needs_review"
            assert await session.scalar(text("SELECT count(*) FROM offer_sources")) == 1
            assert await session.scalar(text("SELECT count(*) FROM source_message_revisions")) == 1
            assert await session.scalar(text("SELECT raw_checksum FROM source_messages")) == (
                raw.checksum
            )
    finally:
        await database.engine.dispose()
        await _purge()


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
