"""Source-specific ingestion adapter implementations."""

from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
    TelegramExportScan,
)

__all__ = ["TelegramDesktopExportAdapter", "TelegramExportScan"]
