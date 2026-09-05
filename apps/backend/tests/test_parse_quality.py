"""Recovery eligibility and safe benchmark coverage beyond parser warnings."""

from __future__ import annotations

# ruff: noqa: RUF001 - intentional multilingual source-equivalent fixtures
import json
from dataclasses import replace

import pytest

from tests.parser_benchmark import FIXTURE, evaluate
from tests.test_listing_extraction import _message
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parse_quality import (
    ParseClassification,
    classify_parse,
)


def test_silent_labeled_price_miss_is_eligible_without_a_warning() -> None:
    text = "Продажа: квартира\nЦена апартамента: 780 000 PLN\nПлощадь: 37.50 m²"
    result = extract_listing(_message(text))
    assert not result.warnings
    assert result.listing is not None
    assert result.listing.apartment_price is None
    quality = classify_parse(text, result)
    assert quality.recovery_eligible
    field = next(field for field in quality.fields if field.field_name == "apartment_price")
    assert field.classification is ParseClassification.EXTRACTION_MISS
    assert field.spans[0].extract(text) == "780 000 PLN"


@pytest.mark.parametrize(
    "text", ["", "Photo album", "Service message", "Usługi: remont", "Привет!", "Area: 12 m²"]
)
def test_non_listing_content_does_not_enter_recovery(text: str) -> None:
    quality = classify_parse(text, extract_listing(_message(text)))
    assert not quality.recovery_eligible
    assert quality.classification in {
        ParseClassification.EXPECTED_NON_OFFER,
        ParseClassification.UNCLASSIFIED,
    }


def test_source_absent_is_distinct_from_unrecognized_prose() -> None:
    text = "Sprzedam mieszkanie\nCena: nie podano"
    quality = classify_parse(text, extract_listing(_message(text)))
    price = next(field for field in quality.fields if field.field_name == "apartment_price")
    assert price.classification is ParseClassification.SOURCE_ABSENT
    assert not quality.recovery_eligible
    area = next(field for field in quality.fields if field.field_name == "area_sqm")
    assert area.classification is ParseClassification.UNCLASSIFIED


def test_contradictions_are_not_automatically_repairable() -> None:
    text = "For sale: apartment\nRooms: 2\nRooms: 4"
    result = extract_listing(_message(text))
    assert result.warnings
    quality = classify_parse(text, result)
    assert quality.classification is ParseClassification.CONFLICTING
    assert not quality.recovery_eligible


def test_included_storage_gap_is_classified_as_inclusion_not_money() -> None:
    text = "Продажа: квартира\nКладовая: входит в цену"
    quality = classify_parse(text, extract_listing(_message(text)))
    storage = next(
        field for field in quality.fields if field.field_name == "storage_included_in_price"
    )
    assert storage.classification is ParseClassification.EXTRACTION_MISS
    assert quality.recovery_eligible


def test_candidate_detection_miss_can_still_have_listing_evidence() -> None:
    text = "Sprzedam mieszkanie\nParking: 45 000 PLN"
    result = extract_listing(_message(text))
    assert not result.decision.is_candidate
    quality = classify_parse(text, result)
    assert quality.classification is ParseClassification.EXTRACTION_MISS
    assert quality.recovery_eligible


def test_clean_parse_has_no_recovery_work() -> None:
    text = "For sale: studio apartment\nPrice: 700 000 PLN\nArea: 50 m²\nRooms: 2"
    quality = classify_parse(text, extract_listing(_message(text)))
    assert not quality.recovery_eligible
    assert quality.classification is ParseClassification.COMPLETE


def test_benchmark_labels_have_valid_source_offsets_and_negative_denominators() -> None:
    corpus = json.loads(FIXTURE.read_text())
    cases = corpus["cases"]
    assert len(cases) >= 60
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert sum(not case["candidate"] for case in cases) >= 15
    assert {case["language"] for case in cases} >= {"pl", "ru", "uk", "en"}
    for case in cases:
        assert case["provenance"].startswith(("invented", "audit-derived invented"))
        for label in case["expected"].values():
            if label["presence"] == "evidenced":
                assert label["value"] is not None
                assert label["spans"]
            for span in label["spans"]:
                assert 0 <= span["start"] < span["end"] <= len(case["text"])
        if not case["candidate"]:
            assert not classify_parse(
                case["text"], extract_listing(_message(case["text"]))
            ).recovery_eligible


def test_benchmark_exposes_known_gaps_and_rejects_new_regressions() -> None:
    baseline = json.loads(FIXTURE.with_name("parser-quality-v1-baseline.json").read_text())
    report, failures = evaluate()
    assert failures <= set(baseline["known_failures"])
    assert report["candidate"]["fp"] == 0
    assert report["candidate"]["fn"] <= baseline["report"]["candidate"]["fn"]
    assert report["fields"]["apartment_price"]["evidenced"] > 0


def test_inconsistent_warning_field_does_not_invent_source_evidence() -> None:
    text = "For sale: apartment\nRooms: 2\nRooms: 4"
    result = extract_listing(_message(text))
    warning = replace(result.warnings[0], field_name="storage_price")
    quality = classify_parse(text, replace(result, warnings=(warning,)))
    assert not quality.recovery_eligible


def test_empty_label_never_borrows_the_following_line() -> None:
    text = "Продажа: квартира\nЦена апартамента:\nПлощадь: 37.50 m²"
    quality = classify_parse(text, extract_listing(_message(text)))
    price = next(field for field in quality.fields if field.field_name == "apartment_price")
    assert price.classification is ParseClassification.UNCLASSIFIED
    assert not price.spans


def test_implicit_english_property_evidence_exposes_silent_omission() -> None:
    text = "For sale: apartment\nPrice: 700 000 PLN"
    quality = classify_parse(text, extract_listing(_message(text)))
    prop = next(field for field in quality.fields if field.field_name == "property_type")
    assert prop.classification is ParseClassification.EXTRACTION_MISS
    assert prop.spans[0].extract(text) == "apartment"
