"""Backend-owned map filters, query port, and grouped projection service."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.catalog.domain import ContentType, MarketType

_BBOX_COORDINATE_COUNT = 4
_MIN_QUERY_LONGITUDE = 20.5
_MAX_QUERY_LONGITUDE = 21.6
_MIN_QUERY_LATITUDE = 51.8
_MAX_QUERY_LATITUDE = 52.6
_MAX_QUERY_SPAN = 0.8
_MAX_ROOM_VALUES = 10
_MAX_DISTRICT_VALUES = 20


class MapFilterError(ValueError):
    """Raised when filter combinations violate application bounds."""


class ConfidenceIndicator(StrEnum):
    """Coarse public representation of internal coordinate confidence."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Validated map extent in GeoJSON coordinate order."""

    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float

    @classmethod
    def parse(cls, value: str) -> BoundingBox:
        """Parse and validate a bounded Warsaw viewport."""
        try:
            coordinates = tuple(float(part.strip()) for part in value.split(","))
        except ValueError as error:
            message = "bbox must contain four numeric coordinates"
            raise MapFilterError(message) from error
        if len(coordinates) != _BBOX_COORDINATE_COUNT or not all(
            math.isfinite(item) for item in coordinates
        ):
            message = "bbox must contain four finite coordinates"
            raise MapFilterError(message)
        min_lng, min_lat, max_lng, max_lat = coordinates
        if min_lng >= max_lng or min_lat >= max_lat:
            message = "bbox minimum coordinates must precede maximum coordinates"
            raise MapFilterError(message)
        if (
            min_lng < _MIN_QUERY_LONGITUDE
            or max_lng > _MAX_QUERY_LONGITUDE
            or min_lat < _MIN_QUERY_LATITUDE
            or max_lat > _MAX_QUERY_LATITUDE
        ):
            message = "bbox must remain within the Warsaw query boundary"
            raise MapFilterError(message)
        if max_lng - min_lng > _MAX_QUERY_SPAN or max_lat - min_lat > _MAX_QUERY_SPAN:
            message = "bbox exceeds the maximum query span"
            raise MapFilterError(message)
        return cls(
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
        )

    def key(self) -> tuple[float, float, float, float]:
        """Return stable rounded ordinates for request identity."""
        return (
            round(self.min_lng, 6),
            round(self.min_lat, 6),
            round(self.max_lng, 6),
            round(self.max_lat, 6),
        )


