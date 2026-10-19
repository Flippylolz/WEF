"""Synthetic parser boundaries and exact source-span normalization."""

import re
from decimal import Decimal

import pytest

from tests.test_inventory_extraction import ROWS
from tests.test_listing_extraction import _candidate
from wef_backend.features.catalog.domain import PropertyType
from wef_backend.features.ingestion.application.extraction import (
    _pin_line_value,
    _trimmed_span,
    source_text_contains_unmasked_contacts,
)
from wef_backend.features.ingestion.application.extraction_inventory import extract_inventory
from wef_backend.features.ingestion.application.extraction_numbers import (
    _currency,
    _decimal_range,
    _parsed_money,
    _room_tag_range,
)
from wef_backend.features.ingestion.domain import DecimalRange, ExtractionWarningCode, SourceSpan


@pytest.mark.parametrize("value", ["no amount", "1 / 2 / 3"])
def test_decimal_range_requires_one_or_two_numeric_values(value: str) -> None:
    """Missing numbers and an unbounded list do not become scalar evidence."""
    assert _decimal_range(value) is None


@pytest.mark.parametrize("value", ["100 PLN / unknown", "100 PLN / 200 EUR / 300 USD"])
def test_alternate_quotes_require_two_complete_amounts(value: str) -> None:
    """An absent or third quote cannot authorize choosing a convenient currency."""
    assert _parsed_money(value) is None


@pytest.mark.parametrize("value", ["#rooms", "#0_rooms", "#21_rooms"])
def test_room_tag_requires_a_bounded_positive_count(value: str) -> None:
    """Absent and impossible room counts remain unknown."""
    assert _room_tag_range(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [("unknown", None), ("€", "EUR"), ("$", "USD")],
)
def test_currency_symbols_and_unknown_markers(value: str, expected: str | None) -> None:
    """Symbols preserve denomination and unrecognized text invents none."""
    assert _currency(value) == expected


def test_inventory_rejects_zero_total_price() -> None:
    """A syntactically valid advertised row still needs a positive total."""
    assert extract_inventory(ROWS.replace("510 000", "0")) is None


@pytest.mark.parametrize(
    ("label", "expected"),
    [("semi", PropertyType.SEMI_DETACHED), ("unclassified", None)],
)
def test_property_type_label_preserves_known_or_unknown_evidence(
    label: str,
    expected: PropertyType | None,
) -> None:
    result = _candidate(f"For sale:\nProperty type: {label}")
    assert result.listing is not None
    actual = result.listing.property_type
    assert (actual.value if actual else None) == expected


def test_conflicting_labeled_districts_remain_unknown() -> None:
    result = _candidate("For sale: Apartment\nDistrict: Wola\nDistrict: Mokotów")
    assert result.listing is not None
    assert result.listing.district is None
    warning = next(warning for warning in result.warnings if warning.field_name == "district")
    assert warning.code is ExtractionWarningCode.CONFLICTING_VALUES
    assert tuple(
        span.extract("For sale: Apartment\nDistrict: Wola\nDistrict: Mokotów")
        for span in warning.spans
    ) == ("Wola", "Mokotów")


@pytest.mark.parametrize("label", ["Parking price", "Storage price"])
def test_addon_starting_price_cannot_imply_a_complete_quote(label: str) -> None:
    result = _candidate(f"For sale: Apartment\n{label}: from 20000 PLN")
    assert result.listing is not None
    assert result.listing.parking_price is None
    assert result.listing.storage_price is None
    assert any(warning.code is ExtractionWarningCode.INVALID_RANGE for warning in result.warnings)


def test_invalid_room_tag_does_not_create_a_room_range() -> None:
    result = _candidate("For sale: Apartment\n#21_rooms")
    assert result.listing is not None
    assert result.listing.rooms is None
    assert any(
        warning.field_name == "rooms" and warning.code is ExtractionWarningCode.INVALID_RANGE
        for warning in result.warnings
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("@synthetic_contact", True),
        ("+48 600 700 800", True),
        ("600700800", True),
        ("Price: 700000 PLN, area: 50 m²", False),
    ],
)
def test_contact_guard_distinguishes_contacts_from_ordinary_listing_numbers(
    source: str,
    *,
    expected: bool,
) -> None:
    assert source_text_contains_unmasked_contacts(source) is expected


def test_non_numeric_area_remains_unknown_without_invalid_range_warning() -> None:
    result = _candidate("For sale: Apartment\nArea: not supplied")
    assert result.listing is not None
    assert result.listing.area_sqm is None
    assert not any(warning.field_name == "area_sqm" for warning in result.warnings)


def test_span_trimming_keeps_offsets_of_only_the_value() -> None:
    text = "Field: \t 37.50 \t"
    match = re.search(r"Field:(?P<value>[^\n]+)", text)
    assert match is not None
    span = _trimmed_span(text, match)
    assert span == SourceSpan(text.index("37.50"), text.index("37.50") + 5)
    assert span.extract(text) == "37.50"
    assert _decimal_range(span.extract(text)) == DecimalRange(Decimal("37.50"), Decimal("37.50"))


def test_pin_value_trims_surrounding_whitespace_and_delimiters() -> None:
    text = "📍\u00a0ul. Syntetyczna, Warszawa \t,|\t"
    match = re.search(r"📍(?P<value>[^\n]+)", text)
    assert match is not None
    value, span = _pin_line_value(text, match)
    assert value == "ul. Syntetyczna, Warszawa"
    assert span.extract(text) == value
