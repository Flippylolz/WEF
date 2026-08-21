"""PostGIS integration for historical visibility promotion."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select, update

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import (
    PromotePublicCatalog,
    SeedM1Catalog,
)
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.application.promote_public_catalog import (
    SYNTHETIC_PARSER_VERSION,
)
from wef_backend.features.catalog.domain import LocationReviewStatus, OfferVisibility
from wef_backend.features.catalog.infrastructure import (
    LocationRow,
    OfferRow,
    SQLAlchemyCatalogSeedAdapter,
    SQLAlchemyPromotePublicCatalogAdapter,
)
from wef_backend.migration import alembic_command, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL is required for PostGIS integration",
)

_SYNTHETIC_CENTER = UUID("10000000-0000-4000-8000-000000000001")


@pytest.mark.asyncio
async def test_promote_public_catalog_hides_synthetic_and_publishes_historical() -> None:
    """Synthetic seed is retired; non-synthetic needs_review offers become visible."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    await asyncio.to_thread(alembic_command.upgrade, alembic_config(settings), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    try:
        await SeedM1Catalog(
            SQLAlchemyCatalogSeedAdapter(database.session_factory),
            environment="test",
        )(*m1_fixture())

        async with database.session_factory() as session:
            offer_id = await session.scalar(
                select(OfferRow.id)
                .where(OfferRow.parser_version == SYNTHETIC_PARSER_VERSION)
                .limit(1)
            )
            assert offer_id is not None
            await session.execute(
                update(OfferRow)
                .where(OfferRow.id == offer_id)
                .values(
                    parser_version="historical-e3-v1",
                    visibility=OfferVisibility.NEEDS_REVIEW.value,
                )
            )
            await session.commit()

        result = await PromotePublicCatalog(
            SQLAlchemyPromotePublicCatalogAdapter(database.session_factory),
        )()

        assert result.offers_promoted >= 1
        assert result.synthetic_offers_hidden >= 4
        assert result.synthetic_locations_rejected == 4
        assert result.visible_offers >= 1
        # All fixture locations are synthetic, so promotion rejects every pin.
        assert result.map_eligible_locations == 0

        async with database.session_factory() as session:
            synthetic_visible = await session.scalar(
                select(OfferRow.id)
                .where(
                    OfferRow.parser_version == SYNTHETIC_PARSER_VERSION,
                    OfferRow.visibility == OfferVisibility.VISIBLE.value,
                )
                .limit(1)
            )
            assert synthetic_visible is None
            historical = await session.scalar(
                select(OfferRow.visibility).where(OfferRow.id == offer_id)
            )
            assert historical == OfferVisibility.VISIBLE.value
            status = await session.scalar(
                select(LocationRow.review_status).where(LocationRow.id == _SYNTHETIC_CENTER)
            )
            assert status == LocationReviewStatus.REJECTED.value
    finally:
        await database.engine.dispose()
