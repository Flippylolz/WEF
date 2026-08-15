"""Source-specific ingestion adapter implementations."""

from wef_backend.features.ingestion.infrastructure.geocode_store import (
    SQLAlchemyGeocodeStore,
    StaleGeocodeClaimError,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import (
    FixtureGeocoder,
    HostedGeocoder,
    HTTPXJSONTransport,
    ProviderPolicy,
)
from wef_backend.features.ingestion.infrastructure.report_writer import (
    AtomicReportWriter,
    ReportPaths,
    ReportWriteError,
    audit_evidence_document,
    report_document,
)
from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
    TelegramExportScan,
)

__all__ = [
    "AtomicReportWriter",
    "FixtureGeocoder",
    "HTTPXJSONTransport",
    "HostedGeocoder",
    "ProviderPolicy",
    "ReportPaths",
    "ReportWriteError",
    "SQLAlchemyGeocodeStore",
    "StaleGeocodeClaimError",
    "TelegramDesktopExportAdapter",
    "TelegramExportScan",
    "audit_evidence_document",
    "report_document",
]
