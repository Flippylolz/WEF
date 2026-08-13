"""Streaming dry-run orchestration and atomic report tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

import pytest

from wef_backend.features.ingestion.application import (
    ChannelExpectation,
    HistoricalSourcePort,
    ScanSummary,
    SourceErrorCode,
    SourceScanError,
    run_dry_run,
)
from wef_backend.features.ingestion.domain import (
    DryRunErrorCode,
    DryRunTerminalStatus,
    PrimaryClassification,
    RawMessage,
    RecordDisposition,
    RecordResult,
    ScanCounts,
    SourceIdentity,
    SourceMetadata,
    SourcePlatform,
    canonical_json_checksum,
    freeze_json,
)
from wef_backend.features.ingestion.infrastructure import (
    AtomicReportWriter,
    ReportWriteError,
    TelegramDesktopExportAdapter,
    report_document,
)

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

EXPECTATION = ChannelExpectation(
    channel_id="9100",
    channel_type="public_channel",
    channel_name="Synthetic Dry Run",
)


def _write_export(path: Path, messages: list[object]) -> None:
    path.write_text(
        json.dumps(
            {
                "name": EXPECTATION.channel_name,
                "type": EXPECTATION.channel_type,
                "id": int(EXPECTATION.channel_id),
                "messages": messages,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _messages() -> list[object]:
    return [
        {
            "id": 801,
            "type": "message",
            "date_unixtime": "1924992000",
            "text": ("Kupno | Mieszkanie\nCena: 500 000 PLN\nKontakt: +48 600 700 800"),
            "text_entities": [],
            "photo": "photos/sample_dry_run_1.jpg",
        },
        {
            "id": 802,
            "type": "message",
            "date_unixtime": "1924992030",
            "text": "",
            "text_entities": [],
            "photo": "photos/sample_dry_run_2.jpg",
        },
        {
            "id": 803,
            "type": "service",
            "date_unixtime": "1924992060",
            "text": "",
            "text_entities": [],
        },
        {
            "type": "message",
            "date_unixtime": "1924992090",
            "text": "synthetic malformed",
            "text_entities": [],
        },
    ]


def _adapter(path: Path) -> TelegramDesktopExportAdapter:
    return TelegramDesktopExportAdapter(path, EXPECTATION)


def test_complete_dry_run_reconciles_all_source_and_downstream_counts(
    tmp_path: Path,
) -> None:
    """All records, decisions, and media receive one aggregate disposition."""
    source = tmp_path / "source.json"
    _write_export(source, _messages())

    report = run_dry_run(_adapter(source), monotonic=lambda: 0.0)

    assert report.terminal_status is DryRunTerminalStatus.SUCCEEDED
    assert report.error_code is None
    assert report.is_complete
    assert report.source is not None
    assert report.source.file_size == source.stat().st_size
    assert report.source.checksum is not None
    assert report.source.published_from == datetime.fromtimestamp(1924992000, tz=UTC)
    assert report.source.published_to == datetime.fromtimestamp(1924992060, tz=UTC)
    assert report.counts.records_total == 4
    assert report.counts.messages_evaluated == 3
    assert report.counts.candidates == 1
    assert report.counts.non_candidates == 2
    assert report.counts.media_total == 2
    assert report.counts.media_associated == 2
    assert report.counts.media_unassociated == 0
    assert {bucket.name: bucket.count for bucket in report.source_classifications} == {
        "malformed": 1,
        "photo": 2,
        "service": 1,
    }
    assert {bucket.name: bucket.count for bucket in report.media_rules} == {
        "same_message": 1,
        "time_burst": 1,
    }
    assert all(timing.duration_ms == 0 for timing in report.timings)


def test_empty_cancelled_and_invalid_sources_have_distinct_terminal_states(
    tmp_path: Path,
) -> None:
    """Empty completion, cancellation, and preflight failure never masquerade as success."""
    empty_source = tmp_path / "empty.json"
    _write_export(empty_source, [])
    empty = run_dry_run(_adapter(empty_source), monotonic=lambda: 0.0)
    assert empty.terminal_status is DryRunTerminalStatus.EMPTY
    assert empty.error_code is None
    assert empty.source is not None
    assert empty.source.checksum is not None

    populated_source = tmp_path / "populated.json"
    _write_export(populated_source, _messages())
    cancelled = run_dry_run(
        _adapter(populated_source),
        cancel_requested=lambda: True,
        monotonic=lambda: 0.0,
    )
    assert cancelled.terminal_status is DryRunTerminalStatus.CANCELLED
    assert cancelled.error_code is DryRunErrorCode.CANCELLED
    assert cancelled.source is not None
    assert cancelled.source.checksum is None
    assert cancelled.counts.records_total == 0

    invalid_source = tmp_path / "invalid.json"
    invalid_source.write_text("{", encoding="utf-8")
    failed = run_dry_run(_adapter(invalid_source), monotonic=lambda: 0.0)
    assert failed.terminal_status is DryRunTerminalStatus.FAILED
    assert failed.error_code is DryRunErrorCode.TRUNCATED_JSON
    assert failed.source is None


def test_partial_source_failure_preserves_reconciled_counts_without_checksum() -> None:
    """A failure after one record remains explicitly partial."""
    message = _raw_message()
    result = RecordResult(
        source_index=0,
        disposition=RecordDisposition.ACCEPTED,
        classification=PrimaryClassification.TEXT,
        checksum=message.checksum,
        message=message,
    )
    scan = _FailingScan((result,), fail_after=1)

    report = run_dry_run(_FakeSource(scan), monotonic=lambda: 0.0)

    assert report.terminal_status is DryRunTerminalStatus.PARTIAL
    assert report.error_code is DryRunErrorCode.SOURCE_IO
    assert report.source is not None
    assert report.source.checksum is None
    assert report.counts.records_total == 1
    assert sum(bucket.count for bucket in report.source_classifications) == 1


def test_count_mismatch_fails_closed_after_source_exhaustion() -> None:
    """A dishonest terminal source summary cannot produce success."""
    message = _raw_message()
    result = RecordResult(
        source_index=0,
        disposition=RecordDisposition.ACCEPTED,
        classification=PrimaryClassification.TEXT,
        checksum=message.checksum,
        message=message,
    )
    scan = _FailingScan((result,), summary_counts=ScanCounts())

    report = run_dry_run(_FakeSource(scan), monotonic=lambda: 0.0)

    assert report.terminal_status is DryRunTerminalStatus.FAILED
    assert report.error_code is DryRunErrorCode.COUNT_RECONCILIATION
    assert report.source is not None
    assert report.source.checksum == "a" * 64


def test_atomic_report_writer_is_deterministic_and_contains_no_source_samples(
    tmp_path: Path,
) -> None:
    """Machine and human outputs contain only aggregate safe report data."""
    source = tmp_path / "source.json"
    _write_export(source, _messages())
    report = run_dry_run(_adapter(source), monotonic=lambda: 0.0)
    destination = tmp_path / "ignored" / "audit"
    writer = AtomicReportWriter(destination)

    paths = writer.write(report)
    first_json = paths.json_path.read_bytes()
    first_markdown = paths.markdown_path.read_bytes()
    writer.write(report)

    assert paths.json_path.read_bytes() == first_json
    assert paths.markdown_path.read_bytes() == first_markdown
    document = json.loads(first_json)
    assert document == report_document(report)
    rendered = (first_json + first_markdown).decode()
    assert "Kupno | Mieszkanie" not in rendered
    assert "500 000" not in rendered
    assert "+48 600 700 800" not in rendered
    assert "sample_dry_run" not in rendered
    assert str(source) not in rendered
    assert "contact" in rendered


def test_atomic_report_writer_preserves_targets_on_pre_replace_failure(
    tmp_path: Path,
) -> None:
    """Rendered temporary files are cleaned and old reports remain intact."""
    source = tmp_path / "source.json"
    _write_export(source, _messages())
    report = run_dry_run(_adapter(source), monotonic=lambda: 0.0)
    destination = tmp_path / "report"
    json_path = destination.with_suffix(".json")
    markdown_path = destination.with_suffix(".md")
    json_path.write_text("old-json", encoding="utf-8")
    markdown_path.write_text("old-markdown", encoding="utf-8")

    def fail_replace(_source: Path, _target: Path) -> None:
        message = "synthetic replace failure"
        raise OSError(message)

    with pytest.raises(ReportWriteError, match="report write failed"):
        AtomicReportWriter(destination, replace=fail_replace).write(report)

    assert json_path.read_text(encoding="utf-8") == "old-json"
    assert markdown_path.read_text(encoding="utf-8") == "old-markdown"
    assert tuple(tmp_path.glob(".e2-report-*")) == ()


def _raw_message() -> RawMessage:
    payload = {"id": 901, "text": "ordinary message"}
    frozen = freeze_json(payload)
    assert isinstance(frozen, Mapping)
    return RawMessage(
        source=_source_metadata().identity,
        external_message_id=901,
        reply_to_message_id=None,
        published_at=datetime(2031, 1, 1, tzinfo=UTC),
        edited_at=None,
        message_type="message",
        text="ordinary message",
        original_text="ordinary message",
        text_entities=(),
        media=(),
        raw_payload=frozen,
        checksum=canonical_json_checksum(payload),
    )


def _source_metadata() -> SourceMetadata:
    return SourceMetadata(
        identity=SourceIdentity(
            platform=SourcePlatform.TELEGRAM,
            channel_id="fake",
            channel_name="Fake",
            channel_type="public_channel",
        ),
        file_size=10,
    )


class _FakeSource(HistoricalSourcePort):
    def __init__(self, scan: _FailingScan) -> None:
        self._scan = scan

    def open_scan(self) -> _FailingScan:
        return self._scan


class _FailingScan:
    def __init__(
        self,
        records: tuple[RecordResult, ...],
        *,
        fail_after: int | None = None,
        summary_counts: ScanCounts | None = None,
    ) -> None:
        self._records = records
        self._index = 0
        self._fail_after = fail_after
        self._summary_counts = summary_counts or ScanCounts(text=len(records))
        self._complete = False

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> RecordResult:
        if self._fail_after is not None and self._index >= self._fail_after:
            raise SourceScanError(SourceErrorCode.SOURCE_IO)
        if self._index >= len(self._records):
            self._complete = True
            raise StopIteration
        record = self._records[self._index]
        self._index += 1
        return record

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self.close()

    @property
    def is_complete(self) -> bool:
        return self._complete

    @property
    def source(self) -> SourceMetadata:
        return _source_metadata()

    @property
    def summary(self) -> ScanSummary:
        if not self._complete:
            message = "summary unavailable"
            raise AssertionError(message)
        return ScanSummary(
            source=self.source,
            source_checksum="a" * 64,
            counts=self._summary_counts,
        )

    def close(self) -> None:
        return
