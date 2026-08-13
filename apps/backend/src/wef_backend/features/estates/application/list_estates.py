"""List-estates query and its persistence port."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from wef_backend.features.estates.domain import Availability, GeoPoint


@dataclass(frozen=True, slots=True)
class EstateRecord:
    """Application-owned data shape returned by a query adapter."""

    estate_id: int
    title: str
    location: GeoPoint
    availability: Availability


@dataclass(frozen=True, slots=True)
class EstateDTO:
    """Delivery-neutral output from the list-estates query."""

    estate_id: int
    title: str
    location: GeoPoint
    availability: Availability
    availability_label_key: str


class EstateQueryPort(Protocol):
    """Narrow inward-owned contract for reading estate records."""

    async def list_estate_records(self) -> Sequence[EstateRecord]:
        """Return estate records in deterministic display order."""
        ...


class ListEstates:
    """Decorate persisted records with backend-owned display decisions."""

    def __init__(self, estate_query: EstateQueryPort) -> None:
        """Store the required query port explicitly."""
        self._estate_query = estate_query

    async def __call__(self) -> tuple[EstateDTO, ...]:
        """Return immutable DTOs with backend-computed label keys."""
        records = await self._estate_query.list_estate_records()
        return tuple(
            EstateDTO(
                estate_id=record.estate_id,
                title=record.title,
                location=record.location,
                availability=record.availability,
                availability_label_key=record.availability.label_key,
            )
            for record in records
        )
