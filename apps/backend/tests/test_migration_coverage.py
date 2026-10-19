"""Real migration rehearsals retain schema and refuse populated evidence loss."""

from __future__ import annotations

import asyncio
import os
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    TelegramChannelProgressRow,
    TelegramRawEventRow,
)
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from wef_backend.database import DatabaseResources

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _config() -> Config:
    if TEST_DATABASE_URL is None or urlsplit(TEST_DATABASE_URL).path != "/wef_test":
        message = "migration rehearsals require the reserved wef_test database"
        raise RuntimeError(message)
    return alembic_config(
        Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))
    )


async def _empty_database(db: DatabaseResources) -> None:
    # _config has already restricted every destructive rehearsal to wef_test.
    async with db.session_factory.begin() as session:
        names = (
            await session.scalars(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename NOT IN ('spatial_ref_sys','alembic_version')"
                )
            )
        ).all()
        quoted = ",".join(
            db.engine.dialect.identifier_preparer.quote_identifier(name) for name in names
        )
        if quoted:
            await session.execute(text(f"TRUNCATE TABLE {quoted} CASCADE"))


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="reserved PostGIS test database required")
async def test_migration_schema_survives_empty_database_round_trip() -> None:
    config = _config()
    await asyncio.to_thread(command.upgrade, config, "head")
    assert TEST_DATABASE_URL is not None
    db = create_database_resources(TEST_DATABASE_URL)
    await _empty_database(db)
    schema = text(
        "SELECT table_name,column_name,data_type,is_nullable FROM "
        "information_schema.columns WHERE table_schema='public' AND "
        "table_name<>'spatial_ref_sys' ORDER BY "
        "table_name,ordinal_position"
    )
    indexes = text(
        "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE "
        "schemaname='public' AND tablename<>'spatial_ref_sys' ORDER BY "
        "tablename,indexname"
    )
    try:
        async with db.session_factory() as session:
            before_columns = (await session.execute(schema)).all()
            before_indexes = (await session.execute(indexes)).all()
        await asyncio.to_thread(command.downgrade, config, "base")
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE "
                        "table_schema='public' AND table_type='BASE TABLE' AND table_name "
                        "NOT IN ('spatial_ref_sys','alembic_version')"
                    )
                )
                == 0
            )
        await asyncio.to_thread(command.upgrade, config, "head")
        async with db.session_factory() as session:
            assert (await session.execute(schema)).all() == before_columns
            assert (await session.execute(indexes)).all() == before_indexes
            assert (
                await session.scalar(text("SELECT version_num FROM alembic_version"))
                == EXPECTED_DATABASE_REVISION
            )
    finally:
        await db.engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="reserved PostGIS test database required")
@pytest.mark.parametrize("stage", ["archive", "progress", "retry"])
async def test_migration_refuses_to_discard_durable_recovery_evidence(stage: str) -> None:
    config = _config()
    await asyncio.to_thread(command.upgrade, config, "head")
    assert TEST_DATABASE_URL is not None
    db = create_database_resources(TEST_DATABASE_URL)
    await _empty_database(db)
    channel = uuid4()
    try:
        async with db.session_factory.begin() as session:
            if stage == "archive":
                await session.execute(
                    text(
                        "INSERT INTO "
                        "telegram_archive_recovery(channel_external_id,phase,policy_version,"
                        "canary_ids,baseline_count,next_batch_at) "
                        "VALUES ('migration-fixture','running','fixture','[]',0,now())"
                    )
                )
            elif stage == "progress":
                session.add(
                    SourceChannelRow(
                        id=channel,
                        platform="telegram",
                        external_id="migration-fixture",
                        display_name="Synthetic migration source",
                    )
                )
                await session.flush()
                session.add(TelegramChannelProgressRow(source_channel_id=channel))
            else:
                session.add(
                    TelegramRawEventRow(
                        id=uuid4(),
                        event_kind="new",
                        channel_external_id="migration-fixture",
                        external_message_id=7,
                        payload_json={"id": 7},
                        checksum="a" * 64,
                        data_failure_count=1,
                    )
                )
        with pytest.raises(RuntimeError, match="retained"):
            await asyncio.to_thread(command.downgrade, config, "base")
        async with db.session_factory() as session:
            assert (
                await session.scalar(text("SELECT version_num FROM alembic_version"))
                == EXPECTED_DATABASE_REVISION
            )
            if stage == "archive":
                assert (
                    await session.scalar(
                        text(
                            "SELECT phase FROM telegram_archive_recovery WHERE "
                            "channel_external_id='migration-fixture'"
                        )
                    )
                    == "running"
                )
            elif stage == "progress":
                assert (
                    await session.scalar(
                        text(
                            "SELECT source_channel_id FROM telegram_channel_progress WHERE "
                            "source_channel_id=:channel"
                        ),
                        {"channel": channel},
                    )
                    == channel
                )
            else:
                assert (
                    await session.scalar(
                        text(
                            "SELECT data_failure_count FROM telegram_raw_events WHERE "
                            "channel_external_id='migration-fixture'"
                        )
                    )
                    == 1
                )
    finally:
        async with db.session_factory.begin() as session:
            await session.execute(
                text(
                    "DELETE FROM telegram_raw_events WHERE channel_external_id='migration-fixture'"
                )
            )
            await session.execute(
                text(
                    "DELETE FROM telegram_archive_recovery WHERE "
                    "channel_external_id='migration-fixture'"
                )
            )
            await session.execute(
                text("DELETE FROM telegram_channel_progress WHERE source_channel_id=:channel"),
                {"channel": channel},
            )
            await session.execute(
                text("DELETE FROM source_channels WHERE id=:channel"), {"channel": channel}
            )
        await db.engine.dispose()


def test_offline_migration_sql_requires_no_database_or_logging_file() -> None:
    output = StringIO()
    config = Config(output_buffer=output)
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://unused.invalid/wef_test")
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE offers" in sql
    assert "CREATE TABLE parser_replay_work" in sql
    assert EXPECTED_DATABASE_REVISION in sql


def test_offline_migration_honors_explicit_logging_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\n[loggers]\nkeys=root\n")
    calls: list[str] = []
    monkeypatch.setattr("logging.config.fileConfig", calls.append)
    output = StringIO()
    config = Config(str(ini), output_buffer=output)
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://unused.invalid/wef_test")
    command.upgrade(config, "head", sql=True)
    assert calls == [str(ini)]
    assert "CREATE TABLE offers" in output.getvalue()
