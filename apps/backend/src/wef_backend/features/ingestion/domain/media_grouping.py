"""Framework-independent media association values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.extraction import CandidateDecision, Confidence
    from wef_backend.features.ingestion.domain.model import MediaDescriptor, RawMessage


class MediaAssociationRule(StrEnum):
    """Ordered evidence used to associate source-owned media."""

    SAME_MESSAGE = "same_message"
    EXPLICIT_GROUP = "explicit_group"
    REPLY = "reply"
    TIME_BURST = "time_burst"


class UnassociatedMediaReason(StrEnum):
    """Stable reasons for retaining media without a listing association."""

    SERVICE_BOUNDARY = "service_boundary"
    TEXT_BOUNDARY = "text_boundary"
    UNKNOWN_REPLY_TARGET = "unknown_reply_target"
    UNKNOWN_EXPLICIT_GROUP = "unknown_explicit_group"
    TIME_GAP = "time_gap"
    NO_ACTIVE_CANDIDATE = "no_active_candidate"


@dataclass(frozen=True, slots=True)
class GroupingInput:
    """One chronological message and its versioned candidate decision."""

    message: RawMessage
    candidate: CandidateDecision


@dataclass(frozen=True, slots=True)
class MediaReference:
    """A descriptor retaining its immutable source-message ownership."""

    source_message_id: int
    media_index: int
    descriptor: MediaDescriptor

    def __post_init__(self) -> None:
        """Reject invalid source positions."""
        if self.source_message_id <= 0 or self.media_index < 0:
            message = "media reference requires a positive source id and non-negative index"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MediaAssociation:
    """One explicit listing relationship for a source-owned descriptor."""

    reference: MediaReference
    listing_message_id: int
    rule: MediaAssociationRule
    confidence: Confidence
    grouping_version: str

    def __post_init__(self) -> None:
        """Require a positive listing identity and explicit rule version."""
        if self.listing_message_id <= 0 or not self.grouping_version:
            message = "media association requires listing identity and grouping version"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MediaDisposition:
    """Exactly-one associated or unassociated result for one descriptor."""

    reference: MediaReference
    association: MediaAssociation | None = None
    unassociated_reason: UnassociatedMediaReason | None = None

    def __post_init__(self) -> None:
        """Keep associated and unassociated result shapes disjoint."""
        if (self.association is None) == (self.unassociated_reason is None):
            message = "media disposition must be associated or unassociated"
            raise ValueError(message)
        if self.association is not None and self.association.reference != self.reference:
            message = "media association must retain the disposition source reference"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MediaGroup:
    """All descriptor associations currently owned by one listing."""

    listing_message_id: int
    associations: tuple[MediaAssociation, ...]

    def __post_init__(self) -> None:
        """Reject empty, mixed-owner, or duplicate-reference groups."""
        if self.listing_message_id <= 0 or not self.associations:
            message = "media group requires a listing identity and associations"
            raise ValueError(message)
        if any(
            association.listing_message_id != self.listing_message_id
            for association in self.associations
        ):
            message = "media group associations must share one listing owner"
            raise ValueError(message)
        references = tuple(association.reference for association in self.associations)
        if len(set(references)) != len(references):
            message = "media group cannot contain duplicate source references"
            raise ValueError(message)
