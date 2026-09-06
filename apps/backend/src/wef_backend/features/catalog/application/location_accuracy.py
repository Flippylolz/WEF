"""Backend-owned location uncertainty, independent of offer completeness."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

POINT_PRECISIONS = ("building", "street")
_HIGH_CONFIDENCE = Decimal("0.90")


class EffectivePrecision(StrEnum):
    """Honest display categories; an area is never a precise point."""

    BUILDING = "building"
    STREET = "street"
    AREA = "area"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class LocationAccuracy:
    """Public policy projection, not a probability or fresh geometry verification."""

    precision: EffectivePrecision
    validation_status: str
    uncertainty_reason: str | None
    label: str


def project_location_accuracy(
    *,
    precision: str,
    review_status: str,
    confidence: Decimal,
    has_point: bool,
) -> LocationAccuracy:
    """Translate persisted review/precision into consistent public semantics."""
    if precision in {"district", "city"}:
        return LocationAccuracy(
            EffectivePrecision.AREA, review_status, "area_only", "Approximate area"
        )
    if review_status != "accepted" or not has_point or precision not in POINT_PRECISIONS:
        return LocationAccuracy(
            EffectivePrecision.UNRESOLVED,
            review_status,
            "location_not_validated",
            "Location unresolved",
        )
    if precision == "street":
        return LocationAccuracy(
            EffectivePrecision.STREET, review_status, "street_only", "Approximate street location"
        )
    return LocationAccuracy(
        EffectivePrecision.BUILDING,
        review_status,
        "low_location_confidence" if confidence < _HIGH_CONFIDENCE else None,
        "Building location",
    )
