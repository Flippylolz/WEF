"""Invented legacy quote shapes, not copied channel offers."""

from decimal import Decimal

import pytest

from tests.test_listing_extraction import _message
from wef_backend.features.catalog.domain import ContentType
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.extraction_inventory import extract_inventory
from wef_backend.features.ingestion.application.extraction_numbers import _parsed_money
from wef_backend.features.ingestion.application.persistence_projection import build_extraction_json
from wef_backend.features.ingestion.domain.geocoding import normalize_geocode_query

ROWS = (
    "• 2-комнатные квартиры — 35-45 м2 - от 510 000 злотых\n"
    "• 3-комнатные квартиры — 54-78 м2 - от 740 000 злотых"
)
SOURCE = "Квартиры от застройщика в Варшаве\n📍 ul. Syntetyczna, Warszawa\n" + ROWS


def test_developer_rows_preserve_inventory_ranges_and_unknown_price_ceiling() -> None:
    result = extract_listing(_message(SOURCE))
    listing = result.listing
    assert listing
    assert listing.content_type
    assert listing.content_type.value == ContentType.DEVELOPMENT
    assert listing.apartment_price
    assert listing.apartment_price.value.is_lower_bound
    assert listing.apartment_price.value.amount.lower == Decimal(510000)
    assert listing.area_sqm
    assert listing.area_sqm.value.lower == Decimal(35)
    assert listing.area_sqm.value.upper == Decimal(78)
    assert listing.rooms
    assert (listing.rooms.value.lower, listing.rooms.value.upper) == (2, 3)
    assert '"max_minor":null' in build_extraction_json(listing)
    assert not result.warnings


def test_exact_advertised_inventory_quotes_keep_both_price_bounds() -> None:
    inventory = extract_inventory(ROWS.replace("от ", ""))
    assert inventory
    assert not inventory.price.is_lower_bound
    assert inventory.price.amount.upper == Decimal(740000)


@pytest.mark.parametrize("replacement", ["USD", "злотых/м²", "", "злотых + parking 20 000 zł"])
def test_partial_or_non_total_inventory_rows_do_not_produce_a_range(replacement: str) -> None:
    assert extract_inventory(ROWS.replace("злотых", replacement, 1)) is None


def test_scalar_fields_and_non_development_ads_do_not_use_inventory_fallback() -> None:
    listing = extract_listing(_message(SOURCE + "\nCena: 900 000 PLN")).listing
    assert listing
    assert listing.apartment_price
    assert listing.apartment_price.value.amount.lower == Decimal(900000)
    assert extract_inventory(ROWS.splitlines()[0]) is None
    assert extract_inventory(ROWS.replace("35-45", "45-35")) is None
    assert extract_inventory(ROWS.replace("2-комнатные", "0-комнатные")) is None
    assert extract_inventory("\n".join([ROWS] * 11)) is None


def test_cyrillic_per_area_quote_cannot_replace_or_hide_the_total() -> None:
    quote = _parsed_money("1 150 000 zł | (13 000 zł/м²)")
    assert quote
    assert quote.amount.lower == Decimal(1150000)
    assert _parsed_money("13 000 zł/м²") is None
    floor = _parsed_money("от 500 000 PLN")
    assert floor
    assert floor.is_lower_bound


def test_exact_spaced_north_praga_remains_a_warsaw_district() -> None:
    query = normalize_geocode_query("ul. Syntetyczna, Praga Północ")
    assert query.address
    assert query.address.city == "Warszawa"
    assert query.address.district == "Praga-Północ"
