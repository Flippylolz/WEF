"""Build redacted parse-issue ledger rows from extraction results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from wef_backend.features.ingestion.application.persistence import (
    MessageOutcome,
    build_source_text_excerpt,
)
from wef_backend.features.ingestion.domain.parse_issue import ParseIssueOutcome

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.extraction import (
        CandidateDecision,
        ExtractionResult,
        ExtractionWarning,
    )
    from wef_backend.features.ingestion.domain.model import RawMessage


def boundary_band(*, score: int, threshold: int) -> str:
    """Mirror dry-run candidate boundary buckets for one message."""
    if score == threshold:
        return "candidate_at_threshold"
    if score > threshold:
        return "candidate_above_threshold"
    if score == threshold - 1:
        return "non_candidate_one_below_threshold"
    return "non_candidate_below_boundary"


def signal_combination(decision: CandidateDecision) -> str:
    """Return a stable sorted reason combination for aggregate reporting."""
    return "+".join(sorted(signal.reason.value for signal in decision.signals)) or "none"


def serialize_signals(decision: CandidateDecision) -> tuple[dict[str, Any], ...]:
    """Return redacted signal metadata without span text."""
    serialized: list[dict[str, Any]] = []
    for signal in decision.signals:
        span = signal.provenance.spans[0] if signal.provenance.spans else None
        serialized.append(
            {
                "reason": signal.reason.value,
                "weight": signal.weight,
                "source_start": span.start if span is not None else None,
                "source_end": span.end if span is not None else None,
            },
        )
    return tuple(serialized)


def serialize_warnings(warnings: tuple[ExtractionWarning, ...]) -> tuple[dict[str, Any], ...]:
    """Return warning codes and field names without source text."""
    return tuple(
        {
            "code": warning.code.value,
            "field_name": warning.field_name,
            "source_start": warning.spans[0].start if warning.spans else None,
            "source_end": warning.spans[0].end if warning.spans else None,
        }
        for warning in warnings
    )


def issue_outcome_for(extraction: ExtractionResult) -> ParseIssueOutcome | None:
    """Classify one extraction into a ledger outcome or skip when parse succeeded."""
    if extraction.listing is None:
        return ParseIssueOutcome.PARSER_MISS
    if extraction.warnings:
        return ParseIssueOutcome.PARSER_INCOMPLETE
    return None


@dataclass(frozen=True, slots=True)
class ParseIssueInsert:
    """Values needed to persist one parse issue in the current transaction."""

    id: UUID
    source_channel_id: UUID
    source_message_id: UUID
    source_message_revision_id: UUID
    external_message_id: int
    ingest_run_id: UUID | None
    parser_version: str
    score: int
    threshold: int
    is_candidate: bool
    signals_json: tuple[dict[str, Any], ...]
    warnings_json: tuple[dict[str, Any], ...]
    issue_outcome: ParseIssueOutcome
    message_outcome: MessageOutcome
    boundary_band: str
    signal_combination: str
    text_excerpt_redacted: str
    offer_id: UUID | None


def build_parse_issue_insert(  # noqa: PLR0913
    *,
    extraction: ExtractionResult,
    raw: RawMessage,
    message_outcome: MessageOutcome,
    channel_id: UUID,
    source_message_id: UUID,
    source_message_revision_id: UUID,
    ingest_run_id: UUID | None,
    offer_id: UUID | None,
) -> ParseIssueInsert | None:
    """Return one ledger insert or None when the parse succeeded cleanly."""
    if message_outcome is MessageOutcome.UNCHANGED:
        return None
    issue_outcome = issue_outcome_for(extraction)
    if issue_outcome is None:
        return None
    decision = extraction.decision
    contacts = extraction.listing.contacts if extraction.listing is not None else ()
    return ParseIssueInsert(
        id=uuid4(),
        source_channel_id=channel_id,
        source_message_id=source_message_id,
        source_message_revision_id=source_message_revision_id,
        external_message_id=raw.external_message_id,
        ingest_run_id=ingest_run_id,
        parser_version=decision.parser_version,
        score=decision.score,
        threshold=decision.threshold,
        is_candidate=decision.is_candidate,
        signals_json=serialize_signals(decision),
        warnings_json=serialize_warnings(extraction.warnings),
        issue_outcome=issue_outcome,
        message_outcome=message_outcome,
        boundary_band=boundary_band(score=decision.score, threshold=decision.threshold),
        signal_combination=signal_combination(decision),
        text_excerpt_redacted=build_source_text_excerpt(raw.text, contacts),
        offer_id=offer_id,
    )
