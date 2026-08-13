"""Immutable, non-sensitive dry-run report values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

_CHECKSUM_LENGTH = 64


class DryRunTerminalStatus(StrEnum):
    """Unambiguous terminal state for every operator run."""

    SUCCEEDED = "succeeded"
    EMPTY = "empty"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DryRunErrorCode(StrEnum):
    """Stable failures that never include source values or paths."""

    SOURCE_IO = "source_io"
    INVALID_JSON = "invalid_json"
    TRUNCATED_JSON = "truncated_json"
    INVALID_TOP_LEVEL = "invalid_top_level"
    CHANNEL_MISMATCH = "channel_mismatch"
    SCAN_ALREADY_STARTED = "scan_already_started"
    COUNT_RECONCILIATION = "count_reconciliation"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, order=True)
class CountBucket:
    """Named aggregate with no representative source sample."""

    name: str
    count: int

    def __post_init__(self) -> None:
        """Reject empty bucket names and negative counts."""
        if not self.name or self.count < 0:
            message = "count bucket requires a name and non-negative count"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class StageTiming:
    """One non-negative elapsed stage duration."""

    stage: str
    duration_ms: int

    def __post_init__(self) -> None:
        """Reject empty stage names and negative durations."""
        if not self.stage or self.duration_ms < 0:
            message = "stage timing requires a name and non-negative duration"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class DryRunSource:
    """Safe source identity and terminal checksum metadata."""

    platform: str
    channel_id: str
    channel_type: str
    file_size: int
    checksum: str | None
    published_from: datetime | None
    published_to: datetime | None

    def __post_init__(self) -> None:
        """Validate source identity, size, checksum, and date order."""
        if not self.platform or not self.channel_id or not self.channel_type or self.file_size < 0:
            message = "dry-run source identity must be complete"
            raise ValueError(message)
        if self.checksum is not None and (
            len(self.checksum) != _CHECKSUM_LENGTH
            or any(character not in "0123456789abcdef" for character in self.checksum)
        ):
            message = "dry-run source checksum must be a lowercase SHA-256 digest"
            raise ValueError(message)
        if (
            self.published_from is not None
            and self.published_to is not None
            and self.published_to < self.published_from
        ):
            message = "dry-run source date range must be ordered"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class DryRunCounts:
    """Reconciled primary and downstream stage totals."""

    records_total: int
    messages_evaluated: int
    candidates: int
    non_candidates: int
    media_total: int
    media_associated: int
    media_unassociated: int

    def __post_init__(self) -> None:
        """Reconcile candidate and media stages and reject negatives."""
        values = (
            self.records_total,
            self.messages_evaluated,
            self.candidates,
            self.non_candidates,
            self.media_total,
            self.media_associated,
            self.media_unassociated,
        )
        if any(value < 0 for value in values):
            message = "dry-run counts must not be negative"
            raise ValueError(message)
        if self.candidates + self.non_candidates != self.messages_evaluated:
            message = "candidate counts must reconcile to evaluated messages"
            raise ValueError(message)
        if self.media_associated + self.media_unassociated != self.media_total:
            message = "media counts must reconcile to media total"
            raise ValueError(message)
        if self.messages_evaluated > self.records_total:
            message = "evaluated messages cannot exceed source records"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class DryRunReport:
    """Complete aggregate report with no source text, contacts, payload, or paths."""

    report_version: str
    parser_version: str
    grouping_version: str
    terminal_status: DryRunTerminalStatus
    error_code: DryRunErrorCode | None
    source: DryRunSource | None
    counts: DryRunCounts
    source_classifications: tuple[CountBucket, ...]
    candidate_reasons: tuple[CountBucket, ...]
    content_types: tuple[CountBucket, ...]
    extracted_fields: tuple[CountBucket, ...]
    warning_codes: tuple[CountBucket, ...]
    media_rules: tuple[CountBucket, ...]
    unassociated_media_reasons: tuple[CountBucket, ...]
    timings: tuple[StageTiming, ...]

    def __post_init__(self) -> None:
        """Keep terminal state, source summary, and primary counts coherent."""
        if not self.report_version or not self.parser_version or not self.grouping_version:
            message = "dry-run report requires explicit versions"
            raise ValueError(message)
        complete = self.terminal_status in {
            DryRunTerminalStatus.SUCCEEDED,
            DryRunTerminalStatus.EMPTY,
        }
        if complete and (self.source is None or self.source.checksum is None):
            message = "complete dry-run reports require a source checksum"
            raise ValueError(message)
        if complete == (self.error_code is not None):
            message = "only incomplete dry-run reports require an error code"
            raise ValueError(message)
        if (
            self.terminal_status is DryRunTerminalStatus.SUCCEEDED
            and self.counts.records_total == 0
        ):
            message = "successful non-empty report requires source records"
            raise ValueError(message)
        if self.terminal_status is DryRunTerminalStatus.EMPTY and self.counts.records_total != 0:
            message = "empty report cannot contain source records"
            raise ValueError(message)
        if sum(bucket.count for bucket in self.source_classifications) != self.counts.records_total:
            message = "source classification buckets must reconcile to input"
            raise ValueError(message)

    @property
    def is_complete(self) -> bool:
        """Return whether source exhaustion and checksum validation succeeded."""
        return self.terminal_status in {
            DryRunTerminalStatus.SUCCEEDED,
            DryRunTerminalStatus.EMPTY,
        }
