"""Candidate detection and typed E2 extraction tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from wef_backend.features.catalog.domain import ContentType, MarketType
from wef_backend.features.ingestion.application import (
    CANDIDATE_THRESHOLD,
    PARSER_VERSION,
    detect_candidate,
    extract_listing,
)
from wef_backend.features.ingestion.domain import (
    CandidateDecision,
    CandidateReason,
    CandidateSignal,
    Confidence,
    ContactKind,
    DecimalRange,
    ExtractionResult,
    ExtractionWarningCode,
    IntegerRange,
    LinkKind,
    MoneyRange,
    RawMessage,
    RuleProvenance,
    SourceIdentity,
    SourcePlatform,
    SourceSpan,
    canonical_json_checksum,
    freeze_json,
)

FIXTURE = Path(__file__).parent / "fixtures" / "telegram_export" / "sanitized-extraction-cases.json"


def _message(text: str, *, message_type: str = "message") -> RawMessage:
    payload = {"id": 501, "type": message_type, "text": text}
    frozen = freeze_json(payload)
    assert isinstance(frozen, Mapping)
    return RawMessage(
        source=SourceIdentity(
            platform=SourcePlatform.TELEGRAM,
            channel_id="fixture-extraction",
            channel_name="Extraction Fixture",
            channel_type="public_channel",
        ),
        external_message_id=501,
        reply_to_message_id=None,
        published_at=datetime(2031, 1, 2, 3, 4, tzinfo=UTC),
        edited_at=None,
        message_type=message_type,
        text=text,
        original_text=text,
        text_entities=(),
        media=(),
        raw_payload=frozen,
        checksum=canonical_json_checksum(payload),
    )


def _candidate(text: str) -> ExtractionResult:
    result = extract_listing(_message(text))
    assert result.listing is not None
    return result


def test_sanitized_extraction_cases_match_expected_primary_types() -> None:
    """Reviewed multilingual positives and negatives remain deterministic."""
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    for case in document["cases"]:
        first = extract_listing(_message(case["text"]))
        second = extract_listing(_message(case["text"]))

        assert first == second
        assert first.decision.parser_version == PARSER_VERSION
        assert first.decision.threshold == CANDIDATE_THRESHOLD
        assert first.decision.is_candidate is case["candidate"]
        assert (first.listing is not None) is case["candidate"]
        if first.listing is None:
            assert case["content_type"] is None
            continue
        content = first.listing.content_type
        market = first.listing.market_type
        price = first.listing.apartment_price
        assert (content.value.value if content else None) == case["content_type"]
        assert (market.value.value if market else None) == case["market_type"]
        assert (price.value.currency if price else None) == case["currency"]


def test_development_extracts_complete_typed_ranges_and_exact_spans() -> None:
    """Development fields retain scalar/range semantics and source evidence."""
    text = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]["text"]
    result = _candidate(text)
    listing = result.listing
    assert listing is not None

    assert result.decision.content_type is ContentType.DEVELOPMENT
    assert listing.content_type is not None
    assert listing.content_type.value is ContentType.DEVELOPMENT
    assert listing.market_type is not None
    assert listing.market_type.value is MarketType.PRIMARY
    assert listing.location is not None
    assert listing.location.value == "ul. Przykładowa 1, Miasto Testowe"
    assert listing.district is not None
    assert listing.district.value == "Wola"
    assert listing.development_name is not None
    assert listing.development_name.value == "Synthetic Riverside"
    assert listing.apartment_price is not None
    assert listing.apartment_price.value == MoneyRange(
        DecimalRange(Decimal(650_000), Decimal(810_000)),
        "PLN",
    )
    assert listing.parking_price is not None
    assert listing.parking_price.value.amount == DecimalRange(Decimal(45_000), Decimal(45_000))
    assert listing.storage_price is None
    assert listing.storage_included_in_price is not None
    assert listing.storage_included_in_price.value is True
    assert listing.area_sqm is not None
    assert listing.area_sqm.value == DecimalRange(Decimal("40.5"), Decimal("62.25"))
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(2, 3)
    assert listing.floor is not None
    assert listing.floor.value == "1-5"
    assert listing.delivery is not None
    assert listing.delivery.value == "Q4 2028"
    assert len(listing.map_links) == 1
    assert listing.map_links[0].kind is LinkKind.GOOGLE_MAPS
    assert listing.map_links[0].span.extract(text) == listing.map_links[0].url
    assert result.warnings == ()

    extracted = (
        listing.content_type,
        listing.market_type,
        listing.location,
        listing.district,
        listing.development_name,
        listing.apartment_price,
        listing.parking_price,
        listing.storage_included_in_price,
        listing.area_sqm,
        listing.rooms,
        listing.floor,
        listing.delivery,
    )
    for field in extracted:
        assert field is not None
        for span in field.provenance.spans:
            assert span.extract(text)
        assert field.provenance.rule_version == PARSER_VERSION


def test_unit_extracts_non_pln_scalar_values() -> None:
    """Cyrillic unit templates preserve explicit non-PLN currency."""
    text = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][1]["text"]
    result = _candidate(text)
    listing = result.listing
    assert listing is not None

    assert listing.content_type is not None
    assert listing.content_type.value is ContentType.UNIT
    assert listing.market_type is not None
    assert listing.market_type.value is MarketType.SECONDARY
    assert listing.apartment_price is not None
    assert listing.apartment_price.value == MoneyRange(
        DecimalRange(Decimal(125_000), Decimal(125_000)),
        "EUR",
    )
    assert listing.area_sqm is not None
    assert listing.area_sqm.value == DecimalRange(Decimal("37.5"), Decimal("37.5"))
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(2, 2)
    assert listing.floor is not None
    assert listing.floor.value == "4"


def test_pin_line_location_extracts_template_address_without_labels() -> None:
    """Live template pin lines yield location and district when labels are absent."""
    text = (
        "🏙 Апартамент в центре Варшавы | Варшава\n"
        "\n"
        "📍ul. Chmielna, Śródmieście, Warszawa\n"
        "📐 2 комнаты | 5 этаж | 44 м2\n"
        "\n"
        "💸 Цена квартиры — 1 800 000 zł"
    )
    result = _candidate(text)
    listing = result.listing
    assert listing is not None

    assert listing.location is not None
    assert listing.location.value == "ul. Chmielna, Śródmieście, Warszawa"
    assert listing.location.provenance.rule_id == "extract.location_pin"
    assert listing.location.provenance.rule_version == PARSER_VERSION
    assert listing.location.provenance.confidence is Confidence.MEDIUM
    for span in listing.location.provenance.spans:
        assert span.extract(text) == "ul. Chmielna, Śródmieście, Warszawa"
    assert listing.district is not None
    assert listing.district.value == "Śródmieście"
    assert listing.district.provenance.rule_id == "extract.district_pin"


def test_pin_line_variants_and_inline_field_boundaries() -> None:
    """City-first, pipe-separated, and inline area fields all stay bounded."""
    city_first = _candidate(
        "Покупка | Квартира\n📍 Варшава, Wola, ul. Stańczyka\nЦена: 850 000 zł",  # noqa: RUF001
    )
    assert city_first.listing is not None
    assert city_first.listing.location is not None
    assert city_first.listing.location.value == "Варшава, Wola, ul. Stańczyka"
    assert city_first.listing.district is not None
    assert city_first.listing.district.value == "Wola"

    piped = _candidate("Покупка | Квартира\n📍 Wola | ул. Konstruktorska\nЦена: 850 000 zł")  # noqa: RUF001
    assert piped.listing is not None
    assert piped.listing.location is not None
    assert piped.listing.location.value == "Wola | ул. Konstruktorska"

    merged = _candidate(
        "Покупка | Квартира\n"
        "📍 ul. Przerwana, Włochy, Warszawa 📐 75,48 м² | 3 / 6 этаж\n"
        "Цена: 500 000 zł",
    )
    assert merged.listing is not None
    assert merged.listing.location is not None
    assert merged.listing.location.value == "ul. Przerwana, Włochy, Warszawa"
    assert merged.listing.district is not None
    assert merged.listing.district.value == "Włochy"


def test_pin_line_rejects_prose_headers_and_out_of_scope_localities() -> None:
    """Section headers, marketing prose, and non-Warsaw localities stay null."""
    header = _candidate(
        "Покупка | Квартира\n"
        "📍 Локация:\n"
        "Śródmieście — главный деловой и lifestyle-центр Варшавы.\n"
        "Цена: 500 000 zł",
    )
    assert header.listing is not None
    assert header.listing.location is None
    assert header.listing.district is None

    out_of_scope = _candidate(
        "Покупка | Квартира\n📍 Dosin, гмина Serock, Мазовецкое воеводство\nЦена: 500 000 zł",  # noqa: RUF001
    )
    assert out_of_scope.listing is not None
    assert out_of_scope.listing.location is None

    prose = _candidate("Покупка | Квартира\n📍 Идеальная локация — тихо и уютно\nЦена: 500 000 zł")  # noqa: RUF001
    assert prose.listing is not None
    assert prose.listing.location is None


def test_labeled_location_wins_and_conflicting_pin_lines_stay_null() -> None:
    """Labeled evidence keeps precedence; divergent pin lines warn instead of choosing."""
    labeled = _candidate(
        "Покупка | Квартира\n📍Локализация: ul. Łodygowa, Targówek, Варшава\nЦена: 500 000 zł",  # noqa: RUF001
    )
    assert labeled.listing is not None
    assert labeled.listing.location is not None
    assert labeled.listing.location.value == "ul. Łodygowa, Targówek, Варшава"
    assert labeled.listing.location.provenance.rule_id == "extract.location"
    assert labeled.listing.location.provenance.confidence is Confidence.HIGH

    text = "Покупка | Квартира\n📍 ul. Pierwsza, Warszawa\n📍 ul. Druga, Warszawa\nЦена: 500 000 zł"  # noqa: RUF001
    conflict = _candidate(text)
    assert conflict.listing is not None
    assert conflict.listing.location is None
    assert [(warning.code, warning.field_name) for warning in conflict.warnings] == [
        (ExtractionWarningCode.CONFLICTING_VALUES, "location")
    ]
    for warning in conflict.warnings:
        assert all(span.extract(text) for span in warning.spans)


def test_currency_word_prices_keep_grouped_magnitude() -> None:
    """Tracked currency words may abut the number without truncating it."""
    samples = (
        "Покупка | Квартира\n💸Цена:850 000злотых",  # noqa: RUF001
        "Покупка | Квартира\nЦена: 850000 злотых",  # noqa: RUF001
        "For sale | Apartment\nPrice: 850 000 złotych",
    )
    for text in samples:
        result = _candidate(text)
        listing = result.listing
        assert listing is not None
        assert listing.apartment_price is not None
        assert listing.apartment_price.value == MoneyRange(
            DecimalRange(Decimal(850_000), Decimal(850_000)),
            "PLN",
        )
        assert listing.apartment_price.provenance.rule_version == PARSER_VERSION


def test_per_area_only_currency_word_price_stays_reviewable() -> None:
    """A currency-word per-area price alone never invents a total."""
    result = _candidate("Покупка | Квартира\nЦена: 12 000злотых за m²")  # noqa: RUF001
    assert result.listing is not None
    assert result.listing.apartment_price is None
    assert [(warning.code, warning.field_name) for warning in result.warnings] == [
        (ExtractionWarningCode.INVALID_RANGE, "apartment_price")
    ]

    untracked = _candidate("For sale | Apartment\nPrice: 500 000 groszy")
    assert untracked.listing is not None
    assert untracked.listing.apartment_price is not None
    assert untracked.listing.apartment_price.value.currency is None
    assert ExtractionWarningCode.UNKNOWN_CURRENCY in {
        warning.code for warning in untracked.warnings
    }


def test_labeled_districts_store_canonical_vocabulary_only() -> None:
    """Labeled district lines reroute reviewed variants and drop unreviewed text."""
    rerouted = _candidate(
        "Inwestycja | Synthetic\nDzielnica: Praga Po\u0142Udnie\nCena: 500 000 PLN",
    )
    assert rerouted.listing is not None
    assert rerouted.listing.district is not None
    assert rerouted.listing.district.value == "Praga-Po\u0142udnie"
    assert rerouted.listing.district.provenance.rule_id == "extract.district"
    assert rerouted.listing.district.provenance.confidence is Confidence.HIGH

    typo = _candidate(
        "Inwestycja | Synthetic\nDzielnica: Bia\u0142O\u0142\u0119Cka\nCena: 500 000 PLN"
    )
    assert typo.listing is not None
    assert typo.listing.district is not None
    assert typo.listing.district.value == "Bia\u0142o\u0142\u0119ka"

    unreviewed = _candidate("Inwestycja | Synthetic\nDzielnica: Mordor\nCena: 500 000 PLN")
    assert unreviewed.listing is not None
    assert unreviewed.listing.district is None
    assert unreviewed.listing.location is None


def test_unknown_currency_remains_null_and_reviewable() -> None:
    """An unlabeled amount never silently becomes PLN."""
    text = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][2]["text"]
    result = _candidate(text)
    listing = result.listing
    assert listing is not None
    assert listing.apartment_price is not None
    assert listing.apartment_price.value.currency is None
    assert ExtractionWarningCode.UNKNOWN_CURRENCY in {warning.code for warning in result.warnings}


def test_conflicting_values_and_content_types_remain_null() -> None:
    """Equal-authority conflicts emit review warnings rather than choices."""
    text = (
        "Inwestycja | Synthetic\n"
        "Покупка | Квартира\n"
        "Lokalizacja: Test A\n"
        "Lokalizacja: Test B\n"
        "Cena: 500 000 PLN\n"
        "Cena: 600 000 PLN"
    )
    result = _candidate(text)
    listing = result.listing
    assert listing is not None

    assert result.decision.content_type is None
    assert listing.content_type is None
    assert listing.location is None
    assert listing.apartment_price is None
    assert {warning.code for warning in result.warnings} == {
        ExtractionWarningCode.CONFLICTING_CONTENT_TYPE,
        ExtractionWarningCode.CONFLICTING_VALUES,
    }
    for warning in result.warnings:
        assert all(span.extract(text) for span in warning.spans)


def test_ambiguous_strong_headers_without_location_remain_reviewable() -> None:
    """No source-template tiebreak is invented when strong headers conflict."""
    result = _candidate("Development opportunity\nFor sale | Apartment\nCena: 500 000 PLN")
    listing = result.listing
    assert listing is not None
    assert listing.content_type is None
    assert result.decision.content_type is None
    assert [warning.code for warning in result.warnings] == [
        ExtractionWarningCode.CONFLICTING_CONTENT_TYPE
    ]


def test_source_shaped_prices_and_room_hashtags_preserve_typed_ranges() -> None:
    """Per-area context is not mistaken for a range and room tags remain typed."""
    scalar = _candidate(
        "Покупка | Квартира\n"
        "Цена: 700 000 PLN (14 000 PLN/m²)\n"
        "Комнаты: #1_комната #2_комнаты #3_комнаты"
    )
    scalar_listing = scalar.listing
    assert scalar_listing is not None
    assert scalar_listing.apartment_price is not None
    assert scalar_listing.apartment_price.value.amount == DecimalRange(
        Decimal(700_000),
        Decimal(700_000),
    )
    assert scalar_listing.rooms is not None
    assert scalar_listing.rooms.value == IntegerRange(1, 3)

    ranged = _candidate(
        "Inwestycja | Synthetic\n"
        "Lokalizacja: Miasto Testowe\n"
        "Cena: 650 000-810 000 PLN (12 500 PLN/m²)"
    )
    ranged_listing = ranged.listing
    assert ranged_listing is not None
    assert ranged_listing.apartment_price is not None
    assert ranged_listing.apartment_price.value.amount == DecimalRange(
        Decimal(650_000),
        Decimal(810_000),
    )

    unknown_primary_currency = _candidate("For sale | Apartment\nPrice: 500000 (14 000 PLN/m²)")
    unknown_listing = unknown_primary_currency.listing
    assert unknown_listing is not None
    assert unknown_listing.apartment_price is not None
    assert unknown_listing.apartment_price.value.currency is None
    assert [
        (warning.code, warning.field_name) for warning in unknown_primary_currency.warnings
    ] == [(ExtractionWarningCode.UNKNOWN_CURRENCY, "apartment_price")]

    tagged = _candidate("For sale | Apartment\nPrice: 500 000 PLN\n#1_room #2_rooms #4_rooms")
    tagged_listing = tagged.listing
    assert tagged_listing is not None
    assert tagged_listing.rooms is not None
    assert tagged_listing.rooms.value == IntegerRange(1, 4)


@pytest.mark.parametrize(
    "value",
    [
        "2.5",
        "4-2",
        "2-25",
        "2-3-4",
        "#2_roommate",
    ],
)
def test_malformed_labeled_room_values_are_not_invented(value: str) -> None:
    """Only bounded ordered integer scalar/range room labels are accepted."""
    result = _candidate(f"For sale | Apartment\nPrice: 500 000 PLN\nRooms: {value}")
    listing = result.listing
    assert listing is not None
    assert listing.rooms is None
    assert [(warning.code, warning.field_name) for warning in result.warnings] == [
        (ExtractionWarningCode.INVALID_RANGE, "rooms")
    ]


def test_room_conflicts_and_invalid_matches_remain_reviewable() -> None:
    """Divergent values stay null and invalid labels survive alongside valid values."""
    conflicting = _candidate("For sale | Apartment\nPrice: 500 000 PLN\nRooms: 2\nRooms: 3")
    assert conflicting.listing is not None
    assert conflicting.listing.rooms is None
    assert [(warning.code, warning.field_name) for warning in conflicting.warnings] == [
        (ExtractionWarningCode.CONFLICTING_VALUES, "rooms")
    ]

    mixed = _candidate("For sale | Apartment\nPrice: 500 000 PLN\nRooms: 2\nRooms: 2.5")
    assert mixed.listing is not None
    assert mixed.listing.rooms is not None
    assert mixed.listing.rooms.value == IntegerRange(2, 2)
    assert [(warning.code, warning.field_name) for warning in mixed.warnings] == [
        (ExtractionWarningCode.INVALID_RANGE, "rooms")
    ]

    label_and_tag = _candidate("For sale | Apartment\nPrice: 500 000 PLN\nRooms: 2\n#3_rooms")
    assert label_and_tag.listing is not None
    assert label_and_tag.listing.rooms is None
    assert [(warning.code, warning.field_name) for warning in label_and_tag.warnings] == [
        (ExtractionWarningCode.CONFLICTING_VALUES, "rooms")
    ]


def test_room_hashtags_require_a_trailing_word_boundary() -> None:
    """A roommate hashtag must not become room-count evidence."""
    result = _candidate("For sale | Apartment\nPrice: 500 000 PLN\n#2_roommate")
    assert result.listing is not None
    assert result.listing.rooms is None
    assert CandidateReason.ROOM_MARKER not in {signal.reason for signal in result.decision.signals}


@pytest.mark.parametrize(
    "value",
    [
        "500 000 PLN 600 000 700 000",
        "500 000-600 000-700 000 PLN",
        "500 000 PLN reference 2026",
        "500 000 PLN (14 000 PLN/m²) reference 2026",
    ],
)
def test_prices_reject_unexplained_extra_numbers(value: str) -> None:
    """Only an explicit per-area amount may be ignored after a total price."""
    result = _candidate(f"For sale | Apartment\nPrice: {value}")
    assert result.listing is not None
    assert result.listing.apartment_price is None
    assert [(warning.code, warning.field_name) for warning in result.warnings] == [
        (ExtractionWarningCode.INVALID_RANGE, "apartment_price")
    ]


def test_invalid_ranges_are_reviewable_and_not_reordered() -> None:
    """Reversed values do not become invented normalized ranges."""
    result = _candidate("Kupno | Mieszkanie\nCena: 800 000-700 000 PLN\nPowierzchnia: 60-40 m2")
    listing = result.listing
    assert listing is not None
    assert listing.apartment_price is None
    assert listing.area_sqm is None
    assert [warning.code for warning in result.warnings].count(
        ExtractionWarningCode.INVALID_RANGE
    ) == 2


def test_synthetic_runtime_contacts_keep_internal_exact_spans() -> None:
    """Contact extraction is tested without committing contact-shaped fixture data."""
    text = "Kupno | Mieszkanie\nCena: 700 000 PLN\nKontakt: +48 600 700 800 lub @fixture_contact"
    result = _candidate(text)
    listing = result.listing
    assert listing is not None

    assert tuple(contact.kind for contact in listing.contacts) == (
        ContactKind.PHONE,
        ContactKind.TELEGRAM,
    )
    assert tuple(contact.span.extract(text) for contact in listing.contacts) == (
        "+48 600 700 800",
        "@fixture_contact",
    )


def test_non_candidates_and_service_records_have_no_derived_listing() -> None:
    """Low-score and non-message input stays accounted for but unparsed."""
    low_score = detect_candidate(_message("Cena: 20 PLN"))
    service = detect_candidate(_message("Kupno | Mieszkanie", message_type="service"))

    assert low_score.is_candidate is False
    assert low_score.score < low_score.threshold
    assert service == CandidateDecision(
        parser_version=PARSER_VERSION,
        is_candidate=False,
        score=0,
        threshold=CANDIDATE_THRESHOLD,
        content_type=None,
        signals=(),
    )
    assert extract_listing(_message("Cena: 20 PLN")).listing is None


def test_extraction_does_not_mutate_source_and_version_is_rule_bound() -> None:
    """Rule provenance cannot be relabeled independently of executable behavior."""
    message = _message("Kupno | Mieszkanie\nCena: 123 456 PLN\nPokoje: 2")
    before = (message.text, message.raw_payload, message.checksum)

    result = extract_listing(message)

    assert (message.text, message.raw_payload, message.checksum) == before
    assert result.decision.parser_version == PARSER_VERSION
    assert result.listing is not None
    assert result.listing.parser_version == PARSER_VERSION
    assert all(
        signal.provenance.rule_version == PARSER_VERSION for signal in result.decision.signals
    )
    with pytest.raises(TypeError, match="parser_version"):
        extract_listing(message, parser_version="misleading-label")  # type: ignore[call-arg]


def test_extraction_domain_values_reject_contradictory_shapes() -> None:
    """Domain invariants reject invalid spans, ranges, provenance, and decisions."""
    with pytest.raises(ValueError, match="source span"):
        SourceSpan(1, 1)
    with pytest.raises(ValueError, match="exceeds"):
        SourceSpan(0, 2).extract("x")
    with pytest.raises(ValueError, match="decimal range"):
        DecimalRange(Decimal(2), Decimal(1))
    with pytest.raises(ValueError, match="integer range"):
        IntegerRange(0, 1)
    with pytest.raises(ValueError, match="currency"):
        MoneyRange(DecimalRange(Decimal(1), Decimal(1)), "zł")
    with pytest.raises(ValueError, match="provenance"):
        RuleProvenance("rule", PARSER_VERSION, Confidence.HIGH, ())

    span = SourceSpan(0, 1)
    provenance = RuleProvenance("rule", PARSER_VERSION, Confidence.HIGH, (span,))
    signal = CandidateSignal(CandidateReason.PRICE_MARKER, 2, provenance)
    with pytest.raises(ValueError, match="score"):
        CandidateDecision(
            parser_version=PARSER_VERSION,
            is_candidate=False,
            score=1,
            threshold=CANDIDATE_THRESHOLD,
            content_type=None,
            signals=(signal,),
        )
    with pytest.raises(ValueError, match="signal weight"):
        replace(signal, weight=0)
    decision = CandidateDecision(
        parser_version=PARSER_VERSION,
        is_candidate=False,
        score=2,
        threshold=CANDIDATE_THRESHOLD,
        content_type=None,
        signals=(signal,),
    )
    with pytest.raises(ValueError, match="only candidate"):
        ExtractionResult(
            decision=decision,
            listing=_candidate("Kupno | Mieszkanie").listing,
        )


def test_stoimost_price_marker_promotes_elestate_format_to_candidate() -> None:
    """Elestate posts label apartment cost as Стоимость rather than Цена."""
    text = (
        "🏡 Квартира на продажу | 64,43 m² | 4 комнаты\n"
        "📐 64,43 m² | 4 комнаты\n"
        "💰 Условия:\n"
        "• Стоимость: 935 374 zł\n"
        "📩 @irynaelestate"
    )
    result = _candidate(text)
    assert result.decision.is_candidate is True
    assert {signal.reason for signal in result.decision.signals} >= {
        CandidateReason.UNIT_MARKER,
        CandidateReason.PRICE_MARKER,
    }
    listing = result.listing
    assert listing is not None
    assert listing.apartment_price is not None
    assert listing.apartment_price.value.amount == DecimalRange(
        Decimal(935374),
        Decimal(935374),
    )


def test_prodazha_header_and_komnatnaya_room_tag_are_candidates() -> None:
    """Secondary-market posts use Продажа headers and #N_комнатная room tags."""
    text = (
        "🏙 Продажа | Вторичный рынок | Варшава\n\n"
        "📍 Район Mokotów | ул. Kwitnących Jabłoni\n\n"
        "🛋 #2_комнатная\n"
        "📐 37,23 м² | 1 этаж из 2\n"
        "Цена: 899 000 zł"
    )
    result = _candidate(text)
    assert result.decision.is_candidate is True
    listing = result.listing
    assert listing is not None
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(2, 2)


def test_hyphenated_komnatnaya_room_count_is_detected() -> None:
    """Some posts omit the # prefix and use N-комнатная instead."""
    text = (
        "🏙 Покупка | Первичный рынок | Варшава\n"
        "📍 ул. Skrajna | район Ząbki\n\n"
        "🛋 4-комнатная\n"
        "📐 88,14 m² | 3 этаж\n"
        "Стоимость: 1 250 000 zł"
    )
    result = _candidate(text)
    assert result.decision.is_candidate is True
    listing = result.listing
    assert listing is not None
    assert listing.rooms is not None
    assert listing.rooms.value == IntegerRange(4, 4)
