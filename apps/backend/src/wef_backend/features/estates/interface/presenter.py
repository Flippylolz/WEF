"""Pure HTTP presentation mapping for estate DTOs."""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from wef_backend.features.estates.application import EstateDTO
from wef_backend.features.estates.domain import Availability


class CoordinatesResponse(BaseModel):
    """WGS84 coordinates exposed by the API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    longitude: float
    latitude: float


class EstateResponse(BaseModel):
    """Public representation of one synthetic estate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    title: str
    location: CoordinatesResponse
    availability: Availability
    availability_label_key: str


class EstatesResponse(BaseModel):
    """Public list-estates response envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[EstateResponse, ...]


def present_estates(estates: Sequence[EstateDTO]) -> EstatesResponse:
    """Map application DTOs to transport models without domain decisions."""
    return EstatesResponse(
        items=tuple(
            EstateResponse(
                id=estate.estate_id,
                title=estate.title,
                location=CoordinatesResponse(
                    longitude=estate.location.longitude,
                    latitude=estate.location.latitude,
                ),
                availability=estate.availability,
                availability_label_key=estate.availability_label_key,
            )
            for estate in estates
        ),
    )
