"""Historical source port and complete-scan lifecycle contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from types import TracebackType

    from wef_backend.features.ingestion.domain import RecordResult, ScanCounts, SourceMetadata

_CHECKSUM_LENGTH = 64


class SourceErrorCode(StrEnum):
    """Stable redacted failures for an entire source document."""

    SOURCE_IO = "source_io"
    INVALID_JSON = "invalid_json"
    TRUNCATED_JSON = "truncated_json"
    INVALID_TOP_LEVEL = "invalid_top_level"
    CHANNEL_MISMATCH = "channel_mismatch"
    SCAN_ALREADY_STARTED = "scan_already_started"


class SourceScanError(RuntimeError):
    """Fail a source scan without leaking a path or source payload."""

    def __init__(self, code: SourceErrorCode) -> None:
        """Store a stable code and safe generic message."""
        self.code = code
        super().__init__(f"historical source scan failed: {code.value}")


class IncompleteScanError(RuntimeError):
    """Raised when a partial consumer requests a complete summary."""


@dataclass(frozen=True, slots=True)
class ChannelExpectation:
    """Explicit channel identity required before source conversion."""

    channel_id: str
    channel_type: str
    channel_name: str | None = None

    def __post_init__(self) -> None:
        """Reject empty expected identity fields."""
        if not self.channel_id or not self.channel_type:
            message = "expected channel id and type must not be empty"
            raise ValueError(message)
        if self.channel_name == "":
            message = "expected channel name must be non-empty when supplied"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ScanSummary:
    """Terminal aggregate available only after complete source exhaustion."""

    source: SourceMetadata
    source_checksum: str
    counts: ScanCounts

    def __post_init__(self) -> None:
        """Validate terminal checksum shape."""
        if len(self.source_checksum) != _CHECKSUM_LENGTH or any(
            character not in "0123456789abcdef" for character in self.source_checksum
        ):
            message = "source checksum must be a lowercase SHA-256 digest"
            raise ValueError(message)


class HistoricalSourceScan(Protocol):
    """One-use, closeable iterator over reconciled source records."""

    def __iter__(self) -> Self:
        """Return this one-use scan."""
        ...

    def __next__(self) -> RecordResult:
        """Yield the next reconciled source record."""
        ...

    def __enter__(self) -> Self:
        """Enter a source scan context."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close source resources."""
        ...

    @property
    def is_complete(self) -> bool:
        """Report whether the source reached validated exhaustion."""
        ...

    @property
    def source(self) -> SourceMetadata:
        """Return safe preflight metadata without claiming complete exhaustion."""
        ...

    @property
    def summary(self) -> ScanSummary:
        """Return terminal aggregates or reject partial access."""
        ...

    def close(self) -> None:
        """Close source resources without claiming completion."""
        ...


class HistoricalSourcePort(Protocol):
    """Port implemented by bounded historical source adapters."""

    def open_scan(self) -> HistoricalSourceScan:
        """Validate the source and return a one-use record scan."""
        ...
