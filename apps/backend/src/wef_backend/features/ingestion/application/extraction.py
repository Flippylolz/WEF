"""Deterministic E2 listing-candidate detection and typed extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from wef_backend.features.catalog.domain import ContentType, MarketType
from wef_backend.features.ingestion.domain import (
    CandidateDecision,
    CandidateReason,
    CandidateSignal,
    Confidence,
    ContactKind,
    ContactSpan,
    DecimalRange,
    ExtractedValue,
    ExtractionResult,
    ExtractionWarning,
    ExtractionWarningCode,
    IntegerRange,
    LinkKind,
    LinkSpan,
    ListingCandidate,
    MoneyRange,
    RawMessage,
    RuleProvenance,
    SourceSpan,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

PARSER_VERSION = "e2-v1"
CANDIDATE_THRESHOLD = 5
_MAX_RANGE_VALUES = 2

_FLAGS = re.IGNORECASE | re.UNICODE
_NUMBER = r"(?<!\w)(?:\d{1,3}(?:[ \u00a0]\d{3})+(?:[,.]\d+)?|\d+(?:[,.]\d+)?)(?!\w)"
_VALUE_SUFFIX = r"\s*(?:[:|]\s*|[\u2013\u2014-]\s+)(?P<value>[^\r\n]+)"
_NUMBER_PATTERN = re.compile(_NUMBER)
_CURRENCY_PATTERN = re.compile(r"(?:\b(?P<iso>PLN|EUR|USD|GBP)\b|(?P<symbol>zł|€|\$))", _FLAGS)
_INCLUDED_PATTERN = re.compile(
    r"\b(?:included|w cenie|wliczon[eya]?|включен[аоы]?|входит в стоимость)\b",
    _FLAGS,
)
_GOOGLE_MAPS_PATTERN = re.compile(
    r"https?://(?:maps\.app\.goo\.gl|goo\.gl/maps|(?:www\.)?google\.[^/\s]+/maps)"
    r"[^\s<>()]*",
    _FLAGS,
)
_PHONE_PATTERN = re.compile(r"(?<!\w)\+\d(?:[\d ()-]{7,}\d)(?!\w)")
_TELEGRAM_PATTERN = re.compile(r"(?<!\w)@[A-Za-z][A-Za-z0-9_]{4,}")


@dataclass(frozen=True, slots=True)
class _CandidateRule:
    reason: CandidateReason
    weight: int
    content_type: ContentType | None
    pattern: re.Pattern[str]


_CANDIDATE_RULES = (
    _CandidateRule(
        CandidateReason.DEVELOPMENT_HEADER,
        5,
        ContentType.DEVELOPMENT,
        re.compile(
            r"(?:\b(?:inwestycj[ae]|development|новостройк[аи]|инвестици[яи])\b"
            r"|(?:rynek|рынок)\s+(?:pierwotny|первичн\w+))",
            _FLAGS,
        ),
    ),
    _CandidateRule(
        CandidateReason.PURCHASE_HEADER,
        5,
        ContentType.UNIT,
        re.compile(
            r"(?:^|\n)\s*(?:покупка|kupno|for sale)\s*[|:\u2013\u2014-]",
            _FLAGS,
        ),
    ),
    _CandidateRule(
        CandidateReason.UNIT_MARKER,
        3,
        ContentType.UNIT,
        re.compile(r"\b(?:mieszkanie|apartament|квартир[аы]|апартамент[ыа]?)\b", _FLAGS),
    ),
    _CandidateRule(
        CandidateReason.LOCATION_MARKER,
        2,
        None,
        re.compile(r"\b(?:lokalizacja|location|adres|локализаци[яи]|адрес)\b", _FLAGS),
    ),
    _CandidateRule(
        CandidateReason.PRICE_MARKER,
        2,
        None,
        re.compile(r"\b(?:cena|price|цен[аы])\b", _FLAGS),
    ),
    _CandidateRule(
        CandidateReason.AREA_MARKER,
        2,
        None,
        re.compile(r"(?:\b(?:powierzchnia|area|площадь)\b|m[²2])", _FLAGS),
    ),
    _CandidateRule(
        CandidateReason.ROOM_MARKER,
        1,
        None,
        re.compile(
            r"(?:#\d+\b|\b(?:pokoje?|rooms?|комнат[аы]?|pok\.)\s*"
            r"(?:[:|]|\u2013|\u2014|-))",
            _FLAGS,
        ),
    ),
    _CandidateRule(
        CandidateReason.GOOGLE_MAPS_LINK,
        1,
        None,
        _GOOGLE_MAPS_PATTERN,
    ),
)

_MARKET_PATTERN = re.compile(
    rf"(?:rynek|market|рынок){_VALUE_SUFFIX}",
    _FLAGS,
)
_LOCATION_PATTERN = re.compile(
    rf"(?:lokalizacja|location|adres|локализаци[яи]|адрес){_VALUE_SUFFIX}",
    _FLAGS,
)
_DISTRICT_PATTERN = re.compile(
    rf"(?:dzielnica|district|район){_VALUE_SUFFIX}",
    _FLAGS,
)
_DEVELOPMENT_PATTERN = re.compile(
    rf"(?:inwestycja|development(?: name)?|название проекта|жилой комплекс|жк){_VALUE_SUFFIX}",
    _FLAGS,
)
_APARTMENT_PRICE_PATTERN = re.compile(
    rf"(?:cena(?: mieszkania)?|apartment price|price|цена(?: квартиры)?){_VALUE_SUFFIX}",
    _FLAGS,
)
_PARKING_PATTERN = re.compile(rf"(?:parking|паркинг|miejsce postojowe){_VALUE_SUFFIX}", _FLAGS)
_STORAGE_PATTERN = re.compile(
    rf"(?:storage|комора|кладов(?:ая|ка)|kom[oó]rka lokatorska){_VALUE_SUFFIX}",
    _FLAGS,
)
_AREA_PATTERN = re.compile(rf"(?:powierzchnia|area|площадь){_VALUE_SUFFIX}", _FLAGS)
_ROOMS_PATTERN = re.compile(rf"(?:pokoje?|rooms?|комнат[аы]?){_VALUE_SUFFIX}", _FLAGS)
_FLOOR_PATTERN = re.compile(rf"(?:pi[eę]tro|floor|этаж){_VALUE_SUFFIX}", _FLAGS)
_DELIVERY_PATTERN = re.compile(
    rf"(?:oddanie|delivery|completion|сдача|готовность){_VALUE_SUFFIX}",
    _FLAGS,
)


def detect_candidate(
    message: RawMessage,
    *,
    parser_version: str = PARSER_VERSION,
) -> CandidateDecision:
    """Score one unchanged raw message against stable candidate evidence."""
    signals: list[CandidateSignal] = []
    if message.message_type == "message":
        for rule in _CANDIDATE_RULES:
            match = rule.pattern.search(message.text)
            if match is not None:
                span = SourceSpan(*match.span())
                signals.append(
                    CandidateSignal(
                        reason=rule.reason,
                        weight=rule.weight,
                        provenance=_provenance(
                            f"candidate.{rule.reason.value}",
                            parser_version,
                            Confidence.HIGH
                            if rule.weight >= CANDIDATE_THRESHOLD
                            else Confidence.MEDIUM,
                            span,
                        ),
                    )
                )
    score = sum(signal.weight for signal in signals)
    is_candidate = score >= CANDIDATE_THRESHOLD
    return CandidateDecision(
        parser_version=parser_version,
        is_candidate=is_candidate,
        score=score,
        threshold=CANDIDATE_THRESHOLD,
        content_type=_decision_content_type(signals) if is_candidate else None,
        signals=tuple(signals),
    )


def extract_listing(
    message: RawMessage,
    *,
    parser_version: str = PARSER_VERSION,
) -> ExtractionResult:
    """Detect and extract one listing without mutating its raw evidence."""
    decision = detect_candidate(message, parser_version=parser_version)
    if not decision.is_candidate:
        return ExtractionResult(decision=decision, listing=None)

    warnings: list[ExtractionWarning] = []
    content_type = _content_value(decision, warnings)
    market_type = _market_type(message.text, parser_version, warnings)
    location = _string_field(
        message.text,
        _LOCATION_PATTERN,
        "location",
        parser_version,
        warnings,
    )
    district = _string_field(
        message.text,
        _DISTRICT_PATTERN,
        "district",
        parser_version,
        warnings,
    )
    development_name = _string_field(
        message.text,
        _DEVELOPMENT_PATTERN,
        "development_name",
        parser_version,
        warnings,
    )
    apartment_price = _money_field(
        message.text,
        _APARTMENT_PRICE_PATTERN,
        "apartment_price",
        parser_version,
        warnings,
    )
    parking_price, parking_included = _addon_fields(
        message.text,
        _PARKING_PATTERN,
        "parking",
        parser_version,
        warnings,
    )
    storage_price, storage_included = _addon_fields(
        message.text,
        _STORAGE_PATTERN,
        "storage",
        parser_version,
        warnings,
    )
    area = _range_field(
        message.text,
        _AREA_PATTERN,
        "area_sqm",
        parser_version,
        warnings,
        _decimal_range,
    )
    rooms = _range_field(
        message.text,
        _ROOMS_PATTERN,
        "rooms",
        parser_version,
        warnings,
        _integer_range,
    )
    floor = _string_field(message.text, _FLOOR_PATTERN, "floor", parser_version, warnings)
    delivery = _string_field(
        message.text,
        _DELIVERY_PATTERN,
        "delivery",
        parser_version,
        warnings,
    )
    listing = ListingCandidate(
        source_message_id=message.external_message_id,
        source_checksum=message.checksum,
        parser_version=parser_version,
        content_type=content_type,
        market_type=market_type,
        location=location,
        district=district,
        development_name=development_name,
        apartment_price=apartment_price,
        parking_price=parking_price,
        storage_price=storage_price,
        parking_included_in_price=parking_included,
        storage_included_in_price=storage_included,
        area_sqm=area,
        rooms=rooms,
        floor=floor,
        delivery=delivery,
        map_links=_map_links(message.text, parser_version),
        contacts=_contacts(message.text, parser_version),
    )
    return ExtractionResult(decision=decision, listing=listing, warnings=tuple(warnings))


def _decision_content_type(signals: Sequence[CandidateSignal]) -> ContentType | None:
    strong_types = {
        rule.content_type
        for rule in _CANDIDATE_RULES
        if rule.weight >= CANDIDATE_THRESHOLD
        and rule.content_type is not None
        and any(signal.reason is rule.reason for signal in signals)
    }
    if len(strong_types) == 1:
        return next(iter(strong_types))
    if len(strong_types) > 1:
        return None
    if any(signal.reason is CandidateReason.UNIT_MARKER for signal in signals):
        return ContentType.UNIT
    return None


def _content_value(
    decision: CandidateDecision,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[ContentType] | None:
    if decision.content_type is None:
        content_signals = tuple(
            signal
            for signal in decision.signals
            if signal.reason
            in {
                CandidateReason.DEVELOPMENT_HEADER,
                CandidateReason.PURCHASE_HEADER,
                CandidateReason.UNIT_MARKER,
            }
        )
        if len(content_signals) > 1:
            warnings.append(
                ExtractionWarning(
                    code=ExtractionWarningCode.CONFLICTING_CONTENT_TYPE,
                    field_name="content_type",
                    spans=tuple(signal.provenance.spans[0] for signal in content_signals),
                )
            )
        return None
    preferred_reason = (
        CandidateReason.DEVELOPMENT_HEADER
        if decision.content_type is ContentType.DEVELOPMENT
        else CandidateReason.PURCHASE_HEADER
    )
    signal = next(
        (item for item in decision.signals if item.reason is preferred_reason),
        None,
    )
    if signal is None:
        signal = next(
            item for item in decision.signals if item.reason is CandidateReason.UNIT_MARKER
        )
    return ExtractedValue(value=decision.content_type, provenance=signal.provenance)


def _market_type(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[MarketType] | None:
    return _mapped_string_field(
        text,
        _MARKET_PATTERN,
        "market_type",
        parser_version,
        warnings,
        _parse_market_type,
    )


def _parse_market_type(value: str) -> MarketType:
    folded = value.casefold()
    if any(token in folded for token in ("pierwot", "primary", "первич")):
        return MarketType.PRIMARY
    if any(token in folded for token in ("wtór", "wtor", "secondary", "вторич")):
        return MarketType.SECONDARY
    return MarketType.UNKNOWN


def _string_field(
    text: str,
    pattern: re.Pattern[str],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[str] | None:
    return _mapped_string_field(
        text,
        pattern,
        field_name,
        parser_version,
        warnings,
        lambda value: value,
    )


def _mapped_string_field[T](  # noqa: PLR0913, PLR0917
    text: str,
    pattern: re.Pattern[str],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
    mapper: Callable[[str], T],
) -> ExtractedValue[T] | None:
    matches = tuple(pattern.finditer(text))
    values = tuple((_trimmed_value(text, match), match) for match in matches)
    values = tuple((value, match) for value, match in values if value)
    if not values:
        return None
    mapped = tuple((mapper(value), match) for value, match in values)
    if len({value for value, _ in mapped}) > 1:
        warnings.append(_conflict_warning(field_name, text, matches))
        return None
    value, match = mapped[0]
    span = _trimmed_span(text, match)
    return ExtractedValue(
        value=value,
        provenance=_provenance(
            f"extract.{field_name}",
            parser_version,
            Confidence.HIGH,
            span,
        ),
    )


def _money_field(
    text: str,
    pattern: re.Pattern[str],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[MoneyRange] | None:
    matches = tuple(pattern.finditer(text))
    parsed: list[tuple[MoneyRange, re.Match[str]]] = []
    for match in matches:
        value = _trimmed_value(text, match)
        amount = _decimal_range(value)
        if amount is None:
            if _NUMBER_PATTERN.search(value):
                warnings.append(_invalid_range_warning(field_name, text, match))
            continue
        currency = _currency(value)
        if currency is None:
            warnings.append(
                ExtractionWarning(
                    code=ExtractionWarningCode.UNKNOWN_CURRENCY,
                    field_name=field_name,
                    spans=(_trimmed_span(text, match),),
                )
            )
        parsed.append((MoneyRange(amount=amount, currency=currency), match))
    return _unique_parsed_value(text, parsed, field_name, parser_version, warnings)


def _addon_fields(
    text: str,
    pattern: re.Pattern[str],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> tuple[ExtractedValue[MoneyRange] | None, ExtractedValue[bool] | None]:
    matches = tuple(pattern.finditer(text))
    included_matches = tuple(
        match for match in matches if _INCLUDED_PATTERN.search(_trimmed_value(text, match))
    )
    if included_matches:
        if len(matches) > len(included_matches):
            warnings.append(_conflict_warning(f"{field_name}_price", text, matches))
            return None, None
        match = included_matches[0]
        span = _trimmed_span(text, match)
        return (
            None,
            ExtractedValue(
                value=True,
                provenance=_provenance(
                    f"extract.{field_name}_included",
                    parser_version,
                    Confidence.HIGH,
                    span,
                ),
            ),
        )
    return (
        _money_field(text, pattern, f"{field_name}_price", parser_version, warnings),
        None,
    )


def _range_field[T](  # noqa: PLR0913, PLR0917
    text: str,
    pattern: re.Pattern[str],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
    parser: Callable[[str], T | None],
) -> ExtractedValue[T] | None:
    matches = tuple(pattern.finditer(text))
    parsed: list[tuple[T, re.Match[str]]] = []
    for match in matches:
        value = parser(_trimmed_value(text, match))
        if value is None:
            if _NUMBER_PATTERN.search(_trimmed_value(text, match)):
                warnings.append(_invalid_range_warning(field_name, text, match))
            continue
        parsed.append((value, match))
    return _unique_parsed_value(text, parsed, field_name, parser_version, warnings)


def _unique_parsed_value[T](
    text: str,
    parsed: Sequence[tuple[T, re.Match[str]]],
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[T] | None:
    if not parsed:
        return None
    if len({value for value, _ in parsed}) > 1:
        warnings.append(_conflict_warning(field_name, text, tuple(match for _, match in parsed)))
        return None
    value, match = parsed[0]
    return ExtractedValue(
        value=value,
        provenance=_provenance(
            f"extract.{field_name}",
            parser_version,
            Confidence.HIGH,
            _trimmed_span(text, match),
        ),
    )


def _decimal_range(value: str) -> DecimalRange | None:
    numbers = _NUMBER_PATTERN.findall(value)
    if not numbers or len(numbers) > _MAX_RANGE_VALUES:
        return None
    try:
        parsed = tuple(_decimal(number) for number in numbers)
        lower, upper = (parsed[0], parsed[0]) if len(parsed) == 1 else parsed
        return DecimalRange(lower=lower, upper=upper)
    except (InvalidOperation, ValueError):
        return None


def _integer_range(value: str) -> IntegerRange | None:
    parsed = _decimal_range(value)
    if (
        parsed is None
        or parsed.lower != parsed.lower.to_integral_value()
        or (parsed.upper != parsed.upper.to_integral_value())
    ):
        return None
    try:
        return IntegerRange(lower=int(parsed.lower), upper=int(parsed.upper))
    except ValueError:
        return None


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(" ", "").replace("\u00a0", "").replace(",", "."))


def _currency(value: str) -> str | None:
    match = _CURRENCY_PATTERN.search(value)
    if match is None:
        return None
    currency_marker = match.group("iso") or match.group("symbol")
    folded = currency_marker.casefold()
    if folded == "zł":
        return "PLN"
    if currency_marker == "€":
        return "EUR"
    if currency_marker == "$":
        return "USD"
    return currency_marker.upper()


def _map_links(text: str, parser_version: str) -> tuple[LinkSpan, ...]:
    links: list[LinkSpan] = []
    for match in _GOOGLE_MAPS_PATTERN.finditer(text):
        span = SourceSpan(*match.span())
        links.append(
            LinkSpan(
                kind=LinkKind.GOOGLE_MAPS,
                url=match.group(),
                span=span,
                provenance=_provenance(
                    "extract.google_maps_link",
                    parser_version,
                    Confidence.HIGH,
                    span,
                ),
            )
        )
    return tuple(links)


def _contacts(text: str, parser_version: str) -> tuple[ContactSpan, ...]:
    contacts: list[ContactSpan] = []
    for kind, pattern in (
        (ContactKind.PHONE, _PHONE_PATTERN),
        (ContactKind.TELEGRAM, _TELEGRAM_PATTERN),
    ):
        for match in pattern.finditer(text):
            span = SourceSpan(*match.span())
            contacts.append(
                ContactSpan(
                    kind=kind,
                    value=match.group(),
                    span=span,
                    provenance=_provenance(
                        f"extract.contact.{kind.value}",
                        parser_version,
                        Confidence.HIGH,
                        span,
                    ),
                )
            )
    return tuple(sorted(contacts, key=lambda item: item.span))


def _trimmed_value(text: str, match: re.Match[str]) -> str:
    return _trimmed_span(text, match).extract(text)


def _trimmed_span(text: str, match: re.Match[str]) -> SourceSpan:
    start, end = match.span("value")
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return SourceSpan(start, end)


def _provenance(
    rule_id: str,
    rule_version: str,
    confidence: Confidence,
    *spans: SourceSpan,
) -> RuleProvenance:
    return RuleProvenance(
        rule_id=rule_id,
        rule_version=rule_version,
        confidence=confidence,
        spans=tuple(spans),
    )


def _conflict_warning(
    field_name: str,
    text: str,
    matches: Sequence[re.Match[str]],
) -> ExtractionWarning:
    return ExtractionWarning(
        code=ExtractionWarningCode.CONFLICTING_VALUES,
        field_name=field_name,
        spans=tuple(_trimmed_span(text, match) for match in matches),
    )


def _invalid_range_warning(
    field_name: str,
    text: str,
    match: re.Match[str],
) -> ExtractionWarning:
    return ExtractionWarning(
        code=ExtractionWarningCode.INVALID_RANGE,
        field_name=field_name,
        spans=(_trimmed_span(text, match),),
    )
