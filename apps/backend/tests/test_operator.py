"""Tests for bounded local operator commands."""

import errno
import json
from io import StringIO
from pathlib import Path

import pytest

from wef_backend import operator
from wef_backend.features.ingestion.domain import (
    CountBucket,
    DryRunCounts,
    DryRunErrorCode,
    DryRunReport,
    DryRunSource,
    DryRunTerminalStatus,
    StageTiming,
)
from wef_backend.features.ingestion.infrastructure import ReportWriteError
from wef_backend.operator import OperatorExitCode, UnsafeSourceMountError, inspect_source
from wef_backend.settings import Settings


def test_inspect_source_rejects_missing_directory(tmp_path: Path) -> None:
    """A missing source is rejected before any scan."""
    with pytest.raises(UnsafeSourceMountError, match="does not exist"):
        inspect_source(tmp_path / "missing")


def test_inspect_source_rejects_writable_directory(tmp_path: Path) -> None:
    """A source mount must not permit importer writes."""
    with pytest.raises(UnsafeSourceMountError, match="must be mounted read-only"):
        inspect_source(tmp_path)

    assert not (tmp_path / ".wef-write-probe").exists()


def test_inspect_source_propagates_unexpected_probe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected filesystem failures are preserved for diagnosis."""
    error = OSError(errno.EIO, "synthetic I/O failure")

    def fail_touch(_self: Path, *, mode: int = 0o666, exist_ok: bool = True) -> None:
        del mode, exist_ok
        raise error

    monkeypatch.setattr(Path, "touch", fail_touch)

    with pytest.raises(OSError, match="synthetic I/O failure") as raised:
        inspect_source(tmp_path)

    assert raised.value is error


@pytest.mark.parametrize("probe_errno", [errno.EACCES, errno.EROFS])
def test_inspect_source_accepts_read_only_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_errno: int,
) -> None:
    """Expected read-only errors result in bounded metadata."""
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "listing.json").write_text("{}", encoding="utf-8")

    def reject_touch(_self: Path, *, mode: int = 0o666, exist_ok: bool = True) -> None:
        del mode, exist_ok
        raise OSError(probe_errno, "read-only")

    monkeypatch.setattr(Path, "touch", reject_touch)

    assert inspect_source(tmp_path) == operator.SourceInspection(
        file_count=1,
        read_only=True,
        source=str(tmp_path),
    )


def test_run_operator_emits_redacted_success_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator output contains status/counts but no configured internal paths."""
    settings = Settings(
        source_path=tmp_path,
        ingestion_report_path=tmp_path / "private" / "report",
    )
    output = StringIO()
    written: list[DryRunReport] = []

    class FakeWriter:
        def __init__(self, destination: Path) -> None:
            assert destination == settings.ingestion_report_path

        def write(self, report: DryRunReport) -> None:
            written.append(report)

    monkeypatch.setattr(
        operator,
        "inspect_source",
        lambda _source: operator.SourceInspection(
            file_count=2,
            read_only=True,
            source=str(tmp_path),
        ),
    )
    monkeypatch.setattr(operator, "TelegramDesktopExportAdapter", lambda *_args: object())
    monkeypatch.setattr(operator, "run_dry_run", lambda *_args, **_kwargs: _report())
    monkeypatch.setattr(operator, "AtomicReportWriter", FakeWriter)

    exit_code = operator.run_operator(settings, stdout=output)

    assert exit_code is OperatorExitCode.SUCCEEDED
    assert written == [_report()]
    assert json.loads(output.getvalue()) == {
        "error_code": None,
        "records_total": 1,
        "status": "succeeded",
    }
    assert str(tmp_path) not in output.getvalue()


