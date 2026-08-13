"""Ingestion source ports and lifecycle contracts."""

from wef_backend.features.ingestion.application.extraction import (
    CANDIDATE_THRESHOLD,
    PARSER_VERSION,
    detect_candidate,
    extract_listing,
)
from wef_backend.features.ingestion.application.source import (
    ChannelExpectation,
    HistoricalSourcePort,
    HistoricalSourceScan,
    IncompleteScanError,
    ScanSummary,
    SourceErrorCode,
    SourceScanError,
)

__all__ = [
    "CANDIDATE_THRESHOLD",
    "PARSER_VERSION",
    "ChannelExpectation",
    "HistoricalSourcePort",
    "HistoricalSourceScan",
    "IncompleteScanError",
    "ScanSummary",
    "SourceErrorCode",
    "SourceScanError",
    "detect_candidate",
    "extract_listing",
]
