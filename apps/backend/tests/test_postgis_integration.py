"""Real PostGIS adapter proof gated by an explicit disposable database URL."""

import os
from typing import cast

import pytest
from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wef_backend.database import create_database_resources
from wef_backend.features.estates.infrastructure import (
    Base,
    EstateRow,
    SQLAlchemyEstateQueryAdapter,
)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SYNTHETIC_ESTATE_ID = 2_000_000_001

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        TEST_DATABASE_URL is None,
        reason="TEST_DATABASE_URL is not configured",
    ),
]


async def test_adapter_maps_a_real_postgis_point() -> None:
    """Round-trip a synthetic point while rolling all state back."""
    assert TEST_DATABASE_URL is not None
    database = create_database_resources(TEST_DATABASE_URL)
    connection = await database.engine.connect()
    transaction = await connection.begin()

    try:
        await connection.execute(text("SELECT PostGIS_Version()"))
        await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker[AsyncSession](
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            session.add(
                EstateRow(
                    estate_id=SYNTHETIC_ESTATE_ID,
                    title="Synthetic PostGIS cabin",
                    availability="available",
                    location=cast(
                        "WKBElement",
                        WKTElement("POINT(21.0122 52.2297)", srid=4326),
                    ),
                ),
            )
            await session.commit()

        records = await SQLAlchemyEstateQueryAdapter(session_factory).list_estate_records()
        record = next(item for item in records if item.estate_id == SYNTHETIC_ESTATE_ID)

        assert record.location.longitude == pytest.approx(21.0122)
        assert record.location.latitude == pytest.approx(52.2297)
        assert record.availability.label_key == "estates.availability.available"
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
        await database.engine.dispose()
