"""Disposable-PostGIS tests for the verbatim raw-event archive (E17-T1)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )


def _archive() -> tuple[SQLAlchemyRawEventArchive, AsyncEngine]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return SQLAlchemyRawEventArchive(factory), engine


async def _clear() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as session:
        await session.execute(text("DELETE FROM telegram_raw_events"))
    await engine.dispose()


async def test_land_dedupe_outcomes_and_bounded_retries() -> None:
    """Landing is idempotent per unique key; failures retry until the cap."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    archive, engine = _archive()
    payload = {
        "id": 101,
        "type": "message",
        "date_unixtime": "1770000000",
        "text": "test listing text",
        "from_live": True,
    }
    try:
        first = await archive.land(
            event_kind="new",
            channel_external_id="2180077318",
            external_message_id=101,
            payload=payload,
            checksum="a" * 64,
        )
        duplicate = await archive.land(
            event_kind="new",
            channel_external_id="2180077318",
            external_message_id=101,
            payload=payload,
            checksum="a" * 64,
        )
        assert first == duplicate

        second = await archive.land(
            event_kind="new",
            channel_external_id="2180077318",
            external_message_id=102,
            payload={**payload, "id": 102},
            checksum="b" * 64,
        )
        assert second != first

        pending = await archive.unprocessed_batch(10)
        assert [record.external_message_id for record in pending] == [101, 102]

        await archive.mark_attempt(first, outcome="processed", completed_at=NOW)
        still_pending = await archive.unprocessed_batch(10)
        assert [record.external_message_id for record in still_pending] == [102]

        for _ in range(4):
            await archive.mark_attempt(
                second,
                outcome="failed",
                error_category="PersistenceBatchError",
                completed_at=NOW,
            )
        retryable = await archive.unprocessed_batch(10)
        assert [record.external_message_id for record in retryable] == [102]
        assert retryable[0].attempts == 4

        await archive.mark_attempt(
            second,
            outcome="failed",
            error_category="PersistenceBatchError",
            completed_at=NOW,
        )
        exhausted = await archive.unprocessed_batch(10)
        assert exhausted == ()
        assert await archive.failed_exhausted_count() == 1
    finally:
        await _clear()
        await engine.dispose()


async def test_delete_events_land_one_row_per_id() -> None:
    """Delete batches land one verbatim row per deleted message id."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    archive, engine = _archive()
    try:
        for deleted_id in (201, 202):
            await archive.land(
                event_kind="delete",
                channel_external_id="2180077318",
                external_message_id=deleted_id,
                payload={"id": deleted_id, "type": "deleted_message", "from_live": True},
                checksum=f"{deleted_id:064x}",
            )
        pending = await archive.unprocessed_batch(10)
        assert sorted(record.event_kind for record in pending) == ["delete", "delete"]
        assert sorted(record.external_message_id for record in pending) == [201, 202]
    finally:
        await _clear()
        await engine.dispose()
