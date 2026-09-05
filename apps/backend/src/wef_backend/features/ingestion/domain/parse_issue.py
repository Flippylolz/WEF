"""Durable parse-miss records for ingestion issue reporting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class ParseIssueOutcome(StrEnum):
    """Why one ingested message was logged for parser follow-up."""

    PARSER_MISS = "parser_miss"
    PARSER_INCOMPLETE = "parser_incomplete"


@dataclass(frozen=True, slots=True)
class SourceMessageParseIssue:
    """One redacted parse issue row ready for admin export."""

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
    message_outcome: str
    boundary_band: str
    signal_combination: str
    text_excerpt_redacted: str
    offer_id: UUID | None
    created_at: datetime
    classification: str = "unclassified"
    lifecycle_state: str = "open"
    recovery_eligible: bool = False
    policy_version: str | None = None
