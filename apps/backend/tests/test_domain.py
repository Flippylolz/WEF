"""Unit tests for framework-free estate values."""

import pytest

from wef_backend.features.estates.domain import Availability, GeoPoint


def test_availability_owns_localization_keys() -> None:
    """Keep display decisions in the backend domain."""
    assert Availability.AVAILABLE.label_key == "estates.availability.available"
    assert Availability.RESERVED.label_key == "estates.availability.reserved"


@pytest.mark.parametrize(
    ("longitude", "latitude", "message"),
    [
        (181.0, 0.0, "longitude"),
        (0.0, -91.0, "latitude"),
        (float("nan"), 0.0, "longitude"),
    ],
)
def test_geo_point_rejects_invalid_coordinates(
    longitude: float,
    latitude: float,
    message: str,
) -> None:
    """Reject invalid WGS84 points before they cross a boundary."""
    with pytest.raises(ValueError, match=message):
        GeoPoint(longitude=longitude, latitude=latitude)
