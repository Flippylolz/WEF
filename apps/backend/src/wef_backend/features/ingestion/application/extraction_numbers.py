"""Pure numeric, currency and room parsing; no extraction assembly or I/O."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from wef_backend.features.ingestion.domain import DecimalRange, IntegerRange, MoneyRange

_ALTERNATIVE_QUOTE_COUNT = 2

_MAX_RANGE_VALUES = 2

_MAX_ROOM_COUNT = 20

_FLAGS = re.IGNORECASE | re.UNICODE

_CURRENCY_WORD = r"(?:злот\w*|złot\w*|zlot\w*)"

_NUMBER = (
    r"(?<!\w)(?:\d{1,3}(?:[ \u00a0]\d{3})+(?:[,.]\d+)?|\d+(?:[,.]\d+)?)"
    r"(?=$|[\s\u00a0.,;:|()\[\]{}»«\"'\u2013\u2014-]|" + _CURRENCY_WORD + r")"
)

_NUMBER_PATTERN = re.compile(_NUMBER)

_ROOM_SLUG = r"(?:комнат(?:ная|ные|[аы])|кімнат(?:на|ні))"

_ROOM_TAG_PATTERN = re.compile(
    rf"#\s*\d+\s*[_ -]?\s*(?:pokoje?|rooms?|{_ROOM_SLUG})(?!\w)",
    _FLAGS,
)

_ROOM_RANGE_PATTERN = re.compile(
    r"\s*(?P<lower>\d+)(?:\s*(?:-|\u2013|\u2014|\b\u0434\u043e\b|\bto\b)"
    r"\s*(?P<upper>\d+))?\s*",
    _FLAGS,
)

_RANGE_JOINER_PATTERN = re.compile(
    r"(?:-|\u2013|\u2014|\b\u0434\u043e\b|\bto\b)",
    _FLAGS,
)

_CURRENCY_PATTERN = re.compile(
    rf"(?:\b(?P<iso>PLN|EUR|USD|GBP)\b|(?P<symbol>zł|€|\$)|(?P<word>{_CURRENCY_WORD}))",
    _FLAGS,
)

_PER_AREA_CONTEXT_PATTERN = re.compile(
    rf"(?:\(\s*)?{_NUMBER}\s*(?:PLN|EUR|USD|GBP|zł|€|\$|{_CURRENCY_WORD})?\s*"
    r"(?:/|\bper\b|\bza\b|\bna\b|\b\u0437\u0430\b)\s*"
    r"(?:m(?:²|2)|sqm|\u043a\u0432\.?\s*\u043c)(?:\s*\))?",
    _FLAGS,
)


def _decimal_range(value: str) -> DecimalRange | None:
    matches = tuple(_NUMBER_PATTERN.finditer(value))
    if not 0 < len(matches) <= _MAX_RANGE_VALUES:
        return None
    try:
        lower = _decimal(matches[0].group())
        upper = lower
        if len(matches) == _MAX_RANGE_VALUES:
            separator = value[matches[0].end() : matches[1].start()]
            if _RANGE_JOINER_PATTERN.fullmatch(separator.strip()) is None:
                return None
            upper = _decimal(matches[1].group())
        return DecimalRange(lower=lower, upper=upper)
    except (InvalidOperation, ValueError):
        return None


def _primary_money_fragment(value: str) -> str:
    """Separate explicitly named appended add-ons, never an unexplained sum."""
    parts = re.split(r"\s+\+\s+", value, maxsplit=1)
    if len(parts) == _ALTERNATIVE_QUOTE_COUNT and re.match(
        r"(?:parking|паркинг|паркінг|storage|комора|кладов\w*|kom[oó]rka)\b",
        parts[1],
        _FLAGS,
    ):
        return parts[0]
    return value


def _parsed_money(value: str) -> MoneyRange | None:
    """Keep quote currency, actual ranges and per-area context distinct."""
    value = _primary_money_fragment(value)
    contexts = tuple(_PER_AREA_CONTEXT_PATTERN.finditer(value))
    numbers = tuple(
        match
        for match in _NUMBER_PATTERN.finditer(value)
        if not any(context.start() <= match.start() < context.end() for context in contexts)
    )
    if not numbers or any(context.start() < numbers[-1].end() for context in contexts):
        return None
    primary = value[: contexts[0].start()] if contexts else value
    primary = primary.strip().rstrip("(").strip()
    # Explicit alternatives are independently denominated scalar quotes. PLN is
    # selected only when supplied; the second quote is never an exchange rate.
    alternatives = re.split(
        r"\s*(?:/|=|\bor\b|\blub\b|\bили\b|\b\u0430\u0431\u043e\b|\()\s*", primary, flags=_FLAGS
    )
    if len(alternatives) > 1:
        quotes = tuple(_single_currency_money(part.strip().rstrip(")")) for part in alternatives)
        if len(quotes) != _ALTERNATIVE_QUOTE_COUNT or any(quote is None for quote in quotes):
            return None
        valid = tuple(quote for quote in quotes if quote is not None)
        if any(
            quote.currency is None or quote.amount.lower != quote.amount.upper for quote in valid
        ):
            return None
        if len({quote.currency for quote in valid}) != len(valid):
            return None
        return next((quote for quote in valid if quote.currency == "PLN"), None)
    return _single_currency_money(primary)


def _single_currency_money(value: str) -> MoneyRange | None:
    currencies = {_currency(match.group()) for match in _CURRENCY_PATTERN.finditer(value)}
    if len(currencies) > 1:
        return None
    numbers = tuple(_NUMBER_PATTERN.finditer(value))
    if not 0 < len(numbers) <= _MAX_RANGE_VALUES:
        return None
    if re.search(r"[-\u2212]", value[: numbers[0].start()]):
        return None
    # Strip currency markers between endpoints only after verifying agreement.
    amount_text = numbers[0].group()
    if len(numbers) == _MAX_RANGE_VALUES:
        separator = _CURRENCY_PATTERN.sub("", value[numbers[0].end() : numbers[1].start()])
        amount_text += separator + numbers[1].group()
    amount = _decimal_range(amount_text)
    if amount is None:
        return None
    return MoneyRange(amount, next(iter(currencies), None))


def _room_range(value: str) -> IntegerRange | None:
    match = _ROOM_RANGE_PATTERN.fullmatch(value)
    if match is None:
        return None
    lower = int(match.group("lower"))
    upper_group = match.group("upper")
    upper = int(upper_group) if upper_group is not None else lower
    if not 0 < lower <= upper <= _MAX_ROOM_COUNT:
        return None
    return IntegerRange(lower=lower, upper=upper)


def _is_room_tag_list(value: str) -> bool:
    if _ROOM_TAG_PATTERN.search(value) is None:
        return False
    remainder = _ROOM_TAG_PATTERN.sub("", value)
    return not remainder.strip(" \t,;|")


def _room_tag_range(value: str) -> IntegerRange | None:
    match = re.search(r"\d+", value)
    if match is None:
        return None
    room = int(match.group())
    if not 0 < room <= _MAX_ROOM_COUNT:
        return None
    return IntegerRange(lower=room, upper=room)


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(" ", "").replace("\u00a0", "").replace(",", "."))


def _currency(value: str) -> str | None:
    match = _CURRENCY_PATTERN.search(value)
    if match is None:
        return None
    if match.group("word") is not None:
        return "PLN"
    currency_marker = match.group("iso") or match.group("symbol")
    folded = currency_marker.casefold()
    if folded == "zł":
        return "PLN"
    if currency_marker == "€":
        return "EUR"
    if currency_marker == "$":
        return "USD"
    return currency_marker.upper()