@dataclass(frozen=True, slots=True)
class MapFilters:
    """Normalized M1 filters shared by catalog read use cases."""

    bbox: BoundingBox
    price_min: int | None = None
    price_max: int | None = None
    area_min: Decimal | None = None
    area_max: Decimal | None = None
    rooms: tuple[int, ...] = ()
    districts: tuple[str, ...] = ()
    market_types: tuple[MarketType, ...] = ()
    content_types: tuple[ContentType, ...] = ()
    published_from: datetime | None = None
    published_to: datetime | None = None
    quick_filter: str | None = None

    def __post_init__(self) -> None:
        """Reject contradictory ranges and unsafe repeated groups."""
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            message = "price_min must not exceed price_max"
            raise MapFilterError(message)
        if (
            self.area_min is not None
            and self.area_max is not None
            and self.area_min > self.area_max
        ):
            message = "area_min must not exceed area_max"
            raise MapFilterError(message)
        if (
            self.published_from is not None
            and self.published_to is not None
            and self.published_from > self.published_to
        ):
            message = "published_from must not exceed published_to"
            raise MapFilterError(message)
        if self.quick_filter is not None and self.published_from is None:
            message = "quick_filter requires a resolved published_from"
            raise MapFilterError(message)
        if len(self.rooms) > _MAX_ROOM_VALUES or len(self.districts) > _MAX_DISTRICT_VALUES:
            message = "too many repeated filter values"
            raise MapFilterError(message)

    def normalized_key(self) -> str:
        """Serialize equivalent filters identically for request identity."""
        payload = {
            "area_max": self._decimal_key(self.area_max),
            "area_min": self._decimal_key(self.area_min),
            "bbox": self.bbox.key(),
            "content_types": sorted(item.value for item in self.content_types),
            "districts": sorted(set(self.districts)),
            "market_types": sorted(item.value for item in self.market_types),
            "price_max": self.price_max,
            "price_min": self.price_min,
            "published_from": (self.published_from.isoformat() if self.published_from else None),
            "published_to": self.published_to.isoformat() if self.published_to else None,
            "quick_filter": self.quick_filter,
            "rooms": sorted(set(self.rooms)),
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _decimal_key(value: Decimal | None) -> str | None:
        """Normalize equivalent decimal spellings."""
        return format(value.normalize(), "f") if value is not None else None


@dataclass(frozen=True, slots=True)
class MapLocationRecord:
    """Persistence-neutral grouped map row."""

    id: UUID
    longitude: float
    latitude: float
    display_name: str
    display_address: str
    district: str | None
    precision: str
    confidence: Decimal
    matching_offer_count: int
    total_offer_count: int
    latest_published_at: datetime
    price_min_minor: int | None
    price_max_minor: int | None
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None


@dataclass(frozen=True, slots=True)
class MapQuerySnapshot:
    """Grouped rows and the relevant persisted data version."""

    records: tuple[MapLocationRecord, ...]
    data_version: datetime | None


@dataclass(frozen=True, slots=True)
class MapLocationDTO:
    """Backend-decorated public map projection."""

    id: UUID
    longitude: float
    latitude: float
    display_name: str
    display_address: str
    district: str | None
    precision: str
    confidence_indicator: ConfidenceIndicator
    matching_offer_count: int
    total_offer_count: int
    latest_published_at: datetime
    price_min_minor: int | None
    price_max_minor: int | None
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None


class MapQueryPort(Protocol):
    """Narrow persisted grouped-map query contract."""

    async def query_map(self, filters: MapFilters) -> MapQuerySnapshot:
        """Return grouped matching locations and data version."""
        ...


@dataclass(frozen=True, slots=True)
class MapQueryResult:
    """Delivery-neutral grouped map response."""

    records: tuple[MapLocationDTO, ...]
    etag: str


class QueryMapLocations:
    """Execute the backend-authoritative grouped map query."""

    def __init__(self, query_port: MapQueryPort) -> None:
        """Store the required persistence port."""
        self._query_port = query_port

    async def __call__(self, filters: MapFilters) -> MapQueryResult:
        """Return grouped rows and a deterministic weak projection tag."""
        snapshot = await self._query_port.query_map(filters)
        records = tuple(
            MapLocationDTO(
                id=record.id,
                longitude=record.longitude,
                latitude=record.latitude,
                display_name=record.display_name,
                display_address=record.display_address,
                district=record.district,
                precision=record.precision,
                confidence_indicator=self._confidence_indicator(record.confidence),
                matching_offer_count=record.matching_offer_count,
                total_offer_count=record.total_offer_count,
                latest_published_at=record.latest_published_at,
                price_min_minor=record.price_min_minor,
                price_max_minor=record.price_max_minor,
                area_min_sqm=record.area_min_sqm,
                area_max_sqm=record.area_max_sqm,
            )
            for record in snapshot.records
        )
        version = snapshot.data_version.isoformat() if snapshot.data_version else "empty"
        projection = json.dumps(
            [asdict(record) for record in records],
            default=str,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = sha256(f"{filters.normalized_key()}|{version}|{projection}".encode()).hexdigest()
        return MapQueryResult(records=records, etag=f'W/"{digest}"')

    @staticmethod
    def _confidence_indicator(confidence: Decimal) -> ConfidenceIndicator:
        """Map exact internal confidence to a coarse public indicator."""
        if confidence >= Decimal("0.90"):
            return ConfidenceIndicator.HIGH
        if confidence >= Decimal("0.75"):
            return ConfidenceIndicator.MEDIUM
        return ConfidenceIndicator.LOW
