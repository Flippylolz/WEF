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


def test_extraction_does_not_mutate_source_and_versions_are_explicit() -> None:
    """Repeated versions leave raw text/payload/checksum byte semantics untouched."""
    message = _message("Kupno | Mieszkanie\nCena: 123 456 PLN\nPokoje: 2")
    before = (message.text, message.raw_payload, message.checksum)

    custom = extract_listing(message, parser_version="e2-test-version")

    assert (message.text, message.raw_payload, message.checksum) == before
    assert custom.decision.parser_version == "e2-test-version"
    assert custom.listing is not None
    assert custom.listing.parser_version == "e2-test-version"
    assert all(
        signal.provenance.rule_version == "e2-test-version" for signal in custom.decision.signals
    )


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
