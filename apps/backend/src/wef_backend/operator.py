"""Bounded operator commands used by the local Compose topology."""

from __future__ import annotations

import errno
import json
import sys
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application import (
    GROUPING_VERSION,
    ChannelExpectation,
    run_dry_run,
)
from wef_backend.features.ingestion.domain import DryRunTerminalStatus
from wef_backend.features.ingestion.infrastructure import (
    AtomicReportWriter,
    ReportWriteError,
    TelegramDesktopExportAdapter,
)
from wef_backend.settings import load_settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import TextIO

    from wef_backend.settings import Settings


class OperatorExitCode(IntEnum):
    """Stable process exits for automation and human operation."""

    SUCCEEDED = 0
    CONFIGURATION = 2
    EMPTY = 3
    PARTIAL = 4
    FAILED = 5
    REPORT_IO = 6
    CANCELLED = 130


class UnsafeSourceMountError(RuntimeError):
    """Raised when the source path is unavailable or writable."""


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """Non-sensitive metadata emitted by the importer safety probe."""

    file_count: int
    read_only: bool
    source: str


_STATUS_EXITS = {
    DryRunTerminalStatus.SUCCEEDED: OperatorExitCode.SUCCEEDED,
    DryRunTerminalStatus.EMPTY: OperatorExitCode.EMPTY,
    DryRunTerminalStatus.PARTIAL: OperatorExitCode.PARTIAL,
    DryRunTerminalStatus.CANCELLED: OperatorExitCode.CANCELLED,
    DryRunTerminalStatus.FAILED: OperatorExitCode.FAILED,
}


def inspect_source(source: Path) -> SourceInspection:
    """Confirm that an import source exists and is mounted read-only."""
    if not source.is_dir():
        message = f"Source directory does not exist: {source}"
        raise UnsafeSourceMountError(message)

    probe = source / ".wef-write-probe"
    try:
        probe.touch(exist_ok=False)
    except OSError as error:
        if error.errno not in {errno.EACCES, errno.EROFS}:
            raise
    else:
        probe.unlink(missing_ok=True)
        message = f"Source directory must be mounted read-only: {source}"
        raise UnsafeSourceMountError(message)

    file_count = sum(path.is_file() for path in source.rglob("*"))
    return SourceInspection(
        file_count=file_count,
        read_only=True,
        source=str(source),
    )


def run_operator(
    settings: Settings,
    *,
    cancel_requested: Callable[[], bool] | None = None,
    stdout: TextIO | None = None,
) -> OperatorExitCode:
    """Validate the mount, run the bounded pipeline, and atomically write reports."""
    output = stdout or sys.stdout
    try:
        inspection = inspect_source(settings.source_path)
        del inspection
        adapter = TelegramDesktopExportAdapter(
            settings.source_path / settings.historical_export_filename,
            ChannelExpectation(
                channel_id=settings.historical_channel_id,
                channel_type=settings.historical_channel_type,
                channel_name=settings.historical_channel_name,
            ),
        )
        report = run_dry_run(
            adapter,
            parser_version=settings.ingestion_parser_version,
            grouping_version=GROUPING_VERSION,
            cancel_requested=cancel_requested,
        )
        AtomicReportWriter(settings.ingestion_report_path).write(report)
    except UnsafeSourceMountError:
        _emit_operator_summary(
            output,
            status="failed",
            error_code="unsafe_source_mount",
            records_total=0,
        )
        return OperatorExitCode.CONFIGURATION
    except ReportWriteError:
        _emit_operator_summary(
            output,
            status="failed",
            error_code="report_io",
            records_total=0,
        )
        return OperatorExitCode.REPORT_IO

    _emit_operator_summary(
        output,
        status=report.terminal_status.value,
        error_code=report.error_code.value if report.error_code is not None else None,
        records_total=report.counts.records_total,
    )
    return _STATUS_EXITS[report.terminal_status]


def _emit_operator_summary(
    output: TextIO,
    *,
    status: str,
    error_code: str | None,
    records_total: int,
) -> None:
    output.write(
        json.dumps(
            {
                "error_code": error_code,
                "records_total": records_total,
                "status": status,
            },
            sort_keys=True,
        )
        + "\n"
    )


def main() -> int:
    """Run the read-only historical parser and return a stable process code."""
    return int(run_operator(load_settings()))
