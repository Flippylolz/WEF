"""Invented regression cases for deterministic garage prices and recovery evidence."""

# ruff: noqa: RUF001 - intentional multilingual fixtures
from decimal import Decimal

import pytest

from tests.test_listing_extraction import _message
from wef_backend.features.admin.application.recovery_validation import (
    evidence_supports_field,
    money_currency_matches,
)
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.parse_quality import classify_parse
from wef_backend.features.ingestion.domain import DecimalRange


@pytest.mark.parametrize("prefix", ["", "• ", "* "])
@pytest.mark.parametrize("separator", [": ", " — ", " – ", " - "])
def test_garage_quote_is_extracted_without_ai(prefix: str, separator: str) -> None:
    quote = f"{prefix}гараж{separator}47 500 zł"
    source = f"For sale: apartment\nPrice: 825000 PLN\n{quote}"
    result = extract_listing(_message(source))
    assert result.listing is not None
    price = result.listing.parking_price
    assert price is not None
    assert price.value.amount == DecimalRange(Decimal(47500), Decimal(47500))
    assert price.value.currency == "PLN"
    assert price.provenance.rule_version == PARSER_VERSION
    assert price.provenance.spans[0].extract(source) == "47 500 zł"
    assert result.listing.parking_included_in_price is None
    assert result.listing.market_type is None
    assert not classify_parse(source, result).recovery_eligible
    for field in ("parking_price_min", "parking_price_max"):
        assert evidence_supports_field(source, quote, field, 47500)
        assert money_currency_matches(source, quote, field, "PLN")
        assert not money_currency_matches(source, quote, field, "EUR")
        assert not evidence_supports_field(source, quote, field, 47501)


@pytest.mark.parametrize(
    "quote",
    [
        "• гараж — аренда 450 zł",
        "• гараж — 450 zł/месяц",
        "• гараж — доступен по запросу",
        "• гараж — 47500 zł или 12000 EUR",
        "• гараж — 47500-55000 zł",
        "• гараж — -47500 zł",
        "• гараж — 47500 zł + 5000 zł",
        "• аренда гараж — 47500 zł",
        "• гараж —\n47500 zł",
    ],
)
def test_garage_availability_and_non_scalar_quotes_are_not_purchase_prices(quote: str) -> None:
    source = f"For sale: apartment\nPrice: 825000 PLN\n{quote}"
    result = extract_listing(_message(source))
    assert result.listing is not None
    assert result.listing.parking_price is None
    assert not evidence_supports_field(source, quote, "parking_price_min", 47500)


def test_conflicting_garage_quotes_remain_blocked() -> None:
    quote = "• гараж — 47500 zł"
    source = f"For sale: apartment\n{quote}\nгараж: 55000 zł"
    result = extract_listing(_message(source))
    assert result.listing is not None
    assert result.listing.parking_price is None
    assert any(w.field_name == "parking_price" for w in result.warnings)
    assert not classify_parse(source, result).recovery_eligible
    assert not evidence_supports_field(source, quote, "parking_price_min", 47500)


def test_sale_and_separate_price_do_not_prove_market_or_inclusion() -> None:
    title = "3-комнатная квартира | продажа"
    quote = "• гараж — 47500 zł"
    source = f"{title}\n{quote}"
    assert not evidence_supports_field(source, title, "market_type", "secondary")
    assert not evidence_supports_field(source, quote, "parking_included_in_price", proposed=False)
    assert not evidence_supports_field(source, quote, "parking_included_in_price", proposed=True)
    assert not evidence_supports_field(source, quote, "apartment_price_min", 47500)


def test_equal_amounts_in_conflicting_currencies_do_not_validate() -> None:
    quote = "• гараж — 47500 zł"
    source = f"{quote}\nгараж: 47500 EUR"
    assert not money_currency_matches(source, quote, "parking_price_min", "PLN")
