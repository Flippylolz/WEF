"""Unit tests for parse issue serialization and ledger rules."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from tests.test_listing_extraction import _message
from tests.test_persistence_application import _raw
from wef_backend.features.ingestion.application.extraction import (
    CANDIDATE_THRESHOLD,
    PARSER_VERSION,
    extract_listing,
)
from wef_backend.features.ingestion.application.parse_issue_serialization import (
    boundary_band,
    build_parse_issue_insert,
    issue_outcome_for,
    signal_combination,
)
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain.parse_issue import ParseIssueOutcome

FIXTURE = Path(__file__).parent / "fixtures" / "telegram_export" / "sanitized-extraction-cases.json"


def test_boundary_band_matches_dry_run_buckets() -> None:
    assert boundary_band(score=5, threshold=5) == "candidate_at_threshold"
    assert boundary_band(score=6, threshold=5) == "candidate_above_threshold"
    assert boundary_band(score=4, threshold=5) == "non_candidate_one_below_threshold"
    assert boundary_band(score=2, threshold=5) == "non_candidate_below_boundary"


def test_build_parse_issue_insert_skips_clean_candidate() -> None:
    case = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]
    raw = _message(case["text"])
    extraction = extract_listing(raw)
    assert extraction.listing is not None
    issue = build_parse_issue_insert(
        extraction=extraction,
        raw=raw,
        message_outcome=MessageOutcome.CREATED,
        channel_id=uuid4(),
        source_message_id=uuid4(),
        source_message_revision_id=uuid4(),
        ingest_run_id=uuid4(),
        offer_id=uuid4(),
    )
    assert issue is None


def test_build_parse_issue_insert_records_parser_miss() -> None:
    raw = _raw(message_id=11, text="random service message", checksum="c" * 64)
    extraction = extract_listing(raw)
    issue = build_parse_issue_insert(
        extraction=extraction,
        raw=raw,
        message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE,
        channel_id=uuid4(),
        source_message_id=uuid4(),
        source_message_revision_id=uuid4(),
        ingest_run_id=uuid4(),
        offer_id=None,
    )
    assert issue is not None
    assert issue.issue_outcome is ParseIssueOutcome.PARSER_MISS
    assert issue.score < CANDIDATE_THRESHOLD
    assert issue.parser_version == PARSER_VERSION
    assert issue.signal_combination == signal_combination(extraction.decision)
    assert issue_outcome_for(extraction) is ParseIssueOutcome.PARSER_MISS


def test_build_parse_issue_insert_allows_version_evaluation_on_unchanged_replay() -> None:
    raw = _raw(message_id=12, text="random service message", checksum="d" * 64)
    extraction = extract_listing(raw)
    assert (
        build_parse_issue_insert(
            extraction=extraction,
            raw=raw,
            message_outcome=MessageOutcome.UNCHANGED,
            channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=uuid4(),
            ingest_run_id=uuid4(),
            offer_id=None,
        )
        is not None
    )
