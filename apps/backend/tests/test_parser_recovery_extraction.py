"""Evidence-preserving money and inclusion regression tests for E25-T2."""

from decimal import Decimal

import pytest

from tests.parser_benchmark import evaluate
from tests.test_listing_extraction import _candidate
from wef_backend.features.ingestion.domain import DecimalRange, IntegerRange


@pytest.mark.parametrize(
    "value",
    [
        "780 000 PLN / 182 000 EUR",
        "182 000 EUR / 780 000 PLN",
        "PLN 780 000 or EUR 182 000",
        "780 000 PLN (182 000 EUR)",
        "780 000 PLN = 182 000 EUR",
    ],
)
def test_alternate_quote_uses_supplied_pln_without_conversion(value: str) -> None:
    result = _candidate(f"For sale: Apartment\nPrice: {value}")
    assert result.listing is not None
    price = result.listing.apartment_price
    assert price is not None
    assert price.value.currency == "PLN"
    assert price.value.amount == DecimalRange(Decimal(780000), Decimal(780000))
    assert not result.warnings
    assert value in price.provenance.spans[0].extract(f"For sale: Apartment\nPrice: {value}")


@pytest.mark.parametrize(
    "value",
    [
        "780 000 PLN - 182 000 EUR",
        "780 000 PLN / 790 000 PLN",
        "182 000 EUR / 200 000 USD",
        "780 000 PLN EUR",
        "780 000 PLN + 20 000 PLN",
        "780 000 PLN 182 000 EUR",
        "-780 000 PLN",
        "780 00 PLN",
        "15 000 PLN/m²",
        "780 000 PLN / 180 000-190 000 EUR",
    ],
)
def test_ambiguous_money_never_becomes_an_applied_range(value: str) -> None:
    result = _candidate(f"For sale: Apartment\nPrice: {value}")
    assert result.listing is not None
    assert result.listing.apartment_price is None
    assert any(w.field_name == "apartment_price" for w in result.warnings)


def test_same_currency_range_accepts_repeated_units() -> None:
    result = _candidate("For sale: Apartment\nPrice: 600 000 PLN - 700 000 PLN")
    assert result.listing is not None
    assert result.listing.apartment_price is not None
    assert result.listing.apartment_price.value.amount == DecimalRange(
        Decimal(600000), Decimal(700000)
    )
    assert not result.warnings


def test_appended_addon_and_labeled_addon_do_not_replace_apartment_price() -> None:
    result = _candidate("For sale: Apartment\nPrice: 1 399 000 PLN + parking: 39 000 PLN")
    assert result.listing is not None
    assert result.listing.apartment_price is not None
    assert result.listing.parking_price is not None
    assert result.listing.apartment_price.value.amount.lower == 1399000
    assert result.listing.parking_price.value.amount.lower == 39000
    only_addon = _candidate("For sale: Apartment\nParking price: 39 000 PLN")
    assert only_addon.listing is not None
    assert only_addon.listing.apartment_price is None
    assert only_addon.listing.parking_price is not None


@pytest.mark.parametrize("value", ["included, 20 000 PLN", "not included", "nie wliczone"])
def test_contradictory_or_negated_inclusion_is_not_true(value: str) -> None:
    result = _candidate(f"For sale: Apartment\nStorage: {value}")
    assert result.listing is not None
    assert result.listing.storage_included_in_price is None
    assert result.listing.storage_price is None
    assert result.warnings


def test_matching_inline_room_tag_has_no_spurious_warning() -> None:
    result = _candidate("For sale: Apartment\nRooms: 2 #2_rooms")
    assert result.listing is not None
    assert result.listing.rooms is not None
    assert result.listing.rooms.value == IntegerRange(2, 2)
    assert not result.warnings
    conflict = _candidate("For sale: Apartment\nRooms: 2 #3_rooms")
    assert conflict.listing is not None
    assert conflict.listing.rooms is None
    assert conflict.warnings


def test_empty_label_does_not_borrow_next_line() -> None:
    result = _candidate("For sale: Apartment\nPrice:\nArea: 37.50 m²")
    assert result.listing is not None
    assert result.listing.apartment_price is None


def test_invalid_additional_price_keeps_conflicting_field_unapplied() -> None:
    result = _candidate("For sale: Apartment\nPrice: 700 000 PLN\nPrice: 800 000 PLN - 180 000 EUR")
    assert result.listing is not None
    assert result.listing.apartment_price is None
    assert result.warnings


def test_accepted_parser_fixes_all_labeled_benchmark_fields() -> None:
    report, failures = evaluate()
    assert not failures
    assert report["candidate"]["fp"] == 0
    assert report["candidate"]["fn"] == 0
