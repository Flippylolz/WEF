"""Invented current-channel syntax; no production descriptions or contacts."""

from dataclasses import replace
from decimal import Decimal

import pytest

from tests.test_listing_extraction import _message
from wef_backend.features.catalog.domain import ContentType, PropertyType
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parse_quality import (
    ParseClassification,
    classify_parse,
)
from wef_backend.features.ingestion.domain import IntegerRange

APARTMENT = """🏙 2-комнатная квартира | 38,6 м² | Warszawa
📐 38,6 м² | #2_комнаты_elestate
📍 Warszawa, ul. Przykładowa 12
💰 Условия:
• Квартира: 812 000 zł - возможен торг
• Паркоместо: 42 000 zł - обязательная покупка
• Кладовая 4 м²: 23 000 zł - обязательная покупка
"""
HOUSE = """🏡 Дом на продажу | 145 м² | 5 комнат | Miejscowość Testowa
📐 145 м² | 5 комнат
🏡 Дом-близнец
📍 Miejscowość Testowa, гмина Testowa
💰 Условия:
• Цена дома: 1 450 000 zł
• Цена за м²: 10 000 zł
"""


def test_current_apartment_creates_candidate_and_separate_evidenced_prices() -> None:
    result = extract_listing(_message(APARTMENT))
    listing = result.listing
    assert listing is not None
    assert listing.content_type is not None
    assert listing.content_type.value is ContentType.UNIT
    assert listing.property_type is not None
    assert listing.property_type.value is PropertyType.APARTMENT
    for name, amount, fragment in (
        ("apartment_price", 812000, "812 000 zł - возможен торг"),
        ("parking_price", 42000, "42 000 zł - обязательная покупка"),
        ("storage_price", 23000, "23 000 zł - обязательная покупка"),
    ):
        field = getattr(listing, name)
        assert field is not None
        assert field.value.amount.lower == field.value.amount.upper == amount
        assert field.value.currency == "PLN"
        assert field.provenance.spans[0].extract(APARTMENT) == fragment
    assert listing.area_sqm is not None
    assert listing.area_sqm.value.lower == Decimal("38.6")
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(2, 2)
    assert not result.warnings


def test_house_header_and_total_are_independent_of_warsaw_location_support() -> None:
    result = extract_listing(_message(HOUSE))
    listing = result.listing
    assert listing is not None
    assert listing.content_type is not None
    assert listing.content_type.value is ContentType.UNIT
    assert listing.property_type is not None
    assert listing.property_type.value is PropertyType.SEMI_DETACHED
    assert listing.apartment_price is not None
    assert listing.apartment_price.value.amount.lower == 1450000
    assert listing.area_sqm is not None
    assert listing.area_sqm.value.lower == 145
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(5, 5)
    assert listing.location is None  # E28-T3 owns explicit nearby-locality resolution.
    assert not result.warnings


@pytest.mark.parametrize("source", [APARTMENT, HOUSE])
def test_independent_evidence_exposes_candidate_misses_for_current_templates(source: str) -> None:
    result = extract_listing(_message(source))
    missed = replace(
        result,
        listing=None,
        decision=replace(
            result.decision, is_candidate=False, score=0, signals=(), content_type=None
        ),
    )
    quality = classify_parse(source, missed)
    assert quality.recovery_eligible
    assert quality.classification is ParseClassification.EXTRACTION_MISS
    price = next(field for field in quality.fields if field.field_name == "apartment_price")
    assert price.classification is ParseClassification.EXTRACTION_MISS
    assert price.spans


@pytest.mark.parametrize("field", ["apartment_price", "parking_price", "storage_price"])
def test_silent_new_label_misses_still_enter_recovery(field: str) -> None:
    result = extract_listing(_message(APARTMENT))
    assert result.listing is not None
    listing = result.listing
    missed = replace(
        result,
        listing=replace(
            listing,
            apartment_price=None if field == "apartment_price" else listing.apartment_price,
            parking_price=None if field == "parking_price" else listing.parking_price,
            storage_price=None if field == "storage_price" else listing.storage_price,
        ),
    )
    quality = classify_parse(APARTMENT, missed)
    assert quality.recovery_eligible
    assert next(f for f in quality.fields if f.field_name == field).classification is (
        ParseClassification.EXTRACTION_MISS
    )


@pytest.mark.parametrize(
    "text",
    ["", "Photo album", "Ремонт квартир: 38 м²", "Аренда дома: 4 000 zł", "Квартира: 900 zł"],
)
def test_non_offer_and_addon_prose_do_not_become_new_listing_candidates(text: str) -> None:
    assert extract_listing(_message(text)).listing is None


@pytest.mark.parametrize(
    "label",
    ["Цена за м²", "Паркоместо", "Кладовая 4 м²", "Аренда квартиры", "Аренда дома"],
)
def test_other_money_is_never_a_property_total(label: str) -> None:
    result = extract_listing(_message(f"🏡 Дом на продажу | 145 м²\n• {label}: 10 000 zł"))
    assert result.listing is not None
    assert result.listing.apartment_price is None


def test_conflicting_totals_and_room_counts_remain_unapplied() -> None:
    source = APARTMENT + "• Цена квартиры: 900 000 zł\n📐 38,6 м² | 3 комнаты\n"
    result = extract_listing(_message(source))
    assert result.listing is not None
    assert result.listing.apartment_price is None
    assert result.listing.rooms is None
    assert {warning.field_name for warning in result.warnings} >= {"apartment_price", "rooms"}


def test_explicit_detached_and_semi_detached_descriptions_still_conflict() -> None:
    result = extract_listing(_message(HOUSE + "Detached house\n"))
    assert result.listing is not None
    assert result.listing.property_type is None
    assert any(w.field_name == "property_type" for w in result.warnings)


@pytest.mark.parametrize("rooms", ["0", "21"])
def test_summary_room_count_rejects_invalid_bounds(rooms: str) -> None:
    result = extract_listing(_message(HOUSE.replace("5 комнат", f"{rooms} комнат")))
    assert result.listing is not None
    assert result.listing.rooms is None
    assert any(w.field_name == "rooms" for w in result.warnings)
