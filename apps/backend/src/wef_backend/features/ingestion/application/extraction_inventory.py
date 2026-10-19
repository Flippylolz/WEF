"""Bounded advertised apartment rows, retaining ranges and open price bounds."""

from __future__ import annotations

import re
from dataclasses import dataclass

from wef_backend.features.ingestion.application.extraction_numbers import (
    _NUMBER,
    _decimal_range,
    _parsed_money,
)
from wef_backend.features.ingestion.domain import DecimalRange, IntegerRange, MoneyRange, SourceSpan

_START = re.compile(r"(?m)^[ \t]*[•*-]?[ \t]*\d+[- ]комнатные[ \t]+квартиры\b", re.IGNORECASE)
_ROW = re.compile(
    r"(?m)^[ \t]*[•*-]?[ \t]*(?P<rooms>\d+)[- ]комнатные[ \t]+квартиры"
    r"[ \t]*[\u2014\u2013-][ \t]*(?P<area>\d+(?:[,.]\d+)?"
    r"(?:[ \t]*[\u2014\u2013-][ \t]*\d+(?:[,.]\d+)?)?)"
    r"[ \t]*[mм][²2][ \t]*[\u2014\u2013-][ \t]*"
    rf"(?P<price>(?:(?:от|from|od)[ \t]+)?{_NUMBER}[ \t]*(?:PLN|zł|злотых))[ \t]*$",
    re.IGNORECASE,
)
_MIN_ROWS = 2
_MAX_ROWS = 20
_MAX_ROOMS = 20


@dataclass(frozen=True, slots=True)
class InventoryQuote:
    """Ranges summarize quoted units; starting prices never imply a ceiling."""

    price: MoneyRange
    area: DecimalRange
    rooms: IntegerRange
    span: SourceSpan


def extract_inventory(text: str) -> InventoryQuote | None:
    """Require every advertised apartment row to be complete and consistently denominated."""
    rows = tuple(_ROW.finditer(text))
    if not _MIN_ROWS <= len(rows) <= _MAX_ROWS or len(rows) != len(tuple(_START.finditer(text))):
        return None
    prices, areas, rooms = [], [], []
    for row in rows:
        price = _parsed_money(row.group("price"))
        area = _decimal_range(row.group("area"))
        room_count = int(row.group("rooms"))
        if price is None or price.currency != "PLN" or price.amount.lower <= 0:
            return None
        if area is None or area.lower <= 0 or not 1 <= room_count <= _MAX_ROOMS:
            return None
        prices.append(price)
        areas.append(area)
        rooms.append(room_count)
    return InventoryQuote(
        price=MoneyRange(
            DecimalRange(min(p.amount.lower for p in prices), max(p.amount.upper for p in prices)),
            "PLN",
            is_lower_bound=any(p.is_lower_bound for p in prices),
        ),
        area=DecimalRange(min(a.lower for a in areas), max(a.upper for a in areas)),
        rooms=IntegerRange(min(rooms), max(rooms)),
        span=SourceSpan(rows[0].start(), rows[-1].end()),
    )
