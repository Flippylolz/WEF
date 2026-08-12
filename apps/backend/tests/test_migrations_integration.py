"""Forward migration and deterministic seed checks against disposable PostGIS."""

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend.composition import build_services
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        TEST_DATABASE_URL is None,
        reason="TEST_DATABASE_URL is not configured",
    ),
]


async def test_clean_upgrade_and_seed_replay_converge() -> None:
    """Upgrade twice and replay the fixture without duplicate rows."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    locations, offers = m1_fixture()
    location_ids = tuple(item.id for item in locations)
    offer_ids = tuple(item.id for item in offers)

    try:
        async with database.engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS e0_proof_estates (estate_id bigint PRIMARY KEY)",
                ),
            )

        await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")
        await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")

        service = SeedM1Catalog(
            SQLAlchemyCatalogSeedAdapter(database.session_factory),
            environment="test",
        )
        assert await service(locations, offers) == await service(locations, offers)

        async with database.session_factory() as session:
            revision = await session.scalar(
                text("SELECT version_num FROM alembic_version"),
            )
            location_count = await session.scalar(
                text("SELECT count(*) FROM locations WHERE id = ANY(:ids)"),
                {"ids": location_ids},
            )
            offer_count = await session.scalar(
                text("SELECT count(*) FROM offers WHERE id = ANY(:ids)"),
                {"ids": offer_ids},
            )
            point = (
                await session.execute(
                    text(
                        "SELECT ST_X(point), ST_Y(point) FROM locations WHERE id = :location_id",
                    ),
                    {"location_id": location_ids[0]},
                )
            ).one()
            forbidden_columns = await session.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name = 'offers' "
                    "AND column_name IN ('available', 'active', 'sold')",
                ),
            )
            gist_index = await session.scalar(
                text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE tablename = 'locations' "
                    "AND indexname = 'ix_locations_point_gist' "
                    "AND indexdef ILIKE '%USING gist%'",
                ),
            )
            check_constraints = await session.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conname LIKE 'ck_locations_%' "
                    "OR conname LIKE 'ck_offers_%'",
                ),
            )
            proof_table = await session.scalar(
                text("SELECT to_regclass('public.e0_proof_estates') IS NOT NULL"),
            )

        assert revision == EXPECTED_DATABASE_REVISION
        assert location_count == 4
        assert offer_count == 5
        assert tuple(float(value) for value in point) == pytest.approx((21.0122, 52.2297))
        assert forbidden_columns == 0
        assert gist_index == 1
        assert check_constraints == 13
        assert proof_table is True
        services = build_services(settings)
        assert await services.is_ready() is True
        await services.close()
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM offers WHERE id = ANY(:ids)"),
                {"ids": offer_ids},
            )
            await connection.execute(
                text("DELETE FROM locations WHERE id = ANY(:ids)"),
                {"ids": location_ids},
            )
            await connection.execute(text("DROP TABLE IF EXISTS e0_proof_estates"))
        await database.engine.dispose()
