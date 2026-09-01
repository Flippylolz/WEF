"""Tests for parse-issue ledger backfill."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.infrastructure.models import SourceMessageRow

from tests.test_persistence_application import _raw
from tests.test_persistence_integration import (
    TEST_DATABASE_URL,
    _plain,
    _prepare,
    _purge,
    _settings,
)
from wef_backend import backfill_parse_issues_command
from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.persistence import (
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure import parse_issue_backfill as backfill_module
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import (
    backfill_parse_issues,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)


def test_payload_for_message_falls_back_to_external_id() -> None:
    payload = backfill_module._payload_for_message(payload="", external_message_id=99)  # noqa: SLF001
    assert payload == {"id": 99}


def test_row_to_raw_builds_message_from_projection() -> None:
    message = cast(
        "SourceMessageRow",
        SimpleNamespace(
            external_message_id=12,
            published_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            edited_at=None,
            message_type="message",
            text_original="hello",
            raw_payload_json={"id": 12, "text": "hello"},
            raw_checksum="a" * 64,
            source_channel_id=uuid4(),
            id=uuid4(),
            current_revision_id=uuid4(),
        ),
    )
    raw = backfill_module._row_to_raw(  # noqa: SLF001
        message=message,
        channel_external_id="2180077318",
        channel_name="Test channel",
    )
    assert raw.external_message_id == 12
    assert raw.text == "hello"
    assert raw.source.channel_id == "2180077318"


@pytest.mark.asyncio
async def test_backfill_parse_issues_respects_limit_and_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    async def _fake_process_batch(_session: object, *, batch_size: int) -> tuple[int, int, int]:
        calls.append(batch_size)
        if len(calls) == 1:
            return 4, 1, 5
        return 0, 0, 0

    monkeypatch.setattr(backfill_module, "_process_batch", _fake_process_batch)

    class _Session:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        def begin(self) -> _Begin:
            return _Begin(self)

    class _Begin:
        def __init__(self, session: _Session) -> None:
            self._session = session

        async def __aenter__(self) -> _Session:
            return self._session

        async def __aexit__(self, *_args: object) -> None:
            return None

    class _SessionFactory:
        def __call__(self) -> _Session:
            return _Session()

    summary = await backfill_parse_issues(
        cast("async_sessionmaker[AsyncSession]", _SessionFactory()),
        limit=5,
        batch_size=10,
    )
    assert summary.processed == 5
    assert summary.inserted == 4
    assert summary.skipped_clean == 1
    assert summary.batches == 1
    assert calls == [5]


@pytest.mark.asyncio
async def test_backfill_parse_issues_rejects_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size must be positive"):
        await backfill_parse_issues(AsyncMock(), batch_size=0)


@pytest.mark.asyncio
async def test_backfill_parse_issues_command_run_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed = False

    class _Engine:
        async def dispose(self) -> None:
            nonlocal disposed
            disposed = True

    class _Database:
        session_factory = object()
        engine = _Engine()

    async def _fake_backfill(
        *_args: object,
        **_kwargs: object,
    ) -> backfill_module.ParseIssueBackfillSummary:
        return backfill_module.ParseIssueBackfillSummary(
            processed=0,
            inserted=0,
            skipped_clean=0,
            batches=0,
        )

    monkeypatch.setattr(
        backfill_parse_issues_command,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://example/unused"),
    )
    monkeypatch.setattr(
        backfill_parse_issues_command,
        "create_database_resources",
        lambda _url: _Database(),
    )
    monkeypatch.setattr(backfill_parse_issues_command, "backfill_parse_issues", _fake_backfill)
    payload = await backfill_parse_issues_command.run(limit=10, batch_size=25)
    assert payload == {
        "processed": 0,
        "inserted": 0,
        "skipped_clean": 0,
        "batches": 0,
    }
    assert disposed is True


@pytest.mark.asyncio
async def test_backfill_parse_issues_inserts_missing_rows() -> None:
    """Historical non-offer messages without ledger rows are backfilled once."""
    if TEST_DATABASE_URL is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _prepare()
    settings = _settings()
    database = create_database_resources(settings.database_url)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    service = PersistHistoricalIngestion(store=store, batch_size=10)
    await service(
        channel=_raw().source,
        messages=[_plain(42, "random service message", "c" * 64)],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session, session.begin():
        await session.execute(text("DELETE FROM source_message_parse_issues"))
    summary = await backfill_parse_issues(database.session_factory, batch_size=10)
    assert summary.processed == 1
    assert summary.inserted == 1
    assert summary.skipped_clean == 0
    async with database.session_factory() as session:
        count = await session.scalar(
            text("SELECT count(*) FROM source_message_parse_issues"),
        )
    assert count == 1
    repeat = await backfill_parse_issues(database.session_factory, batch_size=10)
    assert repeat.processed == 0
    assert repeat.inserted == 0
    await database.engine.dispose()
    await _purge()


def test_backfill_parse_issues_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_run(*, limit: int | None, batch_size: int) -> dict[str, int]:
        assert limit == 25
        assert batch_size == 100
        return {"processed": 25, "inserted": 20, "skipped_clean": 5, "batches": 1}

    monkeypatch.setattr(backfill_parse_issues_command, "run", _fake_run)
    backfill_parse_issues_command.main(["--limit", "25", "--batch-size", "100"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["inserted"] == 20
    assert payload["batches"] == 1


def test_backfill_parse_issues_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(*, limit: int | None, batch_size: int) -> dict[str, int]:
        _ = (limit, batch_size)
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(backfill_parse_issues_command, "run", _boom)
    with pytest.raises(SystemExit) as exited:
        backfill_parse_issues_command.main([])
    assert exited.value.code == 2
