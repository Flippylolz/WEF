"""Source-specific ingestion adapter implementations."""

from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    CompleteImportLeaseHeldError,
    ImportVerification,
    LocationWorkItem,
    SourceAnchor,
    SQLAlchemyCompleteImportRepository,
    StaleCompleteImportLeaseError,
)
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
from wef_backend.features.ingestion.infrastructure.media_filesystem import (
    LocalMediaStorage,
    MediaDerivativeError,
)
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaPersistenceError,
    SQLAlchemyMediaRepository,
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
    "CompleteImportLeaseHeldError",
    "FixtureGeocoder",
    "HTTPXJSONTransport",
    "HostedGeocoder",
    "ImportVerification",
    "LocalMediaStorage",
    "LocationWorkItem",
    "MediaDerivativeError",
    "MediaPersistenceError",
    "ProviderPolicy",
    "ReportPaths",
    "ReportWriteError",
    "SQLAlchemyCompleteImportRepository",
    "SQLAlchemyGeocodeStore",
    "SQLAlchemyMediaRepository",
    "SourceAnchor",
    "StaleCompleteImportLeaseError",
    "StaleGeocodeClaimError",
    "TelegramDesktopExportAdapter",
    "TelegramExportScan",
    "audit_evidence_document",
    "report_document",
]
