"""Finite scalar-family calibration; no claim of production model accuracy."""

from decimal import Decimal

import pytest

from wef_backend.features.admin.application.recovery_validation import (
    CALIBRATED_FIELDS,
    evidence_supports_field,
    listing_creation_supported,
    money_currency_matches,
)


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize("name", sorted(CALIBRATED_FIELDS))
def test_calibrated_scalar_positive_and_negative_cases(name: str, index: int) -> None:
    value: str | int | Decimal
    amount = 100000 + 375 * index
    if name == "currency":
        source, value = f"Price: {amount} PLN", "PLN"
    elif name == "floor_label":
        source, value = f"Piętro {index + 1}", str(index + 1)
    elif name == "market_type":
        label = ["Market", "Rynek"][index % 2]
        word = ["primary", "secondary"][index % 2]
        source, value = f"{label}: {word}", word
    elif name.startswith("rooms"):
        source, value = f"Rooms: {index + 1}", index + 1
    elif name.startswith("area"):
        source, value = f"Area: {37 + index}.50 m²", Decimal(f"{37 + index}.50")
    else:
        label = {"apartment": "Price", "parking": "Parking", "storage": "Storage"}[
            name.split("_", maxsplit=1)[0]
        ]
        source, value = f"{label}: {amount} PLN", Decimal(amount)
    assert evidence_supports_field(source, source, name, value)
    wrong = "EUR" if name == "currency" else ("invented" if isinstance(value, str) else value + 1)
    assert not evidence_supports_field(source, source, name, wrong)
    assert not evidence_supports_field(source + "\n" + source, source, name, value)
    assert not evidence_supports_field(source, "invented evidence", name, value)


@pytest.mark.parametrize(
    "source",
    [
        "Price: 780000 PLN / 190000 EUR",
        "Price: 780000 PLN/m²",
        "Price: -780000 PLN",
        "Parking: 780000 PLN",
        "Price: 780000 PLN + 50000 PLN",
        "Price: 780000-900000 PLN",
        "Price: 780000 PLN\nPrice: 900000 PLN",
        "Price:\n780000 PLN",
        "Price: included 780000 PLN",
        "Price: 780000 PLN or negotiable",
    ],
)
def test_ambiguous_price_semantics_never_apply(source: str) -> None:
    assert not evidence_supports_field(
        source, source.splitlines()[0], "apartment_price_min", 780000
    )


def test_currency_cannot_change_when_filling_a_price() -> None:
    source = "Parking: 39000 EUR"
    assert money_currency_matches(source, source, "parking_price_min", "EUR")
    assert not money_currency_matches(source, source, "parking_price_min", "PLN")
    assert not money_currency_matches(source, source, "parking_price_min", None)


def test_uncalibrated_fields_remain_observation_only() -> None:
    assert not evidence_supports_field(
        "Delivery: tomorrow", "Delivery: tomorrow", "delivery_label", "tomorrow"
    )
    assert not evidence_supports_field(
        "Storage: included", "Storage: included", "storage_included_in_price", proposed=True
    )


@pytest.mark.parametrize("index", range(10))
def test_complete_creation_family_requires_literal_location_and_all_fields(index: int) -> None:
    location = f"Warszawa, Testowa {index + 1}"
    price = 780000 + index
    source = f"Продажа: квартира\nLocation: {location}\nPrice: {price} PLN"
    fields: tuple[dict[str, object], ...] = (
        {"field_name": "location", "proposed_value": location, "evidence_fragment": location},
        {
            "field_name": "apartment_price_min",
            "proposed_value": price,
            "evidence_fragment": f"{price} PLN",
        },
        {"field_name": "currency", "proposed_value": "PLN", "evidence_fragment": "PLN"},
    )
    assert listing_creation_supported(source, fields)
    wrong = ({**fields[0], "proposed_value": "Warszawa, Invented 99"}, *fields[1:])
    assert not listing_creation_supported(source, wrong)
    assert not listing_creation_supported(source, fields[1:])
    assert not listing_creation_supported(
        source, (*fields, {"field_name": "district", "proposed_value": "invented"})
    )
