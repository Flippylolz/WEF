"""Deterministic E2 listing-candidate detection and typed extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from wef_backend.features.catalog.domain import ContentType, MarketType, PropertyType
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
from wef_backend.features.ingestion.domain.geocoding import (
    canonical_warsaw_district,
    looks_like_warsaw_address,
    warsaw_district_in,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

PARSER_VERSION = "e2-v12"
CANDIDATE_THRESHOLD = 5
_MAX_RANGE_VALUES = 2
_MAX_ROOM_COUNT = 20

_FLAGS = re.IGNORECASE | re.UNICODE
# A number may end only at whitespace/punctuation or directly before a tracked
# currency word (an 850k example: "850 000" + PLN-word suffix), so grouped
# amounts keep their magnitude.
_CURRENCY_WORD = r"(?:злот\w*|złot\w*|zlot\w*)"
_NUMBER = (
    r"(?<!\w)(?:\d{1,3}(?:[ \u00a0]\d{3})+(?:[,.]\d+)?|\d+(?:[,.]\d+)?)"
    r"(?=$|[\s\u00a0.,;:|()\[\]{}»«\"'\u2013\u2014-]|" + _CURRENCY_WORD + r")"
)
_VALUE_SUFFIX = r"\s*(?:[:|]\s*|[\u2013\u2014-]\s+)(?P<value>[^\r\n]+)"
_NUMBER_PATTERN = re.compile(_NUMBER)
_ROOM_SLUG = r"(?:комнат(?:ная|ные|[аы])|кімнат(?:на|ні))"
_ROOM_TAG_PATTERN = re.compile(
    rf"#\s*\d+\s*[_ -]?\s*(?:pokoje?|rooms?|{_ROOM_SLUG})(?!\w)",
    _FLAGS,
)
_ROOM_HYPHEN_PATTERN = re.compile(
    r"\b(?P<rooms>\d+)\s*-\s*(?:комнат(?:ная|ные)|кімнат(?:на|ні))\b",
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
            r"(?:^|\n)\s*(?:[\U0001F3D9\U0001F3E0\U0001F3E1]\ufe0f?\s*)?"
            r"(?:покупка|продажа|купівля|kupno|for sale)\s*[|:\u2013\u2014-]",
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
        re.compile(r"\b(?:cena|price|цен[аы]|стоимость|ціна|вартість)\b", _FLAGS),
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
            rf"(?:#\s*\d+\s*[_ -]?\s*(?:pokoje?|rooms?|{_ROOM_SLUG})(?!\w)"
            r"|\b\d+\s*-\s*(?:комнат(?:ная|ные)|кімнат(?:на|ні))\b"
            r"|\b(?:pokoje?|rooms?|комнат[аы]?|pok\.)\s*"
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
    rf"(?:rynek|market|рынок|ринок){_VALUE_SUFFIX}",
    _FLAGS,
)
# Implicit PRIMARY signals: developer/new-build keywords without an explicit label.
_PRIMARY_IMPLICIT_PATTERN = re.compile(
    r"\b(?:"
    r"новостройк[аи]|новобудов[аи]|нов[аи]?\s+будов[аи]?"  # RU/UA new-build nouns
    r"|від\s+забудовник[аи]"                                 # UA "from developer"
    r"|від\s+завод[аи]?"                                     # UA "from factory" (rare)
    r"|deweloper\w*|inwestycj[ae]|budow[a-z]*\s+nowych"      # PL developer terms
    r"|от\s+застройщик[аи]|застройщик\w*"                    # RU "from developer"
    r"|первичн\w+"                                           # RU "primary" standalone
    r"|pierwot\w+"                                           # PL "primary" standalone
    r"|nowe\s+budownictwo|nowe\s+mieszkan\w+"                # PL new construction
    r")\b",
    _FLAGS,
)
# Implicit SECONDARY signals: resale / pre-owned keywords without an explicit label.
_SECONDARY_IMPLICIT_PATTERN = re.compile(
    r"\b(?:"
    r"вторичн\w+|вторинн\w+"                                 # RU/UA "secondary"
    r"|від\s+власник[аи]|от\s+собственник[аи]"               # UA/RU "from owner"
    r"|od\s+w[łl]a[śs]ciciela"                              # PL "from owner"
    r"|rynek\s+wtórny|wtórn\w+"                              # PL secondary market
    r"|resale|после\s+ремонт[аи]|після\s+ремонт[уа]"         # resale indicators
    r"|kapitaln\w+\s+remont|капитальн\w+\s+ремонт"           # major renovation (resale)
    r"|вже\s+(?:заселен|обжит)|уже\s+(?:заселен|обжит)"     # UA/RU "already occupied"
    r")\b",
    _FLAGS,
)
_PROPERTY_TYPE_LABEL_PATTERN = re.compile(
    rf"(?:typ nieruchomo[śs]ci|property type|rodzaj nieruchomo[śs]ci|"
    rf"тип недвижимости|тип нерухомості){_VALUE_SUFFIX}",
    _FLAGS,
)
_SEMI_DETACHED_PATTERN = re.compile(
    r"\b(?:bli[źz]niak\w*|semi[\s-]?detached|twin\s+house|близнец\w*|близнюк\w*)\b",
    _FLAGS,
)
_APARTMENT_PATTERN = re.compile(
    r"\b(?:mieszkan\w*|apartament\w*|квартир\w*|апартамент\w*|"
    r"studio\s+apartment|studio\s+flat)\b",
    _FLAGS,
)
_HOUSE_PATTERN = re.compile(
    r"\b(?:dom\s+(?:jednorodzinny|wolnostoj\w*)|jednorodzinny|detached\s+house|"
    r"standalone\s+house|частн\w+\s+дом|dom\s+particulier|will[ae]|villa|"
    r"дім\w*|особняк\w*|"
    r"дом\s+(?:на\s+продаж\w*|\u0441\s+садом|под\s+\w+)|"
    r"\d+[\s-]*комнатн\w*\s+дом|"
    r"(?:сімейн\w*|приватн\w*)\s+будинок|"
    r"будинок\s+(?:на\s+продаж\w*|\u0437\s+садом))\b",
    _FLAGS,
)
_LOCATION_PATTERN = re.compile(
    rf"(?:lokalizacja|location|adres|локализаци[яи]|адрес){_VALUE_SUFFIX}",
    _FLAGS,
)
_LOCATION_PIN_LINE_PATTERN = re.compile(
    r"(?m)^[ \t]*\U0001F4CD\ufe0f?[ \t]*(?P<value>[^\r\n]+)",
    _FLAGS,
)
_PIN_FIELD_EMOJI_FLOOR = 0x1F000
_DISTRICT_PATTERN = re.compile(
    rf"(?:dzielnica|district|район){_VALUE_SUFFIX}",
    _FLAGS,
)
_DEVELOPMENT_PATTERN = re.compile(
    rf"(?:inwestycja|development(?: name)?|название проекта|жилой комплекс|жк){_VALUE_SUFFIX}",
    _FLAGS,
)
_APARTMENT_PRICE_PATTERN = re.compile(
    rf"(?:cena(?: mieszkania)?|apartment price|price|цена(?: квартиры)?|стоимость(?: квартиры)?|"
    rf"ціна|вартість)"
    rf"{_VALUE_SUFFIX}",
    _FLAGS,
)
_PARKING_PATTERN = re.compile(
    rf"(?:parking|паркинг|паркінг|miejsce postojowe){_VALUE_SUFFIX}",
    _FLAGS,
)
_STORAGE_PATTERN = re.compile(
    rf"(?:storage|комора|кладов(?:ая|ка)|kom[oó]rka lokatorska){_VALUE_SUFFIX}",
    _FLAGS,
)
_AREA_PATTERN = re.compile(rf"(?:powierzchnia|area|площадь){_VALUE_SUFFIX}", _FLAGS)
_ROOMS_PATTERN = re.compile(
    rf"(?:pokoje?|rooms?|комнат[аы]?|кімнат(?:на|ні)?){_VALUE_SUFFIX}",
    _FLAGS,
)
_FLOOR_PATTERN = re.compile(rf"(?:pi[eę]tro|floor|этаж){_VALUE_SUFFIX}", _FLAGS)
_DELIVERY_PATTERN = re.compile(
    rf"(?:oddanie|delivery|completion|сдача|готовность){_VALUE_SUFFIX}",
    _FLAGS,
)


def detect_candidate(
    message: RawMessage,
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
                            PARSER_VERSION,
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
        parser_version=PARSER_VERSION,
        is_candidate=is_candidate,
        score=score,
        threshold=CANDIDATE_THRESHOLD,
        content_type=_decision_content_type(signals) if is_candidate else None,
        signals=tuple(signals),
    )


def extract_listing(
    message: RawMessage,
) -> ExtractionResult:
    """Detect and extract one listing without mutating its raw evidence."""
    decision = detect_candidate(message)
    if not decision.is_candidate:
        return ExtractionResult(decision=decision, listing=None)

    warnings: list[ExtractionWarning] = []
    content_type = _content_value(decision, warnings)
    market_type = _market_type(message.text, PARSER_VERSION, warnings, content_type)
    property_type = _property_type(message.text, PARSER_VERSION, warnings)
    location = _location_field(message.text, PARSER_VERSION, warnings)
    district = _district_field(message.text, PARSER_VERSION, warnings)
    development_name = _string_field(
        message.text,
        _DEVELOPMENT_PATTERN,
        "development_name",
        PARSER_VERSION,
        warnings,
    )
    apartment_price = _money_field(
        message.text,
        _APARTMENT_PRICE_PATTERN,
        "apartment_price",
        PARSER_VERSION,
        warnings,
    )
    parking_price, parking_included = _addon_fields(
        message.text,
        _PARKING_PATTERN,
        "parking",
        PARSER_VERSION,
        warnings,
    )
    storage_price, storage_included = _addon_fields(
        message.text,
        _STORAGE_PATTERN,
        "storage",
        PARSER_VERSION,
        warnings,
    )
    area = _range_field(
        message.text,
        _AREA_PATTERN,
        "area_sqm",
        PARSER_VERSION,
        warnings,
        _decimal_range,
    )
    rooms = _rooms_field(
        message.text,
        PARSER_VERSION,
        warnings,
    )
    floor = _string_field(message.text, _FLOOR_PATTERN, "floor", PARSER_VERSION, warnings)
    delivery = _string_field(
        message.text,
        _DELIVERY_PATTERN,
        "delivery",
        PARSER_VERSION,
        warnings,
    )
    listing = ListingCandidate(
        source_message_id=message.external_message_id,
        source_checksum=message.checksum,
        parser_version=PARSER_VERSION,
        content_type=content_type,
        market_type=market_type,
        property_type=property_type,
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
        map_links=_map_links(message.text, PARSER_VERSION),
        contacts=_contacts(message.text, PARSER_VERSION),
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
    content_type: ExtractedValue[ContentType] | None = None,
) -> ExtractedValue[MarketType] | None:
    # 1. Explicit label ("rynek: pierwotny", "рынок — вторичный", …) — highest priority.
    explicit = _mapped_string_field(
        text,
        _MARKET_PATTERN,
        "market_type",
        parser_version,
        warnings,
        _parse_market_type,
    )
    if explicit is not None and explicit.value is not MarketType.UNKNOWN:
        return explicit

    # 2. Implicit PRIMARY keywords in the body text.
    primary_match = _PRIMARY_IMPLICIT_PATTERN.search(text)
    if primary_match is not None:
        span = SourceSpan(primary_match.start(), primary_match.end())
        return ExtractedValue(
            value=MarketType.PRIMARY,
            provenance=_provenance(
                "extract.market_type.implicit_primary",
                parser_version,
                Confidence.MEDIUM,
                span,
            ),
        )

    # 3. Implicit SECONDARY keywords in the body text.
    secondary_match = _SECONDARY_IMPLICIT_PATTERN.search(text)
    if secondary_match is not None:
        span = SourceSpan(secondary_match.start(), secondary_match.end())
        return ExtractedValue(
            value=MarketType.SECONDARY,
            provenance=_provenance(
                "extract.market_type.implicit_secondary",
                parser_version,
                Confidence.MEDIUM,
                span,
            ),
        )

    # 4. content_type = DEVELOPMENT strongly implies PRIMARY market.
    # Provenance re-uses the content_type evidence span.
    if (
        content_type is not None
        and content_type.value is ContentType.DEVELOPMENT
        and content_type.provenance.spans
    ):
        return ExtractedValue(
            value=MarketType.PRIMARY,
            provenance=_provenance(
                "extract.market_type.inferred_from_development",
                parser_version,
                Confidence.MEDIUM,
                content_type.provenance.spans[0],
            ),
        )

    return explicit  # None or UNKNOWN from explicit match


def _property_type(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[PropertyType] | None:
    """Classify property kind from explicit multilingual source phrases."""
    labeled = _property_type_labeled_field(text, parser_version, warnings)
    if labeled is not None:
        return labeled

    categories: dict[PropertyType, SourceSpan] = {}
    for pattern, ptype in (
        (_SEMI_DETACHED_PATTERN, PropertyType.SEMI_DETACHED),
        (_APARTMENT_PATTERN, PropertyType.APARTMENT),
        (_HOUSE_PATTERN, PropertyType.HOUSE),
    ):
        match = pattern.search(text)
        if match is not None and ptype not in categories:
            categories[ptype] = SourceSpan(*match.span())

    if len(categories) > 1:
        warnings.append(
            ExtractionWarning(
                code=ExtractionWarningCode.CONFLICTING_VALUES,
                field_name="property_type",
                spans=tuple(categories.values()),
            ),
        )
        return None
    if not categories:
        return None
    selected = next(iter(categories))
    span = categories[selected]
    return ExtractedValue(
        value=selected,
        provenance=_provenance(
            "extract.property_type",
            parser_version,
            Confidence.HIGH,
            span,
        ),
    )


def _property_type_labeled_field(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[PropertyType] | None:
    """Read one labeled property-type line when present."""
    parsed: list[tuple[PropertyType, SourceSpan]] = []
    for match in _PROPERTY_TYPE_LABEL_PATTERN.finditer(text):
        mapped = _parse_property_type_label(_trimmed_value(text, match))
        if mapped is not None:
            parsed.append((mapped, _trimmed_span(text, match)))
    if not parsed:
        return None
    if len({value for value, _ in parsed}) > 1:
        warnings.append(
            ExtractionWarning(
                code=ExtractionWarningCode.CONFLICTING_VALUES,
                field_name="property_type",
                spans=tuple(span for _, span in parsed),
            ),
        )
        return None
    value, span = parsed[0]
    return ExtractedValue(
        value=value,
        provenance=_provenance(
            "extract.property_type",
            parser_version,
            Confidence.HIGH,
            span,
        ),
    )


def _parse_property_type_label(value: str) -> PropertyType | None:
    folded = value.casefold()
    if any(token in folded for token in ("bli", "semi", "twin", "близ")):
        return PropertyType.SEMI_DETACHED
    if any(token in folded for token in ("mieszkan", "apart", "flat", "studio", "кварт", "апарт")):
        return PropertyType.APARTMENT
    if any(
        token in folded for token in ("dom", "house", "villa", "willa", "дом", "дім", "особняк")
    ):
        return PropertyType.HOUSE
    return None


def _location_field(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[str] | None:
    """Prefer labeled location lines over the pin-line template."""
    if _LOCATION_PATTERN.search(text) is not None:
        return _string_field(text, _LOCATION_PATTERN, "location", parser_version, warnings)
    return _pin_line_field(
        text,
        "location",
        parser_version,
        warnings,
        lambda value: value if looks_like_warsaw_address(value) else None,
    )


def _district_field(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[str] | None:
    """Prefer labeled district lines over an exact pin-line district segment."""
    if _DISTRICT_PATTERN.search(text) is not None:
        return _district_labeled_field(text, parser_version, warnings)
    return _pin_line_field(
        text,
        "district",
        parser_version,
        warnings,
        warsaw_district_in,
    )


def _district_labeled_field(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[str] | None:
    """Store only reviewed canonical district names from labeled lines."""
    parsed: list[tuple[str, SourceSpan]] = []
    for match in _DISTRICT_PATTERN.finditer(text):
        canonical = canonical_warsaw_district(_trimmed_value(text, match))
        if canonical is not None:
            parsed.append((canonical, _trimmed_span(text, match)))
    if not parsed:
        return None
    if len({value for value, _ in parsed}) > 1:
        warnings.append(
            ExtractionWarning(
                code=ExtractionWarningCode.CONFLICTING_VALUES,
                field_name="district",
                spans=tuple(span for _, span in parsed),
            ),
        )
        return None
    value, span = parsed[0]
    return ExtractedValue(
        value=value,
        provenance=_provenance(
            "extract.district",
            parser_version,
            Confidence.HIGH,
            span,
        ),
    )


def _pin_line_field[T](
    text: str,
    field_name: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
    read_value: Callable[[str], T | None],
) -> ExtractedValue[T] | None:
    """Read one field from pin-prefixed template lines the labels cannot cover."""
    parsed: list[tuple[T, SourceSpan]] = []
    for match in _LOCATION_PIN_LINE_PATTERN.finditer(text):
        value, span = _pin_line_value(text, match)
        mapped = read_value(value) if value else None
        if mapped is not None:
            parsed.append((mapped, span))
    if not parsed:
        return None
    if len({item for item, _ in parsed}) > 1:
        warnings.append(
            ExtractionWarning(
                code=ExtractionWarningCode.CONFLICTING_VALUES,
                field_name=field_name,
                spans=tuple(span for _, span in parsed),
            ),
        )
        return None
    selected, selected_span = parsed[0]
    return ExtractedValue(
        value=selected,
        provenance=_provenance(
            f"extract.{field_name}_pin",
            parser_version,
            Confidence.MEDIUM,
            selected_span,
        ),
    )


def _pin_line_value(text: str, match: re.Match[str]) -> tuple[str, SourceSpan]:
    start, end = match.span("value")
    end = min(
        (index for index in range(start, end) if ord(text[index]) >= _PIN_FIELD_EMOJI_FLOOR),
        default=end,
    )
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    while end > start and text[end - 1] in ",|":
        end -= 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end], SourceSpan(start, end)


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
        amount = _money_amount_range(value)
        if amount is None:
            if _NUMBER_PATTERN.search(value):
                warnings.append(_invalid_range_warning(field_name, text, match))
            continue
        currency = _money_currency(value)
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


def _append_hyphenated_room_tags(
    matches: tuple[re.Match[str], ...],
    *,
    warnings: list[ExtractionWarning],
) -> list[tuple[IntegerRange, SourceSpan]]:
    """Parse N-комнатная room labels into bounded integer ranges."""
    parsed: list[tuple[IntegerRange, SourceSpan]] = []
    for match in matches:
        room = int(match.group("rooms"))
        span = SourceSpan(*match.span())
        if not 0 < room <= _MAX_ROOM_COUNT:
            warnings.append(
                ExtractionWarning(
                    code=ExtractionWarningCode.INVALID_RANGE,
                    field_name="rooms",
                    spans=(span,),
                )
            )
            continue
        parsed.append((IntegerRange(lower=room, upper=room), span))
    return parsed


def _rooms_field(
    text: str,
    parser_version: str,
    warnings: list[ExtractionWarning],
) -> ExtractedValue[IntegerRange] | None:
    labeled_matches = tuple(_ROOMS_PATTERN.finditer(text))
    tag_matches = tuple(_ROOM_TAG_PATTERN.finditer(text))
    hyphen_matches = tuple(_ROOM_HYPHEN_PATTERN.finditer(text))
    parsed: list[tuple[IntegerRange, SourceSpan]] = []
    for match in labeled_matches:
        value = _trimmed_value(text, match)
        if _is_room_tag_list(value):
            continue
        room_range = _room_range(value)
        if room_range is None:
            warnings.append(_invalid_range_warning("rooms", text, match))
            continue
        parsed.append((room_range, _trimmed_span(text, match)))

    valid_tag_ranges: list[tuple[IntegerRange, SourceSpan]] = []
    for match in tag_matches:
        room_range = _room_tag_range(match.group())
        span = SourceSpan(*match.span())
        if room_range is None:
            warnings.append(
                ExtractionWarning(
                    code=ExtractionWarningCode.INVALID_RANGE,
                    field_name="rooms",
                    spans=(span,),
                )
            )
            continue
        valid_tag_ranges.append((room_range, span))
    valid_tag_ranges.extend(
        _append_hyphenated_room_tags(hyphen_matches, warnings=warnings),
    )
    if valid_tag_ranges:
        parsed.append(
            (
                IntegerRange(
                    lower=min(value.lower for value, _ in valid_tag_ranges),
                    upper=max(value.upper for value, _ in valid_tag_ranges),
                ),
                valid_tag_ranges[0][1],
            )
        )

    if not parsed:
        return None
    distinct = {value for value, _ in parsed}
    spans = tuple(
        dict.fromkeys(
            (
                *(span for _, span in parsed),
                *(span for _, span in valid_tag_ranges),
            )
        )
    )
    if len(distinct) > 1:
        warnings.append(
            ExtractionWarning(
                code=ExtractionWarningCode.CONFLICTING_VALUES,
                field_name="rooms",
                spans=spans,
            )
        )
        return None
    selected_range = parsed[0][0]
    return ExtractedValue(
        value=selected_range,
        provenance=_provenance(
            "extract.rooms",
            parser_version,
            Confidence.HIGH,
            *spans,
        ),
    )


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
    """Keep the first priced fragment when add-ons are appended with plus separators."""
    parts = re.split(r"\s+\+\s+", value, maxsplit=1)
    return parts[0] if parts else value


def _money_amount_range(value: str) -> DecimalRange | None:
    value = _primary_money_fragment(value)
    context_spans = tuple(match.span() for match in _PER_AREA_CONTEXT_PATTERN.finditer(value))
    amount_matches = tuple(
        match
        for match in _NUMBER_PATTERN.finditer(value)
        if not any(start <= match.start() and match.end() <= end for start, end in context_spans)
    )
    if not 0 < len(amount_matches) <= _MAX_RANGE_VALUES or any(
        start < amount_matches[-1].end() for start, _ in context_spans
    ):
        return None
    amount_text = " ".join(match.group() for match in amount_matches)
    if len(amount_matches) == _MAX_RANGE_VALUES:
        separator = value[amount_matches[0].end() : amount_matches[1].start()]
        amount_text = f"{amount_matches[0].group()}{separator}{amount_matches[1].group()}"
    return _decimal_range(amount_text)


def _money_currency(value: str) -> str | None:
    value = _primary_money_fragment(value)
    context = _PER_AREA_CONTEXT_PATTERN.search(value)
    primary_value = value[: context.start()] if context is not None else value
    return _currency(primary_value)


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


_REMAINING_DIGIT_RUN = re.compile(r"\d(?:[\s-]?\d){8,}")


def extract_contact_spans(text: str) -> tuple[ContactSpan, ...]:
    """Return parser-owned contact spans for one source description."""
    return _contacts(text, PARSER_VERSION)


def source_text_contains_unmasked_contacts(text: str) -> bool:
    """Return True when phone/handle-like material remains after masking."""
    if _PHONE_PATTERN.search(text) is not None or _TELEGRAM_PATTERN.search(text) is not None:
        return True
    return _REMAINING_DIGIT_RUN.search(text) is not None


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
