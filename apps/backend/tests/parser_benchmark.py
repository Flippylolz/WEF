"""Exact-value benchmark evaluation; emits only aggregate results when invoked."""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from tests.test_listing_extraction import _message
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parse_quality import classify_parse
from wef_backend.features.ingestion.domain.extraction import DecimalRange, IntegerRange, MoneyRange

FIXTURE = Path(__file__).parent / "fixtures/telegram_export/parser-quality-v1.json"


def normalized(value: object) -> object:
    """Compare source units without Decimal representation artifacts."""
    if isinstance(value, MoneyRange):
        return {
            "lower": str(value.amount.lower.normalize()),
            "upper": str(value.amount.upper.normalize()),
            "currency": value.currency,
        }
    if isinstance(value, (DecimalRange, IntegerRange)):
        return [str(Decimal(value.lower).normalize()), str(Decimal(value.upper).normalize())]
    if isinstance(value, Enum):
        return value.value
    return value


def normalize_label(value: object) -> object:
    """Use the same numerical equivalence for reviewed labels."""
    if isinstance(value, dict):
        return {
            **value,
            "lower": str(Decimal(value["lower"]).normalize()),
            "upper": str(Decimal(value["upper"]).normalize()),
        }
    if isinstance(value, list):
        return [str(Decimal(item).normalize()) for item in value]
    return value


def evaluate() -> tuple[dict[str, Any], set[str]]:
    """Return transparent field/candidate denominators and exact failure IDs."""
    corpus = json.loads(FIXTURE.read_text())
    candidate: Counter[str] = Counter(tp=0, fp=0, fn=0, tn=0)
    metrics: dict[str, Counter[str]] = {}
    failures: set[str] = set()
    classifications: Counter[str] = Counter()
    for case in corpus["cases"]:
        extraction = extract_listing(_message(case["text"]))
        quality = classify_parse(case["text"], extraction)
        classifications[quality.classification.value] += 1
        predicted = extraction.decision.is_candidate
        expected = case["candidate"]
        candidate[
            {(True, True): "tp", (True, False): "fp", (False, True): "fn", (False, False): "tn"}[
                predicted, expected
            ]
        ] += 1
        for name, label in case["expected"].items():
            counts = metrics.setdefault(
                name,
                Counter(
                    total=0, unresolved=0, source_absent=0, false_positives=0, evidenced=0, exact=0
                ),
            )
            counts["total"] += 1
            if label["presence"] == "unresolved":
                counts["unresolved"] += 1
                continue
            field = getattr(extraction.listing, name) if extraction.listing else None
            actual = normalized(field.value) if field else None
            value = normalize_label(label["value"])
            if label["presence"] == "absent":
                counts["source_absent"] += 1
                if actual is not None:
                    counts["false_positives"] += 1
            else:
                counts["evidenced"] += 1
                counts["exact"] += int(actual == value)
            if actual != value:
                failures.add(f"{case['case_id']}:{name}")

    def ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    return {
        "version": corpus["version"],
        "cases": len(corpus["cases"]),
        "candidate": {
            **candidate,
            "precision": ratio(candidate["tp"], candidate["tp"] + candidate["fp"]),
            "recall": ratio(candidate["tp"], candidate["tp"] + candidate["fn"]),
        },
        "fields": {
            name: {
                **counts,
                "accuracy": ratio(counts["exact"], counts["evidenced"]),
                "false_positive_rate": ratio(counts["false_positives"], counts["source_absent"]),
                "source_absent_rate": ratio(counts["source_absent"], counts["total"]),
            }
            for name, counts in metrics.items()
        },
        "classifications": dict(classifications),
    }, failures


if __name__ == "__main__":
    print(json.dumps(evaluate()[0], indent=2, sort_keys=True))  # noqa: T201 - aggregate report
