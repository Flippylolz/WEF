"""Unit tests for the pure estate presenter."""

from wef_backend.features.estates.application import EstateDTO
from wef_backend.features.estates.domain import Availability, GeoPoint
from wef_backend.features.estates.interface.presenter import present_estates


def test_presenter_only_maps_application_output() -> None:
    """Map DTO fields without recomputing the backend label decision."""
    response = present_estates(
        (
            EstateDTO(
                estate_id=11,
                title="Synthetic garden house",
                location=GeoPoint(longitude=7.4474, latitude=46.948),
                availability=Availability.AVAILABLE,
                availability_label_key="backend.provided.label",
            ),
        ),
    )

    assert response.items[0].availability == "available"
    assert response.items[0].availability_label_key == "backend.provided.label"
