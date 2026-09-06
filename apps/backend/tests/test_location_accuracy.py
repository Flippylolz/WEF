"""Precision labels never equate completeness/provider confidence with accuracy."""

from decimal import Decimal

import pytest

from wef_backend.features.catalog.application.location_accuracy import project_location_accuracy


@pytest.mark.parametrize(
    ("precision", "review", "point", "score", "effective", "reason", "label"),
    [
        ("building", "accepted", True, "0.95", "building", None, "Building location"),
        (
            "building",
            "accepted",
            True,
            "0.60",
            "building",
            "low_location_confidence",
            "Building location",
        ),
        (
            "street",
            "accepted",
            True,
            "0.99",
            "street",
            "street_only",
            "Approximate street location",
        ),
        ("district", "accepted", True, "0.99", "area", "area_only", "Approximate area"),
        ("city", "needs_review", False, "0.99", "area", "area_only", "Approximate area"),
        (
            "building",
            "needs_review",
            True,
            "0.99",
            "unresolved",
            "location_not_validated",
            "Location unresolved",
        ),
        (
            "street",
            "rejected",
            True,
            "0.99",
            "unresolved",
            "location_not_validated",
            "Location unresolved",
        ),
        (
            "building",
            "accepted",
            False,
            "0.99",
            "unresolved",
            "location_not_validated",
            "Location unresolved",
        ),
        (
            "unknown",
            "accepted",
            True,
            "0.99",
            "unresolved",
            "location_not_validated",
            "Location unresolved",
        ),
    ],
)
def test_effective_precision(
    *,
    precision: str,
    review: str,
    point: bool,
    score: str,
    effective: str,
    reason: str | None,
    label: str,
) -> None:
    """Coarse/high-confidence and unreviewed points retain honest semantics."""
    result = project_location_accuracy(
        precision=precision, review_status=review, confidence=Decimal(score), has_point=point
    )
    assert result.precision == effective
    assert result.uncertainty_reason == reason
    assert result.label == label
    assert result.validation_status == review
