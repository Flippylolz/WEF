"""Real PostGIS proof that uncertain offers remain visible without invented points."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, update

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import (
    BoundingBox,
    BrowseLocationOffers,
    MapFilters,
    QueryMapLocations,
    SeedM1Catalog,
)
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.application.unmapped_listings import BrowseUnmappedListings
from wef_backend.features.catalog.infrastructure import (
    LocationRow,
    OfferRow,
    SQLAlchemyCatalogBrowseAdapter,
    SQLAlchemyCatalogSeedAdapter,
    SQLAlchemyMapQueryAdapter,
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.features.catalog.interface.presenter import present_unmapped_listing_page
from wef_backend.features.identity.infrastructure.favorite_store import SQLAlchemyFavoriteStore
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.migration import alembic_command, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS is required")
CENTER = UUID("10000000-0000-4000-8000-000000000001")
CENTER_OFFER = UUID("20000000-0000-4000-8000-000000000001")
WARSAW = BoundingBox.parse("20.7,52.0,21.4,52.4")


async def test_non_spatial_discovery_preserves_detail_favorites_and_counts() -> None:  # noqa: PLR0915 - one persisted transition with restoration
    """Quarantine an accepted point without losing the visible offers or saved IDs."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini")
    )
    await asyncio.to_thread(alembic_command.upgrade, alembic_config(settings), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    seed = SeedM1Catalog(SQLAlchemyCatalogSeedAdapter(database.session_factory), environment="test")
    await seed(*m1_fixture())
    adapter = SQLAlchemyCatalogBrowseAdapter(database.session_factory)
    discovery = BrowseUnmappedListings(adapter)
    map_service = QueryMapLocations(SQLAlchemyMapQueryAdapter(database.session_factory))
    favorites = SQLAlchemyFavoriteStore(database.session_factory)
    user_id = uuid4()
    try:
        async with database.session_factory() as session:
            session.add(
                UserRow(
                    id=user_id,
                    username_normalized=f"e26_{user_id.hex}",
                    username_display="Synthetic E26",
                    hashed_password="not-a-login-hash",
                    role="user",
                )
            )
            await session.commit()
        assert await favorites.add_favorite(user_id, CENTER)
        baseline = await discovery(filters=MapFilters(bbox=WARSAW), cursor=None, limit=10)
        assert baseline.matching_count == 0
        assert baseline.mapped_matching_count == 5
        mapped = (await map_service(MapFilters(bbox=WARSAW))).records
        assert len(mapped) == 4
        area = next(item for item in mapped if item.precision == "district")
        assert area.location_accuracy is not None
        assert area.location_accuracy.label == "Approximate area"

        async with database.session_factory() as session:
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == CENTER)
                .values(review_status="needs_review", point=None)
            )
            await session.commit()
        assert [item.location_id for item in await favorites.list_favorites(user_id)] == [CENTER]
        assert await favorites.add_favorite(user_id, CENTER)
        outside = MapFilters(bbox=BoundingBox.parse("20.90,52.20,20.97,52.25"))
        first = await discovery(filters=outside, cursor=None, limit=1)
        assert first.matching_count == 2
        assert first.mapped_matching_count == 1
        assert first.next_cursor is not None
        second = await discovery(filters=outside, cursor=first.next_cursor, limit=2)
        assert second.next_cursor is None
        assert len({item.id for item in (*first.items, *second.items)}) == 2
        for item in present_unmapped_listing_page(second).model_dump()["items"]:
            assert "geometry" not in item["location"]

        filtered = await discovery(
            filters=MapFilters(
                bbox=outside.bbox, districts=("srodmiescie",), price_min=100_000_000
            ),
            cursor=None,
            limit=10,
        )
        assert filtered.matching_count == 2
        assert {item.location.id for item in filtered.items} == {CENTER}
        selected = await BrowseLocationOffers(adapter)(
            location_id=CENTER, filters=outside, include_non_matching=False, cursor=None, limit=10
        )
        assert selected.location_exists
        assert selected.matching_count == 2
        assert selected.location is not None
        assert selected.location.location_accuracy is not None
        assert selected.location.location_accuracy.precision == "unresolved"
        detail = await SQLAlchemyOfferDetailAdapter(database.session_factory).query_offer_detail(
            CENTER_OFFER
        )
        assert detail is not None
        assert detail.location.location_accuracy is not None
        assert detail.location.location_accuracy.precision == "unresolved"

        async with database.session_factory() as session:
            await session.execute(
                update(OfferRow).where(OfferRow.location_id == CENTER).values(visibility="hidden")
            )
            await session.commit()
        assert await favorites.list_favorites(user_id) == ()
        assert not await favorites.add_favorite(user_id, CENTER)
        assert (
            await SQLAlchemyOfferDetailAdapter(database.session_factory).query_offer_detail(
                CENTER_OFFER
            )
            is None
        )
        hidden = await discovery(filters=MapFilters(bbox=WARSAW), cursor=None, limit=10)
        assert hidden.matching_count == 0
    finally:
        async with database.session_factory() as session:
            await session.execute(delete(UserRow).where(UserRow.id == user_id))
            await session.commit()
        await seed(*m1_fixture())
        await database.engine.dispose()
