"""PostGIS integration proof for grouped map filter semantics."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy import text, update

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import (
    BoundingBox,
    BrowseLocationOffers,
    GetOfferDetail,
    MapFilters,
    QueryFacets,
    QueryMapLocations,
    SeedM1Catalog,
)
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.domain import LocationReviewStatus, MarketType
from wef_backend.features.catalog.infrastructure import (
    LocationRow,
    OfferRow,
    SQLAlchemyCatalogBrowseAdapter,
    SQLAlchemyCatalogSeedAdapter,
    SQLAlchemyMapQueryAdapter,
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.migration import alembic_command, alembic_config
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL is required for PostGIS integration",
)

WARSAW = BoundingBox.parse("20.7,52.0,21.4,52.4")


async def test_grouped_map_query_semantics_and_performance() -> None:
    """Prove inclusive filters, grouping gates, coordinates, and local budget."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    await asyncio.to_thread(alembic_command.upgrade, alembic_config(settings), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    adapter = SQLAlchemyMapQueryAdapter(database.session_factory)
    service = QueryMapLocations(adapter)
    seed = SeedM1Catalog(
        SQLAlchemyCatalogSeedAdapter(database.session_factory),
        environment="test",
    )
    await seed(*m1_fixture())

    try:
        all_results = await service(MapFilters(bbox=WARSAW))
        primary = await service(
            MapFilters(bbox=WARSAW, market_types=(MarketType.PRIMARY,)),
        )
        bounded_price = await service(
            MapFilters(bbox=WARSAW, price_max=90_000_000),
        )
        null_excluding_price = await service(MapFilters(bbox=WARSAW, price_min=1))
        repeated_rooms = await service(MapFilters(bbox=WARSAW, rooms=(2, 4)))
        combined_groups = await service(
            MapFilters(
                bbox=WARSAW,
                price_min=100_000_000,
                rooms=(2, 4),
                districts=("srodmiescie", "wola"),
                market_types=(MarketType.PRIMARY,),
            ),
        )
        dated = await service(
            MapFilters(
                bbox=WARSAW,
                published_from=datetime(2026, 8, 2, tzinfo=UTC),
            ),
        )

        assert len(all_results.records) == 4
        center = next(
            item
            for item in all_results.records
            if item.id == UUID("10000000-0000-4000-8000-000000000001")
        )
        assert (center.longitude, center.latitude) == (21.0122, 52.2297)
        assert center.matching_offer_count == 2
        assert center.total_offer_count == 2
        primary_center = next(
            item
            for item in primary.records
            if item.id == UUID("10000000-0000-4000-8000-000000000001")
        )
        assert primary_center.matching_offer_count == 1
        assert primary_center.total_offer_count == 2
        assert {item.district for item in bounded_price.records} == {
            "srodmiescie",
            "wola",
        }
        assert "praga-polnoc" not in {item.district for item in null_excluding_price.records}
        assert {item.district for item in repeated_rooms.records} == {
            "srodmiescie",
            "wola",
        }
        assert [item.district for item in combined_groups.records] == ["srodmiescie"]
        assert {item.district for item in dated.records} == {"praga-polnoc"}

        await _hide_out_of_scope_and_unreviewed_rows(database.session_factory)
        gated = await service(MapFilters(bbox=WARSAW))
        assert [item.district for item in gated.records] == ["srodmiescie"]

        await seed(*m1_fixture())
        await service(MapFilters(bbox=WARSAW))
        timings: list[float] = []
        for _ in range(20):
            started_at = perf_counter()
            await service(MapFilters(bbox=WARSAW, rooms=(2,), price_max=120_000_000))
            timings.append(perf_counter() - started_at)
        timings.sort()
        p95_index = max(0, int(len(timings) * 0.95) - 1)
        assert timings[p95_index] < 0.5

        async with database.session_factory() as session:
            plan = (
                await session.execute(
                    text(
                        "EXPLAIN SELECT id FROM locations "
                        "WHERE ST_Intersects(point, "
                        "ST_MakeEnvelope(20.7, 52.0, 21.4, 52.4, 4326))",
                    ),
                )
            ).scalars()
        assert any("Scan" in line for line in plan)
    finally:
        await seed(*m1_fixture())
        await database.engine.dispose()


