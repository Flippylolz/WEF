"""Final maintenance receipts handle missing source and repeated worker statuses."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_dry_run_domain import report as _report
from wef_backend import parser_replay_worker
from wef_backend.features.ingestion.application.archive_retry import ArchiveFailure
from wef_backend.features.ingestion.domain.dry_run import DryRunErrorCode, DryRunTerminalStatus
from wef_backend.features.ingestion.infrastructure.archive_retry_store import record_retry
from wef_backend.features.ingestion.infrastructure.models import (
    SourceMessageRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import _row_to_raw
from wef_backend.features.ingestion.infrastructure.report_writer import report_document
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.dry_run import DryRunReport

report = _report


@pytest.mark.parametrize("failed", [False, True])
async def test_parser_worker_logs_unchanged_status_only_once(
    *,
    failed: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = asyncio.Event()
    replay = MagicMock(
        tick=AsyncMock(side_effect=RuntimeError if failed else None),
        counts=AsyncMock(return_value={"observed": 1}),
    )
    monkeypatch.setattr(parser_replay_worker, "SQLAlchemyParserReplay", lambda _: replay)
    log = MagicMock()
    monkeypatch.setattr(parser_replay_worker, "logger", log)
    waits = 0

    async def cadence(awaitable: object, *, timeout: int) -> None:  # noqa: ASYNC109
        nonlocal waits
        assert timeout == 60
        waits += 1
        if waits == 1:
            awaitable.close()  # type: ignore[attr-defined]
            raise TimeoutError
        stop.set()
        await awaitable  # type: ignore[misc]

    monkeypatch.setattr(asyncio, "wait_for", cadence)
    await parser_replay_worker.maintain_parser_replay(
        Settings(parser_replay_enabled=True),
        MagicMock(),
        stop,
        lambda: True,
    )
    assert replay.tick.await_count == 2
    assert log.info.call_count == int(not failed)
    assert log.warning.call_count == int(failed)


async def test_systemic_retry_without_recovery_control_preserves_the_deferred_event() -> None:
    row = TelegramRawEventRow(
        processed_at=None,
        attempts=0,
        data_failure_count=0,
        deferral_count=0,
        channel_external_id="fixture",
    )
    session = MagicMock(scalar=AsyncMock(return_value=row), get=AsyncMock(return_value=None))
    now = datetime.now(UTC)
    assert await record_retry(session, uuid4(), ArchiveFailure("systemic", "Unavailable"), now, 0)
    assert row.data_failure_count == 0
    assert row.deferral_count == 1
    assert row.next_attempt_at is not None
    assert row.next_attempt_at > now
    session.add.assert_not_called()


def test_failed_report_can_omit_unavailable_source_metadata(report: DryRunReport) -> None:
    failed = replace(
        report,
        source=None,
        terminal_status=DryRunTerminalStatus.FAILED,
        error_code=DryRunErrorCode.SOURCE_IO,
    )
    document = report_document(failed)
    assert document["source"] is None
    assert document["terminal_status"] == "failed"


def test_backfill_freezes_mapping_payload_without_changing_the_retained_source() -> None:
    payload: dict[str, object] = {"id": 7, "tags": ["synthetic"]}
    row = SourceMessageRow(
        external_message_id=7,
        raw_payload_json=payload,
        published_at=datetime.now(UTC),
        edited_at=None,
        message_type="message",
        text_original="fixture",
        raw_checksum="a" * 64,
    )
    raw = _row_to_raw(message=row, channel_external_id="fixture", channel_name="Synthetic")
    assert raw.raw_payload["tags"] == ("synthetic",)
    assert payload["tags"] == ["synthetic"]
