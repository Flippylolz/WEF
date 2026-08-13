"""Framework-free estate domain values."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

MIN_LONGITUDE = -180
MAX_LONGITUDE = 180
MIN_LATITUDE = -90
MAX_LATITUDE = 90


class Availability(StrEnum):
    """Availability states understood by every delivery channel."""

    AVAILABLE = "available"
    RESERVED = "reserved"

    @property
    def label_key(self) -> str:
        """Return the backend-owned localization key for this state."""
        match self:
            case Availability.AVAILABLE:
                return "estates.availability.available"
            case Availability.RESERVED:
                return "estates.availability.reserved"


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A WGS84 longitude/latitude pair."""

    longitude: float
    latitude: float

    def __post_init__(self) -> None:
        """Reject coordinates that cannot be represented on Earth."""
        if not isfinite(self.longitude) or not (MIN_LONGITUDE <= self.longitude <= MAX_LONGITUDE):
            message = "longitude must be finite and between -180 and 180"
            raise ValueError(message)
        if not isfinite(self.latitude) or not (MIN_LATITUDE <= self.latitude <= MAX_LATITUDE):
            message = "latitude must be finite and between -90 and 90"
            raise ValueError(message)