async def test_facets_offer_context_and_cursor_ties() -> None:
    """Prove canonical facets, match/history context, and stable pagination."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    await asyncio.to_thread(alembic_command.upgrade, alembic_config(settings), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    adapter = SQLAlchemyCatalogBrowseAdapter(database.session_factory)
    facets_service = QueryFacets(adapter)
    browse_service = BrowseLocationOffers(adapter)
    seed = SeedM1Catalog(
        SQLAlchemyCatalogSeedAdapter(database.session_factory),
        environment="test",
    )
    await seed(*m1_fixture())
    center_id = UUID("10000000-0000-4000-8000-000000000001")

    try:
        facets = await facets_service()
        primary_page = await browse_service(
            location_id=center_id,
            filters=MapFilters(
                bbox=WARSAW,
                market_types=(MarketType.PRIMARY,),
            ),
            include_non_matching=True,
            cursor=None,
            limit=1,
        )
        history_page = await browse_service(
            location_id=center_id,
            filters=MapFilters(
                bbox=WARSAW,
                market_types=(MarketType.PRIMARY,),
            ),
            include_non_matching=True,
            cursor=primary_page.next_cursor,
            limit=1,
        )

        assert facets.districts == (
            "mokotow",
            "praga-polnoc",
            "srodmiescie",
            "wola",
        )
        assert facets.rooms == (1, 2, 3)
        assert facets.price_min_minor == 69_000_000
        assert primary_page.matching_count == 1
        assert primary_page.total_count == 2
        assert primary_page.items[0].matches_filters is True
        assert history_page.items[0].matches_filters is False
        assert {primary_page.items[0].id, history_page.items[0].id} == {
            UUID("20000000-0000-4000-8000-000000000001"),
            UUID("20000000-0000-4000-8000-000000000002"),
        }

        async with database.session_factory() as session, session.begin():
            await session.execute(
                update(OfferRow)
                .where(
                    OfferRow.id == UUID("20000000-0000-4000-8000-000000000002"),
                )
                .values(published_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC)),
            )
        tie_first = await browse_service(
            location_id=center_id,
            filters=MapFilters(bbox=WARSAW),
            include_non_matching=False,
            cursor=None,
            limit=1,
        )
        tie_second = await browse_service(
            location_id=center_id,
            filters=MapFilters(bbox=WARSAW),
            include_non_matching=False,
            cursor=tie_first.next_cursor,
            limit=1,
        )
        assert tie_first.items[0].id != tie_second.items[0].id
        assert tie_second.next_cursor is None
    finally:
        await seed(*m1_fixture())
        await database.engine.dispose()


async def test_offer_detail_returns_m1_fixture_without_sensitive_fields() -> None:
    """Prove visible seeded offers load masked text and omit source lineage when absent."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    await asyncio.to_thread(alembic_command.upgrade, alembic_config(settings), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    seed = SeedM1Catalog(
        SQLAlchemyCatalogSeedAdapter(database.session_factory),
        environment="test",
    )
    await seed(*m1_fixture())
    service = GetOfferDetail(SQLAlchemyOfferDetailAdapter(database.session_factory))

    try:
        async with database.session_factory() as session, session.begin():
            await session.execute(
                update(OfferRow)
                .where(OfferRow.id == UUID("20000000-0000-4000-8000-000000000003"))
                .values(visibility="hidden"),
            )
        detail = await service(UUID("20000000-0000-4000-8000-000000000002"))
        missing = await service(UUID("20000000-0000-4000-8000-000000000099"))
        hidden = await service(UUID("20000000-0000-4000-8000-000000000003"))
    finally:
        await seed(*m1_fixture())
        await database.engine.dispose()

    assert missing is None
    assert hidden is None
    assert detail is not None
    assert detail.public_source_text == "Synthetic two-room unit fixture."
    assert detail.verified_source_url is None
    assert detail.source_history == ()
    assert detail.media == ()
    assert detail.location.display_name == "Synthetic Central Residence"


async def _hide_out_of_scope_and_unreviewed_rows(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Persist gate variants read by a separate adapter session."""
    async with session_factory() as session, session.begin():
        await session.execute(
            update(OfferRow)
            .where(
                OfferRow.id == UUID("20000000-0000-4000-8000-000000000003"),
            )
            .values(visibility="hidden"),
        )
        await session.execute(
            update(LocationRow)
            .where(
                LocationRow.id == UUID("10000000-0000-4000-8000-000000000003"),
            )
            .values(
                out_of_scope=True,
                review_status=LocationReviewStatus.NEEDS_REVIEW.value,
            ),
        )
        await session.execute(
            update(LocationRow)
            .where(
                LocationRow.id == UUID("10000000-0000-4000-8000-000000000004"),
            )
            .values(review_status=LocationReviewStatus.NEEDS_REVIEW.value),
        )