@pytest.mark.parametrize(
    ("status", "error", "exit_code"),
    [
        (DryRunTerminalStatus.EMPTY, None, OperatorExitCode.EMPTY),
        (DryRunTerminalStatus.PARTIAL, DryRunErrorCode.SOURCE_IO, OperatorExitCode.PARTIAL),
        (
            DryRunTerminalStatus.CANCELLED,
            DryRunErrorCode.CANCELLED,
            OperatorExitCode.CANCELLED,
        ),
        (DryRunTerminalStatus.FAILED, DryRunErrorCode.SOURCE_IO, OperatorExitCode.FAILED),
    ],
)
def test_run_operator_has_stable_terminal_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: DryRunTerminalStatus,
    error: DryRunErrorCode | None,
    exit_code: OperatorExitCode,
) -> None:
    """Automation can distinguish every non-success terminal state."""
    report = _report(status=status, error=error)

    class FakeWriter:
        def __init__(self, _destination: Path) -> None:
            return

        def write(self, _report_value: DryRunReport) -> None:
            return

    monkeypatch.setattr(
        operator,
        "inspect_source",
        lambda _source: operator.SourceInspection(
            file_count=0,
            read_only=True,
            source="redacted",
        ),
    )
    monkeypatch.setattr(operator, "TelegramDesktopExportAdapter", lambda *_args: object())
    monkeypatch.setattr(operator, "run_dry_run", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(operator, "AtomicReportWriter", FakeWriter)

    assert operator.run_operator(Settings(source_path=tmp_path), stdout=StringIO()) is exit_code


def test_run_operator_redacts_mount_and_report_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuration and output failures never print private paths."""
    output = StringIO()
    monkeypatch.setattr(
        operator,
        "inspect_source",
        lambda _source: (_ for _ in ()).throw(UnsafeSourceMountError(f"private: {tmp_path}")),
    )
    assert (
        operator.run_operator(Settings(source_path=tmp_path), stdout=output)
        is OperatorExitCode.CONFIGURATION
    )
    assert str(tmp_path) not in output.getvalue()

    class FailingWriter:
        def __init__(self, _destination: Path) -> None:
            return

        def write(self, _report_value: DryRunReport) -> None:
            raise ReportWriteError

    output = StringIO()
    monkeypatch.setattr(
        operator,
        "inspect_source",
        lambda _source: operator.SourceInspection(
            file_count=1,
            read_only=True,
            source="redacted",
        ),
    )
    monkeypatch.setattr(operator, "TelegramDesktopExportAdapter", lambda *_args: object())
    monkeypatch.setattr(operator, "run_dry_run", lambda *_args, **_kwargs: _report())
    monkeypatch.setattr(operator, "AtomicReportWriter", FailingWriter)
    assert (
        operator.run_operator(Settings(source_path=tmp_path), stdout=output)
        is OperatorExitCode.REPORT_IO
    )
    assert json.loads(output.getvalue())["error_code"] == "report_io"


def test_main_returns_operator_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """The console entry point delegates its stable integer result."""
    monkeypatch.setattr(operator, "load_settings", Settings)
    monkeypatch.setattr(
        operator,
        "run_operator",
        lambda _settings: OperatorExitCode.SUCCEEDED,
    )

    assert operator.main() == 0


def _report(
    *,
    status: DryRunTerminalStatus = DryRunTerminalStatus.SUCCEEDED,
    error: DryRunErrorCode | None = None,
) -> DryRunReport:
    complete = status in {DryRunTerminalStatus.SUCCEEDED, DryRunTerminalStatus.EMPTY}
    records = (
        1
        if status
        in {
            DryRunTerminalStatus.SUCCEEDED,
            DryRunTerminalStatus.PARTIAL,
        }
        else 0
    )
    source = DryRunSource(
        platform="telegram",
        channel_id="safe",
        channel_type="public_channel",
        file_size=10,
        checksum="a" * 64 if complete else None,
        published_from=None,
        published_to=None,
    )

    return DryRunReport(
        report_version="e2-report-v1",
        parser_version="e2-v1",
        grouping_version="e2-media-v1",
        terminal_status=status,
        error_code=error,
        source=source,
        counts=DryRunCounts(
            records_total=records,
            messages_evaluated=records,
            candidates=0,
            non_candidates=records,
            media_total=0,
            media_associated=0,
            media_unassociated=0,
        ),
        source_classifications=(CountBucket("text", 1),) if records else (),
        candidate_reasons=(),
        content_types=(),
        extracted_fields=(),
        warning_codes=(),
        media_rules=(),
        unassociated_media_reasons=(),
        timings=(StageTiming("total", 0),),
    )
