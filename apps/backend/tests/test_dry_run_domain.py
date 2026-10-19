"""Reject inconsistent dry-run evidence before it can become an operator report."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TypedDict

import pytest

from wef_backend.features.ingestion.domain import (
    CountBucket,
    DryRunCounts,
    DryRunErrorCode,
    DryRunReport,
    DryRunSource,
    DryRunTerminalStatus,
    StageTiming,
)


class _SourceChanges(TypedDict, total=False):
    platform: str
    channel_id: str
    channel_type: str
    file_size: int


class _VersionChanges(TypedDict, total=False):
    report_version: str
    parser_version: str
    grouping_version: str


class _AuditChanges(TypedDict, total=False):
    source_classifications: tuple[CountBucket, ...]
    candidate_score_buckets: tuple[CountBucket, ...]
    candidate_score_combinations: tuple[CountBucket, ...]
    candidate_boundaries: tuple[CountBucket, ...]


@pytest.fixture
def report() -> DryRunReport:
    """Return a reconciled report for one invented source message."""
    now = datetime(2030, 1, 1, tzinfo=UTC)
    return DryRunReport(
        report_version="report-v1",
        parser_version="parser-v1",
        grouping_version="grouping-v1",
        terminal_status=DryRunTerminalStatus.SUCCEEDED,
        error_code=None,
        source=DryRunSource("telegram", "synthetic", "public_channel", 1, "a" * 64, now, now),
        counts=DryRunCounts(1, 1, 1, 0, 0, 0, 0),
        source_classifications=(CountBucket("text", 1),),
        candidate_reasons=(),
        candidate_score_buckets=(CountBucket("above_threshold", 1),),
        candidate_score_combinations=(CountBucket("synthetic_signal", 1),),
        candidate_boundaries=(CountBucket("candidate_above_threshold", 1),),
        content_types=(),
        extracted_fields=(),
        warning_codes=(),
        warning_splits=(),
        media_rules=(),
        unassociated_media_reasons=(),
        timings=(),
    )


@pytest.mark.parametrize(("name", "count"), [("", 0), ("synthetic", -1)])
def test_count_buckets_reject_missing_names_and_negative_totals(name: str, count: int) -> None:
    with pytest.raises(ValueError, match="name and non-negative count"):
        CountBucket(name, count)


@pytest.mark.parametrize(("stage", "duration"), [("", 0), ("parse", -1)])
def test_timings_reject_missing_stages_and_negative_durations(stage: str, duration: int) -> None:
    with pytest.raises(ValueError, match="name and non-negative duration"):
        StageTiming(stage, duration)


@pytest.mark.parametrize(
    "changes",
    [{"platform": ""}, {"channel_id": ""}, {"channel_type": ""}, {"file_size": -1}],
)
def test_source_requires_complete_identity(report: DryRunReport, changes: _SourceChanges) -> None:
    assert report.source is not None
    with pytest.raises(ValueError, match="source identity must be complete"):
        replace(report.source, **changes)


@pytest.mark.parametrize("checksum", ["short", "A" * 64, "a" * 63 + "g"])
def test_source_rejects_invalid_checksums(report: DryRunReport, checksum: str) -> None:
    assert report.source is not None
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        replace(report.source, checksum=checksum)


def test_source_rejects_reversed_publication_dates(report: DryRunReport) -> None:
    assert report.source is not None
    assert report.source.published_from is not None
    with pytest.raises(ValueError, match="date range must be ordered"):
        replace(report.source, published_to=report.source.published_from - timedelta(seconds=1))


@pytest.mark.parametrize(
    "field",
    [
        "records_total",
        "messages_evaluated",
        "candidates",
        "non_candidates",
        "media_total",
        "media_associated",
        "media_unassociated",
    ],
)
def test_counts_reject_negative_values(report: DryRunReport, field: str) -> None:
    with pytest.raises(ValueError, match="counts must not be negative"):
        replace(report.counts, **{field: -1})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"non_candidates": 1}, "candidate counts must reconcile"),
        ({"media_unassociated": 1}, "media counts must reconcile"),
        ({"records_total": 0}, "evaluated messages cannot exceed"),
    ],
)
def test_counts_reject_unreconciled_stages(
    report: DryRunReport, changes: dict[str, int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(report.counts, **changes)


@pytest.mark.parametrize(
    "changes", [{"report_version": ""}, {"parser_version": ""}, {"grouping_version": ""}]
)
def test_report_requires_versions(report: DryRunReport, changes: _VersionChanges) -> None:
    with pytest.raises(ValueError, match="requires explicit versions"):
        replace(report, **changes)


def test_complete_report_requires_a_source_and_checksum(report: DryRunReport) -> None:
    assert report.source is not None
    for source in (None, replace(report.source, checksum=None)):
        with pytest.raises(ValueError, match="require a source checksum"):
            replace(report, source=source)


def test_completion_and_error_codes_cannot_disagree(report: DryRunReport) -> None:
    with pytest.raises(ValueError, match="only incomplete dry-run reports require an error code"):
        replace(report, error_code=DryRunErrorCode.SOURCE_IO)
    with pytest.raises(ValueError, match="only incomplete dry-run reports require an error code"):
        replace(report, terminal_status=DryRunTerminalStatus.FAILED)


def test_empty_and_nonempty_terminal_states_cannot_be_swapped(report: DryRunReport) -> None:
    with pytest.raises(ValueError, match="successful non-empty report requires source records"):
        replace(report, counts=DryRunCounts(0, 0, 0, 0, 0, 0, 0))
    with pytest.raises(ValueError, match="empty report cannot contain source records"):
        replace(report, terminal_status=DryRunTerminalStatus.EMPTY)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_classifications": ()}, "source classification buckets must reconcile"),
        ({"candidate_score_buckets": ()}, "candidate score buckets must reconcile"),
        ({"candidate_score_combinations": ()}, "candidate combinations must reconcile"),
        ({"candidate_boundaries": ()}, "candidate boundaries must reconcile"),
    ],
)
def test_report_rejects_missing_audit_totals(
    report: DryRunReport, changes: _AuditChanges, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(report, **changes)


def test_report_reconciles_warning_splits(report: DryRunReport) -> None:
    with pytest.raises(ValueError, match="warning splits must reconcile"):
        replace(report, warning_codes=(CountBucket("synthetic_warning", 1),))
