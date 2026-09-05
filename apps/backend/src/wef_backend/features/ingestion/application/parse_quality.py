"""Evidence-based recovery eligibility independent of extractor warnings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.extraction import SourceSpan

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.extraction import ExtractionResult

POLICY_VERSION = "source-evidence-v1"


class ParseClassification(StrEnum):
    """Mutually exclusive aggregate evaluation outcomes, including uncertainty."""

    COMPLETE = "complete"
    EXPECTED_NON_OFFER = "expected_non_offer"
    SOURCE_ABSENT = "source_absent"
    EXTRACTION_MISS = "extraction_miss"
    INCOMPLETE = "incomplete"
    CONFLICTING = "conflicting"
    PROVIDER_FAILURE = "provider_failure"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    """A field observation with offsets, never a copy of source text."""

    field_name: str
    classification: ParseClassification
    spans: tuple[SourceSpan, ...] = ()


@dataclass(frozen=True, slots=True)
class ParseQuality:
    """One source/parser/policy evaluation used by the recovery selector."""

    classification: ParseClassification
    recovery_eligible: bool
    fields: tuple[FieldEvidence, ...]
    policy_version: str = POLICY_VERSION


# This detector recognizes evidence, not field values. Keep it independent of
# extraction success so a supported label can expose a silent extraction gap.
_LABELS = {
    "apartment_price": (
        r"(?:cena(?: mieszkania)?|(?:apartment )?price|цена(?: квартиры| апартамента)?|"
        r"стоимость(?: квартиры)?|ціна(?: квартири)?|вартість(?: квартири)?)"
    ),
    "area_sqm": r"(?:powierzchnia|area|площадь|площа)",
    "rooms": r"(?:pokoje?|rooms?|комнаты|комнат|кімнати|кімнат)",
    "parking_price": r"(?:parking(?: price)?|cena parkingu|паркинг|парковка|гараж)",
    "storage_price": r"(?:storage(?: price)?|komórka(?: lokatorska)?|кладовка|кладовая|комірка)",
    "market_type": r"(?:rynek|market|рынок|ринок)",
    "property_type": r"(?:typ nieruchomości|property type|тип недвижимости|тип нерухомості)",
}
_LABEL_PATTERNS = {
    name: re.compile(
        rf"(?im)^[ \t]*(?:[^\w\s]+[ \t]*)?{label}[ \t]*[:|\u2013—-]"
        r"[ \t]*(?P<value>\S[^\n\r]*)"
    )
    for name, label in _LABELS.items()
}
_INCLUDED = re.compile(
    r"(?i)\b(?:included|w cenie|wliczon\w*|включен\w*|"
    r"входит в (?:цену|стоимость)|входить \u0443 вартість)\b"
)
_ABSENT = re.compile(
    r"(?i)^\s*(?:n/?a|brak|nie podano|unknown|not (?:specified|provided)|"
    r"не указана?|не вказано|on request|do uzgodnienia|по запросу|[?—-])\s*[.!]?\s*$"
)
_NEGATIVE = re.compile(
    r"(?i)\b(?:service message|joined the channel|left the channel|photo album|"
    r"usługi|ремонт квартир|послуги|advertising services)\b"
)
_SALE = re.compile(
    r"(?i)\b(?:for sale|sprzedam|sprzedaż|продажа|прода[мю]|продаж|продається|купівля|покупка)\b"
)
_UNIT = re.compile(
    r"(?i)\b(?:mieszkanie|apartament|apartment|flat|house|квартир\w*|апартамент\w*|будинок|dom)\b"
)


def _field_evidence(text: str, extraction: ExtractionResult) -> tuple[FieldEvidence, ...]:
    fields: list[FieldEvidence] = []
    listing = extraction.listing
    warning_fields = {warning.field_name for warning in extraction.warnings}
    for original_name, pattern in _LABEL_PATTERNS.items():
        name = original_name
        matches = tuple(pattern.finditer(text))
        spans = tuple(SourceSpan(*match.span("value")) for match in matches)
        implicit_property = _UNIT.search(text) if name == "property_type" else None
        if not spans and implicit_property:
            spans = (SourceSpan(*implicit_property.span()),)
        value = getattr(listing, name, None) if listing else None
        included_name = name.replace("_price", "_included_in_price")
        if name in {"storage_price", "parking_price"} and any(
            _INCLUDED.search(match["value"]) for match in matches
        ):
            name = included_name
            value = getattr(listing, name, None) if listing else None
        if name in warning_fields or original_name in warning_fields:
            classification = ParseClassification.CONFLICTING
        elif value is not None:
            classification = ParseClassification.COMPLETE
            spans = value.provenance.spans
        elif matches and all(_ABSENT.fullmatch(match["value"]) for match in matches):
            classification = ParseClassification.SOURCE_ABSENT
        elif spans:
            classification = ParseClassification.EXTRACTION_MISS
        else:
            # No supported label is not proof that prose contains no field.
            classification = ParseClassification.UNCLASSIFIED
        fields.append(FieldEvidence(name, classification, spans))
    return tuple(fields)


def classify_parse(text: str, extraction: ExtractionResult) -> ParseQuality:  # noqa: PLR0911
    """Detect repairable evidence without interpreting absent labels as defects."""
    if not text.strip() or (_NEGATIVE.search(text) and not _SALE.search(text)):
        return ParseQuality(
            classification=ParseClassification.EXPECTED_NON_OFFER,
            recovery_eligible=False,
            fields=(),
        )
    fields = _field_evidence(text, extraction)
    evidenced = sum(bool(field.spans) for field in fields)
    listing_evidence = bool(_UNIT.search(text)) and (
        bool(_SALE.search(text)) or evidenced >= 2  # noqa: PLR2004 - two independent labels
    )
    if not extraction.decision.is_candidate and not listing_evidence:
        return ParseQuality(
            classification=ParseClassification.UNCLASSIFIED, recovery_eligible=False, fields=fields
        )
    if not listing_evidence:
        return ParseQuality(
            classification=ParseClassification.UNCLASSIFIED, recovery_eligible=False, fields=fields
        )
    if extraction.warnings:
        return ParseQuality(
            classification=ParseClassification.CONFLICTING, recovery_eligible=False, fields=fields
        )
    missing = any(field.classification is ParseClassification.EXTRACTION_MISS for field in fields)
    if missing:
        classification = (
            ParseClassification.INCOMPLETE
            if extraction.listing
            else ParseClassification.EXTRACTION_MISS
        )
        return ParseQuality(classification=classification, recovery_eligible=True, fields=fields)
    if any(field.classification is ParseClassification.SOURCE_ABSENT for field in fields):
        return ParseQuality(
            classification=ParseClassification.SOURCE_ABSENT, recovery_eligible=False, fields=fields
        )
    return ParseQuality(
        classification=ParseClassification.COMPLETE, recovery_eligible=False, fields=fields
    )
