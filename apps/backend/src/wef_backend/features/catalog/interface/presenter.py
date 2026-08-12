"""Stable GeoJSON presenter for grouped map locations."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wef_backend.features.catalog.application import ConfidenceIndicator, MapQueryResult


class PointGeometry(BaseModel):
    """GeoJSON Point geometry in longitude/latitude order."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class LocationMapProperties(BaseModel):
    """Backend-owned grouped location display data."""

    model_config = ConfigDict(extra="forbid")

    display_name: str
    display_address: str
    district: str | None
    coordinate_precision: str
    confidence: ConfidenceIndicator
    matching_offer_count: int = Field(ge=1)
    total_offer_count: int = Field(ge=1)
    latest_published_at: datetime
    price_min_minor: int | None = Field(default=None, ge=0)
    price_max_minor: int | None = Field(default=None, ge=0)
    area_min_sqm: Decimal | None = Field(default=None, gt=0)
    area_max_sqm: Decimal | None = Field(default=None, gt=0)
    currency: Literal["PLN"] = "PLN"


class LocationMapFeature(BaseModel):
    """One accepted grouped location feature."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: PointGeometry
    properties: LocationMapProperties


class MapResponseMeta(BaseModel):
    """Bounded response metadata safe for public clients."""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    feature_count: int = Field(ge=0)
    matching_offer_count: int = Field(ge=0)


class LocationMapResponse(BaseModel):
    """GeoJSON FeatureCollection with stable WEF metadata."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: tuple[LocationMapFeature, ...]
    meta: MapResponseMeta


def present_location_map(
    result: MapQueryResult,
    *,
    request_id: UUID,
) -> LocationMapResponse:
    """Present backend decisions without exposing persistence rows."""
    features = tuple(
        LocationMapFeature(
            id=record.id,
            geometry=PointGeometry(
                coordinates=(record.longitude, record.latitude),
            ),
            properties=LocationMapProperties(
                display_name=record.display_name,
                display_address=record.display_address,
                district=record.district,
                coordinate_precision=record.precision,
                confidence=record.confidence_indicator,
                matching_offer_count=record.matching_offer_count,
                total_offer_count=record.total_offer_count,
                latest_published_at=record.latest_published_at,
                price_min_minor=record.price_min_minor,
                price_max_minor=record.price_max_minor,
                area_min_sqm=record.area_min_sqm,
                area_max_sqm=record.area_max_sqm,
            ),
        )
        for record in result.records
    )
    return LocationMapResponse(
        features=features,
        meta=MapResponseMeta(
            request_id=request_id,
            feature_count=len(features),
            matching_offer_count=sum(
                feature.properties.matching_offer_count for feature in features
            ),
        ),
    )
