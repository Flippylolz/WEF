"""Conservative, independently evidenced semantics for automatic offer fills."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from wef_backend.features.ingestion.application.extraction import extract_contact_spans

# Only these scalar families have a finite calibration corpus. Other families
# remain observation-only until a reviewed calibration extends this artifact.
CALIBRATED_FIELDS = frozenset(
    {
        "apartment_price_min",
        "apartment_price_max",
        "parking_price_min",
        "parking_price_max",
        "storage_price_min",
        "storage_price_max",
        "area_min_sqm",
        "area_max_sqm",
        "rooms_min",
        "rooms_max",
        "market_type",
        "currency",
        "floor_label",
    }
)
_LABELS = {
    "apartment": r"(?:apartment price|price|cena(?: mieszkania)?|цена(?: квартиры| апартамента)?)",
    "parking": r"(?:parking(?: price)?|паркинг|miejsce postojowe|гараж)",
    "storage": r"(?:storage(?: price)?|кладов(?:ая|ка)|kom[oó]rka lokatorska)",
    "area": r"(?:area|powierzchnia|площадь|площа)",
    "rooms": r"(?:rooms?|pokoje?|комнаты|кімнати)",
    "market": r"(?:market|rynek|рынок|ринок)",
    "floor": r"(?:floor|pi[eę]tro|этаж)",
}
_NUMBER = r"(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d{1,2})?"
_MONEY = re.compile(rf"(?P<number>{_NUMBER})\s*(?P<currency>PLN|zł|EUR|€|USD|GBP)", re.IGNORECASE)
_AREA = re.compile(rf"(?P<number>{_NUMBER})\s*(?:m²|m2|sqm|м²|м2)", re.IGNORECASE)
_MARKETS = {
    "primary": "primary",
    "pierwotny": "primary",
    "первичный": "primary",
    "secondary": "secondary",
    "wtórny": "secondary",
    "вторичный": "secondary",
}
_PARKING_LINE = re.compile(
    rf"^[ \t]*(?:[•*][ \t]*)?{_LABELS['parking']}[ \t]*"
    r"(?:[:|][ \t]*|[\u2013\u2014-][ \t]+)(?P<value>[^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(" ", "").replace("\u00a0", "").replace(",", "."))


def evidence_supports_field(  # noqa: C901, PLR0911, PLR0912 - explicit semantic rejection gates
    source: str, fragment: str, name: str, proposed: object
) -> bool:
    """Require a unique exact non-contact fragment and agreed labeled scalar semantics."""
    if name not in CALIBRATED_FIELDS or not fragment or source.count(fragment) != 1:
        return False
    start, end = source.index(fragment), source.index(fragment) + len(fragment)
    if any(
        span.span.start < end and start < span.span.end for span in extract_contact_spans(source)
    ):
        return False
    family = "apartment" if name == "currency" else name.split("_", maxsplit=1)[0]
    if name == "market_type":
        family = "market"
    pattern = re.compile(
        rf"^[ \t]*(?:{_LABELS[family]})[ \t]*:[ \t]*(?P<value>[^\r\n]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    if family == "parking":
        pattern = _PARKING_LINE
    if family == "floor":
        pattern = re.compile(
            rf"^[ \t]*{_LABELS[family]}[ \t]*:?[ \t]+"
            r"(?P<value>\d{1,2}|parter|ground)(?=,|\.|\n|$| przy metrze[.,])",
            re.IGNORECASE | re.MULTILINE,
        )
    matches = tuple(pattern.finditer(source))
    if not matches:
        return False
    values = []
    supporting = False
    for match in matches:
        raw = match.group("value").strip()
        if match.start() <= start and end <= match.end():
            supporting = True
        if family == "floor":
            value: object = raw
        elif family == "market":
            value = _MARKETS.get(raw.casefold())
        elif family == "rooms":
            value = int(raw) if re.fullmatch(r"(?:[1-9]|1[0-9]|20)", raw) else None
        else:
            numeric = (_AREA if family == "area" else _MONEY).fullmatch(raw)
            if numeric is None:
                return False
            value = _decimal(numeric.group("number"))
            if value <= 0:
                return False
            if name == "currency":
                currency = numeric.group("currency").upper()
                value = {"ZŁ": "PLN", "€": "EUR"}.get(currency, currency)
        if value is None:
            return False
        values.append(value)
    if not supporting or len(set(values)) != 1:
        return False
    if isinstance(values[0], Decimal):
        try:
            return not isinstance(proposed, bool) and Decimal(str(proposed)) == values[0]
        except InvalidOperation:
            return False
    return type(proposed) is type(values[0]) and proposed == values[0]


def money_currency_matches(source: str, fragment: str, name: str, currency: str | None) -> bool:
    """Prevent a numeric price from acquiring a different canonical currency."""
    if currency is None or source.count(fragment) != 1:
        return False
    start, end = source.index(fragment), source.index(fragment) + len(fragment)
    family = name.split("_", maxsplit=1)[0]
    pattern = re.compile(
        rf"^[ \t]*{_LABELS[family]}[ \t]*:[ \t]*(?P<value>[^\r\n]+)", re.IGNORECASE | re.MULTILINE
    )
    if family == "parking":
        pattern = _PARKING_LINE
    supporting = False
    for match in pattern.finditer(source):
        money = _MONEY.fullmatch(match.group("value").strip())
        if money is None:
            return False
        unit = money.group("currency").upper()
        if {"ZŁ": "PLN", "€": "EUR"}.get(unit, unit) != currency:
            return False
        if match.start() <= start and end <= match.end():
            supporting = True
    return supporting


def listing_creation_supported(  # noqa: PLR0911 - reject unsupported creation semantics
    source: str, fields: tuple[dict[str, object], ...]
) -> bool:
    """Validate a narrow complete listing family without model-chosen relationships."""
    names = {str(field.get("field_name")) for field in fields}
    if not {"location", "currency", "apartment_price_min"} <= names:
        return False
    if not names <= CALIBRATED_FIELDS | {"location"}:
        return False
    currency = next(
        str(field["proposed_value"]) for field in fields if field["field_name"] == "currency"
    )
    for field in fields:
        name, fragment = str(field["field_name"]), str(field.get("evidence_fragment", ""))
        value = field.get("proposed_value")
        if "_price_" in name and not money_currency_matches(source, fragment, name, currency):
            return False
        if name != "location":
            if not evidence_supports_field(source, fragment, name, value):
                return False
        else:
            if not fragment or source.count(fragment) != 1 or not isinstance(value, str):
                return False
            match = re.search(
                r"^(?:Location|Lokalizacja|Адрес):[ \t]*(?P<value>Warszawa, [^\r\n]+)$",
                source,
                re.MULTILINE,
            )
            if match is None or match.group("value") != value:
                return False
            if fragment not in match.group() or extract_contact_spans(match.group()):
                return False
    return True
