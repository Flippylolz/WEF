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
from wef_backend.features.ingestion.domain import ExtractionWarningCode, IntegerRange
from wef_backend.features.ingestion.domain.geocoding import (
    normalize_geocode_query,
    normalize_location_display_name,
)

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
    assert listing.location is not None
    assert listing.location.value == "Miejscowość Testowa, гмина Testowa"
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


@pytest.mark.parametrize(
    ("block", "address", "district"),
    [
        (
            (
                "📍 Локализация:\nul. Przykładowa\n"
                "\u0420\u0430\u0439\u043e\u043d: Białołęka, Nowodwory"
            ),
            "ul. Przykładowa",
            "Białołęka",
        ),
        (
            (
                "📍 Локализация:\nAl. Testowa\n"
                "\u0420\u0430\u0439\u043e\u043d: Śródmieście Północne, Śródmieście"
            ),
            "Al. Testowa",
            "Śródmieście",
        ),
        (
            (
                "📍 Локализация:\n\u0420\u0430\u0439\u043e\u043d: Praga-Południe, Grochów\n"
                "\u0423\u043b\u0438\u0446\u0430: Testowa"
            ),
            "\u0423\u043b\u0438\u0446\u0430: Testowa",
            "Praga-Południe",
        ),
        ("Location:\r\n\tul. Testowa 8\r\nDistrict: Wola", "ul. Testowa 8", "Wola"),
        ("Lokalizacja:\naleja Testowa\nDzielnica: Wola", "aleja Testowa", "Wola"),
        ("Street: ul. Testowa\nDistrict: Wola", "Street: ul. Testowa", "Wola"),
        (
            "Location:\n\u0443л. Aleja Testowa\nDistrict: Wilanów",
            "\u0443л. Aleja Testowa",
            "Wilanów",
        ),
    ],
)
def test_multiline_location_templates_keep_exact_source_evidence(
    block: str,
    address: str,
    district: str,
) -> None:
    source = f"For sale: Apartment\n{block}\nPrice: 800000 PLN\nArea: 45 m²"
    result = extract_listing(_message(source))
    listing = result.listing
    assert listing is not None
    assert listing.location is not None
    assert listing.location.value == address
    assert listing.location.provenance.spans[0].extract(source) == address
    assert listing.district is not None
    assert listing.district.value == district
    assert district in listing.district.provenance.spans[0].extract(source)
    display = normalize_location_display_name(address, district=district)
    query = normalize_geocode_query(display, district)
    assert query.address is not None
    assert query.address.street is not None
    assert query.address.district == district


@pytest.mark.parametrize(
    "block",
    [
        "📍 Локализация:\nPrice: 800000 PLN",
        "Location:\nPrice: 800000 PLN\nul. Testowa",
        "Location:\n\nDescription: near ul. Testowa",
        "Location:\n🏢 Floor: 4",
    ],
)
def test_empty_location_header_does_not_consume_another_section(block: str) -> None:
    listing = extract_listing(_message(f"For sale: Apartment\n{block}")).listing
    assert listing is not None
    assert listing.location is None


def test_district_only_block_retains_only_evidenced_district_precision() -> None:
    source = "For sale: Apartment\nLocation:\nDistrict: Skorosze, Ursus"
    listing = extract_listing(_message(source)).listing
    assert listing is not None
    assert listing.location is not None
    assert listing.location.value == "Ursus"
    assert listing.location.provenance.spans[0].extract(source) == "Skorosze, Ursus"
    display = normalize_location_display_name(listing.location.value)
    query = normalize_geocode_query(display)
    assert query.address is not None
    assert query.address.district == "Ursus"
    assert query.address.street is None


def test_unknown_labeled_district_cannot_become_a_location() -> None:
    listing = extract_listing(_message("For sale: Apartment\nDistrict: Not a district")).listing
    assert listing is not None
    assert listing.location is None


def test_district_fallback_preserves_a_supported_pin_address() -> None:
    listing = extract_listing(
        _message("For sale: Apartment\n📍 ul. Testowa\nDistrict: Unknown")
    ).listing
    assert listing is not None
    assert listing.location is not None
    assert listing.location.value == "ul. Testowa"


def test_district_fallback_cannot_hide_conflicting_pin_addresses() -> None:
    listing = extract_listing(
        _message("For sale: Apartment\n📍 ul. Testowa\n📍 ul. Inna\nDistrict: Wola")
    ).listing
    assert listing is not None
    assert listing.location is None


@pytest.mark.parametrize(
    "block",
    [
        "District: Wola, Mokotów",
        "Street: Testowa\nStreet: Inna",
        "ul. Testowa\nStreet: Inna",
    ],
)
def test_conflicting_multiline_address_components_remain_unresolved(block: str) -> None:
    result = extract_listing(_message(f"For sale: Apartment\nLocation:\n{block}"))
    assert result.listing is not None
    field = "district" if block.startswith("District") else "location"
    assert getattr(result.listing, field) is None
    assert any(
        warning.field_name == field and warning.code is ExtractionWarningCode.CONFLICTING_VALUES
        for warning in result.warnings
    )


@pytest.mark.parametrize("rooms", ["0", "21"])
def test_summary_room_count_rejects_invalid_bounds(rooms: str) -> None:
    result = extract_listing(_message(HOUSE.replace("5 комнат", f"{rooms} комнат")))
    assert result.listing is not None
    assert result.listing.rooms is None
    assert any(w.field_name == "rooms" for w in result.warnings)
