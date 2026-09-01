"""Tests for parse-issue ledger backfill."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

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
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import (
    backfill_parse_issues,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)


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
