"""Canonical catalog values for locations and dated offers."""

from enum import StrEnum


class ContentType(StrEnum):
    """Public offer granularity."""

    DEVELOPMENT = "development"
    UNIT = "unit"


class MarketType(StrEnum):
    """Source market classification."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    UNKNOWN = "unknown"


class OfferVisibility(StrEnum):
    """Publication review state, not real-world availability."""

    VISIBLE = "visible"
    NEEDS_REVIEW = "needs_review"
    HIDDEN = "hidden"


class CoordinatePrecision(StrEnum):
    """Coarse location precision exposed to clients."""

    BUILDING = "building"
    STREET = "street"
    DISTRICT = "district"
    CITY = "city"
    UNKNOWN = "unknown"


class LocationReviewStatus(StrEnum):
    """Review state required before a point is public."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    UNGEOCODED = "ungeocoded"
