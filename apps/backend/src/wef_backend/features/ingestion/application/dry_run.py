"""Streaming, read-only E2 dry-run orchestration."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.extraction import (
    PARSER_VERSION,
    extract_listing,
)
from wef_backend.features.ingestion.application.media_grouping import (
    GROUPING_VERSION,
    group_media,
)
from wef_backend.features.ingestion.application.source import SourceScanError
from wef_backend.features.ingestion.domain import (
    CountBucket,
    DryRunCounts,
    DryRunErrorCode,
    DryRunReport,
    DryRunSource,
    DryRunTerminalStatus,
    GroupingInput,
    StageTiming,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime

    from wef_backend.features.ingestion.application import (
        HistoricalSourcePort,
        HistoricalSourceScan,
    )
    from wef_backend.features.ingestion.domain import (
        ExtractionResult,
        RecordResult,
        SourceMetadata,
    )

REPORT_VERSION = "e2-report-v2"
_EXTRACTED_SCALAR_FIELDS = (
    "content_type",
    "market_type",
    "property_type",
    "location",
    "district",
    "development_name",
    "apartment_price",
    "parking_price",
    "storage_price",
    "parking_included_in_price",
    "storage_included_in_price",
    "area_sqm",
    "rooms",
    "floor",
    "delivery",
)


class _DryRunCancelledError(Exception):
    """Stop an active scan without claiming source completion."""


@dataclass(slots=True)
class _MutableRun:
    records_total: int = 0
    messages_evaluated: int = 0
    candidates: int = 0
    non_candidates: int = 0
    media_total: int = 0
    media_associated: int = 0
    media_unassociated: int = 0
    published_from: datetime | None = None
    published_to: datetime | None = None
    source_seconds: float = 0.0
    extraction_seconds: float = 0.0
    grouping_seconds: float = 0.0
    source_classifications: Counter[str] = field(default_factory=Counter)
    candidate_reasons: Counter[str] = field(default_factory=Counter)
    candidate_score_buckets: Counter[str] = field(default_factory=Counter)
    candidate_score_combinations: Counter[str] = field(default_factory=Counter)
    candidate_boundaries: Counter[str] = field(default_factory=Counter)
    content_types: Counter[str] = field(default_factory=Counter)
    extracted_fields: Counter[str] = field(default_factory=Counter)
    warning_codes: Counter[str] = field(default_factory=Counter)
    warning_splits: Counter[str] = field(default_factory=Counter)
    media_rules: Counter[str] = field(default_factory=Counter)
    unassociated_media_reasons: Counter[str] = field(default_factory=Counter)

    def add_record(self, record: RecordResult) -> None:
        self.records_total += 1
        self.source_classifications[record.classification.value] += 1
        if record.message is None:
            return
        self.messages_evaluated += 1
        published_at = record.message.published_at
        if self.published_from is None or published_at < self.published_from:
            self.published_from = published_at
        if self.published_to is None or published_at > self.published_to:
            self.published_to = published_at

    def add_extraction(self, result: ExtractionResult) -> None:
        self._add_candidate_evidence(result)
        if result.decision.is_candidate:
            self.candidates += 1
        else:
            self.non_candidates += 1
        for signal in result.decision.signals:
            self.candidate_reasons[signal.reason.value] += 1
        if result.listing is None:
            return
        if result.listing.content_type is not None:
            self.content_types[result.listing.content_type.value.value] += 1
        for field_name in _EXTRACTED_SCALAR_FIELDS:
            if getattr(result.listing, field_name) is not None:
                self.extracted_fields[field_name] += 1
        self.extracted_fields["google_maps_link"] += len(result.listing.map_links)
        self.extracted_fields["contact"] += len(result.listing.contacts)
        for warning in result.warnings:
            self.warning_codes[warning.code.value] += 1
            self.warning_splits[f"{warning.code.value}:{warning.field_name}"] += 1

    def _add_candidate_evidence(self, result: ExtractionResult) -> None:
        decision = result.decision
        self.candidate_score_buckets[f"score_{decision.score}"] += 1
        combination = "+".join(sorted(signal.reason.value for signal in decision.signals))
        self.candidate_score_combinations[combination or "none"] += 1
        if decision.score == decision.threshold:
            boundary = "candidate_at_threshold"
        elif decision.score > decision.threshold:
            boundary = "candidate_above_threshold"
        elif decision.score == decision.threshold - 1:
            boundary = "non_candidate_one_below_threshold"
        else:
            boundary = "non_candidate_below_boundary"
        self.candidate_boundaries[boundary] += 1


def run_dry_run(
    source: HistoricalSourcePort,
    *,
    grouping_version: str = GROUPING_VERSION,
    cancel_requested: Callable[[], bool] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> DryRunReport:
    """Run all E2 stages without canonical writes, media access, or network calls."""
    started = monotonic()
    mutable = _MutableRun()
    source_metadata: SourceMetadata | None = None
    source_checksum: str | None = None
    terminal_status = DryRunTerminalStatus.FAILED
    error_code: DryRunErrorCode | None = None
    cancel = cancel_requested or _never_cancel

    try:
        scan = source.open_scan()
        source_metadata = scan.source
        with scan:
            grouped = group_media(
                _grouping_inputs(
                    scan,
                    mutable,
                    cancel,
                    monotonic,
                ),
                grouping_version=grouping_version,
            )
            while True:
                before_source = mutable.source_seconds
                before_extraction = mutable.extraction_seconds
                stage_started = monotonic()
                try:
                    disposition = next(grouped)
                except StopIteration:
                    break
                stage_elapsed = monotonic() - stage_started
                upstream_elapsed = (
                    mutable.source_seconds
                    - before_source
                    + mutable.extraction_seconds
                    - before_extraction
                )
                mutable.grouping_seconds += max(0.0, stage_elapsed - upstream_elapsed)
                mutable.media_total += 1
                if disposition.association is not None:
                    mutable.media_associated += 1
                    mutable.media_rules[disposition.association.rule.value] += 1
                else:
                    mutable.media_unassociated += 1
                    reason = disposition.unassociated_reason
                    if reason is not None:
                        mutable.unassociated_media_reasons[reason.value] += 1
            summary = scan.summary
            source_checksum = summary.source_checksum
            if summary.counts.total != mutable.records_total:
                terminal_status = DryRunTerminalStatus.FAILED
                error_code = DryRunErrorCode.COUNT_RECONCILIATION
            elif mutable.records_total == 0:
                terminal_status = DryRunTerminalStatus.EMPTY
            else:
                terminal_status = DryRunTerminalStatus.SUCCEEDED
    except _DryRunCancelledError:
        terminal_status = DryRunTerminalStatus.CANCELLED
        error_code = DryRunErrorCode.CANCELLED
    except SourceScanError as error:
        terminal_status = (
            DryRunTerminalStatus.PARTIAL if mutable.records_total else DryRunTerminalStatus.FAILED
        )
        error_code = DryRunErrorCode(error.code.value)

    return _report(
        mutable,
        source_metadata,
        source_checksum,
        terminal_status,
        error_code,
        grouping_version,
        total_seconds=monotonic() - started,
    )


def _grouping_inputs(
    scan: HistoricalSourceScan,
    mutable: _MutableRun,
    cancel_requested: Callable[[], bool],
    monotonic: Callable[[], float],
) -> Iterator[GroupingInput]:
    while True:
        if cancel_requested():
            raise _DryRunCancelledError
        stage_started = monotonic()
        try:
            record = next(scan)
        except StopIteration:
            mutable.source_seconds += monotonic() - stage_started
            return
        mutable.source_seconds += monotonic() - stage_started
        mutable.add_record(record)
        if record.message is None:
            continue
        stage_started = monotonic()
        extraction = extract_listing(record.message)
        mutable.extraction_seconds += monotonic() - stage_started
        mutable.add_extraction(extraction)
        yield GroupingInput(message=record.message, candidate=extraction.decision)


def _report(  # noqa: PLR0913, PLR0917
    mutable: _MutableRun,
    source_metadata: SourceMetadata | None,
    source_checksum: str | None,
    terminal_status: DryRunTerminalStatus,
    error_code: DryRunErrorCode | None,
    grouping_version: str,
    *,
    total_seconds: float,
) -> DryRunReport:
    source = (
        DryRunSource(
            platform=source_metadata.identity.platform.value,
            channel_id=source_metadata.identity.channel_id,
            channel_type=source_metadata.identity.channel_type,
            file_size=source_metadata.file_size,
            checksum=source_checksum,
            published_from=mutable.published_from,
            published_to=mutable.published_to,
        )
        if source_metadata is not None
        else None
    )
    return DryRunReport(
        report_version=REPORT_VERSION,
        parser_version=PARSER_VERSION,
        grouping_version=grouping_version,
        terminal_status=terminal_status,
        error_code=error_code,
        source=source,
        counts=DryRunCounts(
            records_total=mutable.records_total,
            messages_evaluated=mutable.messages_evaluated,
            candidates=mutable.candidates,
            non_candidates=mutable.non_candidates,
            media_total=mutable.media_total,
            media_associated=mutable.media_associated,
            media_unassociated=mutable.media_unassociated,
        ),
        source_classifications=_buckets(mutable.source_classifications),
        candidate_reasons=_buckets(mutable.candidate_reasons),
        candidate_score_buckets=_buckets(mutable.candidate_score_buckets),
        candidate_score_combinations=_buckets(mutable.candidate_score_combinations),
        candidate_boundaries=_buckets(mutable.candidate_boundaries),
        content_types=_buckets(mutable.content_types),
        extracted_fields=_buckets(mutable.extracted_fields),
        warning_codes=_buckets(mutable.warning_codes),
        warning_splits=_buckets(mutable.warning_splits),
        media_rules=_buckets(mutable.media_rules),
        unassociated_media_reasons=_buckets(mutable.unassociated_media_reasons),
        timings=(
            _timing("source", mutable.source_seconds),
            _timing("extraction", mutable.extraction_seconds),
            _timing("media_grouping", mutable.grouping_seconds),
            _timing("total", total_seconds),
        ),
    )


def _buckets(counter: Counter[str]) -> tuple[CountBucket, ...]:
    return tuple(
        CountBucket(name=name, count=count) for name, count in sorted(counter.items()) if count
    )


def _timing(stage: str, seconds: float) -> StageTiming:
    return StageTiming(stage=stage, duration_ms=max(0, round(seconds * 1000)))


def _never_cancel() -> bool:
    return False
