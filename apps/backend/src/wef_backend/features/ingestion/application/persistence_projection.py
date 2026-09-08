"""Contact-free storage projections, fingerprints and numeric conversion."""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.extraction import (
    Confidence,
    ContactSpan,
    DecimalRange,
    ExtractedValue,
    IntegerRange,
    ListingCandidate,
    MoneyRange,
)
from wef_backend.features.ingestion.domain.geocoding import normalize_location_display_name

if TYPE_CHECKING:
    from collections.abc import Sequence
EXCERPT_MAX_LENGTH = 280
MASK_FILLER = "•••"

_CONFIDENCE_SCORES = {
    Confidence.LOW: 0.5,
    Confidence.MEDIUM: 0.75,
    Confidence.HIGH: 0.95,
}


def confidence_score(confidence: Confidence) -> float:
    """Return the deterministic numeric score for one coarse confidence."""
    return _CONFIDENCE_SCORES[confidence]


def money_to_minor(amount: Decimal) -> int:
    """Convert source major units to integer minor units."""
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _field_value(value: object) -> object:
    """Serialize one extracted field value without source span text."""
    if isinstance(value, MoneyRange):
        return {
            "min_minor": money_to_minor(value.amount.lower),
            "max_minor": None if value.is_lower_bound else money_to_minor(value.amount.upper),
            "currency": value.currency,
        }
    if isinstance(value, DecimalRange):
        return {"min": str(value.lower), "max": str(value.upper)}
    if isinstance(value, IntegerRange):
        return {"min": value.lower, "max": value.upper}
    if hasattr(value, "value") and isinstance(value, StrEnum):
        return value.value
    return value


def build_extraction_json(listing: ListingCandidate) -> str:
    """Serialize contact-free field provenance anchored to one revision."""
    fields: dict[str, dict[str, object]] = {}
    extracted: tuple[tuple[str, ExtractedValue[object] | None], ...] = (
        ("content_type", listing.content_type),
        ("market_type", listing.market_type),
        ("property_type", listing.property_type),
        ("location", listing.location),
        ("district", listing.district),
        ("development_name", listing.development_name),
        ("apartment_price", listing.apartment_price),
        ("parking_price", listing.parking_price),
        ("storage_price", listing.storage_price),
        ("parking_included_in_price", listing.parking_included_in_price),
        ("storage_included_in_price", listing.storage_included_in_price),
        ("area_sqm", listing.area_sqm),
        ("rooms", listing.rooms),
        ("floor", listing.floor),
        ("delivery", listing.delivery),
    )
    for name, item in extracted:
        if item is None:
            continue
        first_span = item.provenance.spans[0]
        fields[name] = {
            "value": _field_value(item.value),
            "rule": f"{item.provenance.rule_id}@{item.provenance.rule_version}",
            "confidence": confidence_score(item.provenance.confidence),
            "source_start": first_span.start,
            "source_end": first_span.end,
        }
    return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contact_spans(contacts: Sequence[ContactSpan]) -> tuple[tuple[int, int], ...]:
    """Return sorted merged contact-covered half-open ranges."""
    ranges = sorted((c.span.start, c.span.end) for c in contacts)
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def build_source_text_excerpt(text: str, contacts: Sequence[ContactSpan]) -> str:
    """Return a contact-free excerpt that omits covered source text."""
    pieces: list[str] = []
    cursor = 0
    for start, end in _contact_spans(contacts):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    excerpt = "".join(pieces)
    return excerpt[:EXCERPT_MAX_LENGTH]


def build_source_text_public_masked(text: str, contacts: Sequence[ContactSpan]) -> str:
    """Return the public rendering with contact spans replaced by filler."""
    pieces: list[str] = []
    cursor = 0
    for start, end in _contact_spans(contacts):
        pieces.append(text[cursor:start])
        pieces.append(MASK_FILLER)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def canonical_fingerprint(listing: ListingCandidate) -> str:
    """Hash the canonical typed projection as a duplicate suggestion key."""

    def value_of(item: ExtractedValue[object] | None) -> object:
        if item is None:
            return None
        value = _field_value(item.value)
        if isinstance(value, str):
            return " ".join(value.casefold().split())
        return value

    payload = json.dumps(
        {
            "content_type": value_of(listing.content_type),
            "market_type": value_of(listing.market_type),
            "property_type": value_of(listing.property_type),
            "location": value_of(listing.location),
            "district": value_of(listing.district),
            "development_name": value_of(listing.development_name),
            "apartment_price": value_of(listing.apartment_price),
            "parking_price": value_of(listing.parking_price),
            "storage_price": value_of(listing.storage_price),
            "area_sqm": value_of(listing.area_sqm),
            "rooms": value_of(listing.rooms),
            "floor": value_of(listing.floor),
            "delivery": value_of(listing.delivery),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def normalized_location_key(location: str | None) -> str:
    """Return the deterministic replay key for one parsed location string."""
    candidate = " ".join((location or "").casefold().split())
    if not candidate:
        candidate = "unknown-location"
    return hashlib.sha256(candidate.encode()).hexdigest()


def normalize_location_text(
    location: str | None,
    *,
    district: str | None = None,
) -> str:
    """Return the canonical display name for one parsed location line."""
    return normalize_location_display_name(location, district=district)
