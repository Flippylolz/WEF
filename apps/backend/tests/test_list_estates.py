"""Unit tests for the list-estates application query."""

from tests.fakes import FakeEstateQuery
from wef_backend.features.estates.application import EstateRecord, ListEstates
from wef_backend.features.estates.domain import Availability, GeoPoint


async def test_list_estates_computes_label_keys() -> None:
    """Return delivery-neutral DTOs with backend-owned label decisions."""
    query = ListEstates(
        FakeEstateQuery(
            records=(
                EstateRecord(
                    estate_id=7,
                    title="Synthetic riverside flat",
                    location=GeoPoint(longitude=14.4378, latitude=50.0755),
                    availability=Availability.RESERVED,
                ),
            ),
        ),
    )

    result = await query()

    assert result[0].estate_id == 7
    assert result[0].availability_label_key == "estates.availability.reserved"
