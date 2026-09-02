"""Framework-independent listing extraction values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from wef_backend.features.catalog.domain import ContentType, MarketType, PropertyType

_CURRENCY_CODE_LENGTH = 3


class Confidence(StrEnum):
    """Coarse deterministic confidence used by parser rules."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CandidateReason(StrEnum):
    """Stable evidence codes contributing to a candidate score."""

    DEVELOPMENT_HEADER = "development_header"
    PURCHASE_HEADER = "purchase_header"
    UNIT_MARKER = "unit_marker"
    LOCATION_MARKER = "location_marker"
    PRICE_MARKER = "price_marker"
    AREA_MARKER = "area_marker"
    ROOM_MARKER = "room_marker"
    GOOGLE_MAPS_LINK = "google_maps_link"


class ExtractionWarningCode(StrEnum):
    """Stable review reasons emitted without inventing values."""

    CONFLICTING_CONTENT_TYPE = "conflicting_content_type"
    CONFLICTING_VALUES = "conflicting_values"
    INVALID_RANGE = "invalid_range"
    UNKNOWN_CURRENCY = "unknown_currency"


class ContactKind(StrEnum):
    """Internally preserved contact value categories."""

    PHONE = "phone"
    TELEGRAM = "telegram"


class LinkKind(StrEnum):
    """Typed links recognized without resolving them."""

    GOOGLE_MAPS = "google_maps"


@dataclass(frozen=True, slots=True, order=True)
class SourceSpan:
    """Half-open offsets into the unchanged flattened source text."""

    start: int
    end: int

    def __post_init__(self) -> None:
        """Reject empty, reversed, or negative spans."""
        if self.start < 0 or self.end <= self.start:
            message = "source span must be a non-empty half-open range"
            raise ValueError(message)

    def extract(self, text: str) -> str:
        """Return the exact source substring represented by the span."""
        if self.end > len(text):
            message = "source span exceeds source text"
            raise ValueError(message)
        return text[self.start : self.end]


@dataclass(frozen=True, slots=True)
class RuleProvenance:
    """Rule identity, confidence, and exact source evidence."""

    rule_id: str
    rule_version: str
    confidence: Confidence
    spans: tuple[SourceSpan, ...]

    def __post_init__(self) -> None:
        """Require stable rule identity and at least one source span."""
        if not self.rule_id or not self.rule_version or not self.spans:
            message = "rule provenance requires identity, version, and source spans"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    """One weighted reason contributing to candidate detection."""

    reason: CandidateReason
    weight: int
    provenance: RuleProvenance

    def __post_init__(self) -> None:
        """Reject non-positive score contributions."""
        if self.weight <= 0:
            message = "candidate signal weight must be positive"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    """Complete, reviewable candidate decision for one raw message."""

    parser_version: str
    is_candidate: bool
    score: int
    threshold: int
    content_type: ContentType | None
    signals: tuple[CandidateSignal, ...]

    def __post_init__(self) -> None:
        """Reconcile score, threshold, decision, and content type."""
        if not self.parser_version or self.threshold <= 0:
            message = "candidate decision requires a version and positive threshold"
            raise ValueError(message)
        if self.score != sum(signal.weight for signal in self.signals):
            message = "candidate score must equal the signal weights"
            raise ValueError(message)
        if self.is_candidate != (self.score >= self.threshold):
            message = "candidate decision must agree with its score and threshold"
            raise ValueError(message)
        if not self.is_candidate and self.content_type is not None:
            message = "non-candidates cannot carry a content type"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class DecimalRange:
    """Inclusive decimal range preserving scalar and ranged source values."""

    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        """Reject negative or reversed decimal ranges."""
        if self.lower < 0 or self.upper < self.lower:
            message = "decimal range must be non-negative and ordered"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class IntegerRange:
    """Inclusive positive integer range."""

    lower: int
    upper: int

    def __post_init__(self) -> None:
        """Reject zero, negative, or reversed integer ranges."""
        if self.lower <= 0 or self.upper < self.lower:
            message = "integer range must be positive and ordered"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MoneyRange:
    """Money in source major units with explicit or unknown currency."""

    amount: DecimalRange
    currency: str | None

    def __post_init__(self) -> None:
        """Require normalized ISO-like currency when it is known."""
        if self.currency is not None and (
            len(self.currency) != _CURRENCY_CODE_LENGTH
            or not self.currency.isascii()
            or not self.currency.isupper()
        ):
            message = "currency must be an uppercase three-letter code"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExtractedValue[T]:
    """Typed field value accompanied by exact parser provenance."""

    value: T
    provenance: RuleProvenance


@dataclass(frozen=True, slots=True)
class ContactSpan:
    """Plain source contact retained only at the internal boundary."""

    kind: ContactKind
    value: str
    span: SourceSpan
    provenance: RuleProvenance

    def __post_init__(self) -> None:
        """Reject empty contact values and mismatched provenance."""
        if not self.value or self.span not in self.provenance.spans:
            message = "contact requires a value and matching source provenance"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class LinkSpan:
    """Typed source URL with no network-resolution behavior."""

    kind: LinkKind
    url: str
    span: SourceSpan
    provenance: RuleProvenance

    def __post_init__(self) -> None:
        """Reject non-HTTP links and mismatched provenance."""
        if (
            not self.url.startswith(("https://", "http://"))
            or self.span not in self.provenance.spans
        ):
            message = "link requires an HTTP URL and matching source provenance"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExtractionWarning:
    """Field-level warning that keeps uncertain evidence reviewable."""

    code: ExtractionWarningCode
    field_name: str
    spans: tuple[SourceSpan, ...] = ()

    def __post_init__(self) -> None:
        """Require a stable field identifier."""
        if not self.field_name:
            message = "extraction warning requires a field name"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ListingCandidate:
    """Complete typed listing candidate derived from one source message."""

    source_message_id: int
    source_checksum: str
    parser_version: str
    content_type: ExtractedValue[ContentType] | None
    market_type: ExtractedValue[MarketType] | None
    property_type: ExtractedValue[PropertyType] | None
    location: ExtractedValue[str] | None
    district: ExtractedValue[str] | None
    development_name: ExtractedValue[str] | None
    apartment_price: ExtractedValue[MoneyRange] | None
    parking_price: ExtractedValue[MoneyRange] | None
    storage_price: ExtractedValue[MoneyRange] | None
    parking_included_in_price: ExtractedValue[bool] | None
    storage_included_in_price: ExtractedValue[bool] | None
    area_sqm: ExtractedValue[DecimalRange] | None
    rooms: ExtractedValue[IntegerRange] | None
    floor: ExtractedValue[str] | None
    delivery: ExtractedValue[str] | None
    map_links: tuple[LinkSpan, ...]
    contacts: tuple[ContactSpan, ...]

    def __post_init__(self) -> None:
        """Require a stable positive source identity and parser version."""
        if self.source_message_id <= 0 or not self.source_checksum or not self.parser_version:
            message = "listing candidate requires source identity and parser version"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Candidate decision plus optional typed listing and review warnings."""

    decision: CandidateDecision
    listing: ListingCandidate | None
    warnings: tuple[ExtractionWarning, ...] = ()

    def __post_init__(self) -> None:
        """Keep positive and negative result shapes disjoint."""
        if self.decision.is_candidate != (self.listing is not None):
            message = "only candidate decisions can carry a listing"
            raise ValueError(message)
