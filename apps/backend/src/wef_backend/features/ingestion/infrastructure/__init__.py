"""Source-specific ingestion adapter implementations."""

from wef_backend.features.ingestion.infrastructure.report_writer import (
    AtomicReportWriter,
    ReportPaths,
    ReportWriteError,
    report_document,
)
from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
    TelegramExportScan,
)

__all__ = [
    "AtomicReportWriter",
    "ReportPaths",
    "ReportWriteError",
    "TelegramDesktopExportAdapter",
    "TelegramExportScan",
    "report_document",
]
