"""Disposable-PostGIS tests for parser replay over the raw archive (E17-T2)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    RunCheckpoint,
    RunCounts,
    RunMode,
)
from wef_backend.features.ingestion.application.raw_replay import RawParserReplayer
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    live_message_payload,
    live_message_to_raw,
    source_identity_from_channel,
)
from wef_backend.features.ingestion.domain.model import canonical_json_checksum
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
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

TEXT = "Покупка | Квартира\n📍 ul. Testowa Integracyjna, Wola, Warszawa\nЦена: 900 000 PLN"


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )


def _resources() -> tuple[SQLAlchemyIngestionPersistence, SQLAlchemyRawEventArchive, AsyncEngine]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return (
        SQLAlchemyIngestionPersistence(factory),
        SQLAlchemyRawEventArchive(factory),
        engine,
    )


def _message(external_id: int) -> LiveTelegramMessage:
    return LiveTelegramMessage(
        external_message_id=external_id,
        text=TEXT,
        published_at=datetime(2026, 8, 29, 8, 0, tzinfo=UTC),
        edited_at=None,
    )


async def _primary_parser_version(engine: AsyncEngine, external_id: int) -> str | None:
    async with engine.connect() as connection:
        value = await connection.execute(
            text(
                "SELECT o.parser_version FROM offers o "
                "JOIN offer_sources os ON os.offer_id = o.id "
                "JOIN source_messages sm ON sm.id = os.source_message_id "
                "WHERE os.relationship = 'primary' AND sm.external_message_id = :eid "
                "ORDER BY o.id LIMIT 1",
            ),
            {"eid": external_id},
        )
        return value.scalar_one_or_none()


async def test_replay_rewrites_stale_offers_and_is_idempotent() -> None:
    """A stale-parser offer re-derives from the archive; a second run no-ops."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    store, archive, engine = _resources()
    identity = default_live_channel_identity()
    channel = source_identity_from_channel(identity)
    message = _message(9001)
    external_id = message.external_message_id
    try:
        channel_id = await store.ensure_channel(
            platform=channel.platform.value,
            external_id=channel.channel_id,
            display_name=channel.channel_name,
        )
        run_id = await store.start_run(
            channel_id=channel_id,
            mode=RunMode.LIVE,
            parser_version=PARSER_VERSION,
            source_checksum=None,
            release_sha=None,
        )
        raw = live_message_to_raw(message, identity=channel)
        await store.persist_live_upsert(
            channel_id=channel_id,
            run_id=run_id,
            message=PersistableMessage(
                raw=raw,
                extraction=extract_listing(raw),
            ),
            checkpoint=RunCheckpoint(),
            counts=RunCounts(),
            advance_checkpoint=True,
        )
        assert await _primary_parser_version(engine, external_id) == PARSER_VERSION

        await archive.land(
            event_kind="new",
            channel_external_id=identity.channel_id,
            external_message_id=external_id,
            payload=live_message_payload(message),
            checksum=canonical_json_checksum(live_message_payload(message)),
        )

        async with engine.begin() as connection:
            await connection.execute(text("UPDATE offers SET parser_version = 'e2-v1'"))
        assert await _primary_parser_version(engine, external_id) == "e2-v1"

        replayer = RawParserReplayer(store=store, source=archive, identity=identity)
        summary = await replayer(release_sha="test-sha")
        assert summary.reprocessed == 1
        assert summary.stale_after_replay == 0
        assert await _primary_parser_version(engine, external_id) == PARSER_VERSION

        again = await replayer(release_sha="test-sha")
        assert again.reprocessed == 0
        assert again.stale_after_replay == 0
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM offer_sources WHERE source_message_id IN "
                    "(SELECT id FROM source_messages WHERE external_message_id = :eid)",
                ),
                {"eid": external_id},
            )
            await connection.execute(
                text(
                    "DELETE FROM offers WHERE id IN "
                    "(SELECT offer_id FROM offer_sources WHERE offer_id NOT IN "
                    "(SELECT offer_id FROM offer_sources))",
                ),
            )
            await connection.execute(
                text(
                    "DELETE FROM locations WHERE id NOT IN "
                    "(SELECT location_id FROM offers) AND display_address = :addr",
                ),
                {"addr": "ul. Testowa Integracyjna, Wola, Warszawa"},
            )
            await connection.execute(
                text("DELETE FROM source_messages WHERE external_message_id = :eid"),
                {"eid": external_id},
            )
            await connection.execute(
                text(
                    "DELETE FROM source_message_revisions WHERE source_message_id NOT IN "
                    "(SELECT id FROM source_messages)",
                ),
            )
            await connection.execute(
                text(
                    "DELETE FROM ingest_runs WHERE source_channel_id IN "
                    "(SELECT id FROM source_channels WHERE external_id = :cid)",
                ),
                {"cid": identity.channel_id},
            )
            await connection.execute(
                text("DELETE FROM source_channels WHERE external_id = :cid"),
                {"cid": identity.channel_id},
            )
            await connection.execute(text("DELETE FROM telegram_raw_events"))
        await engine.dispose()
