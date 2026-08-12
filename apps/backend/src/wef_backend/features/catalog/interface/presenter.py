"""Stable GeoJSON presenter for grouped map locations."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wef_backend.features.catalog.application import (
    ConfidenceIndicator,
    FacetSnapshot,
    LocationOfferPage,
    MapQueryResult,
    OfferDataConfidence,
)
from wef_backend.features.catalog.domain import ContentType, MarketType


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


class FilterFacetsResponse(BaseModel):
    """Canonical visible options and dataset bounds."""

    model_config = ConfigDict(extra="forbid")

    districts: tuple[str, ...]
    rooms: tuple[int, ...]
    market_types: tuple[MarketType, ...]
    content_types: tuple[ContentType, ...]
    price_min_minor: int | None
    price_max_minor: int | None
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None
    published_from: datetime | None
    published_to: datetime | None


class OfferSummaryResponse(BaseModel):
    """Dated selected-location offer summary."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    content_type: ContentType
    market_type: MarketType
    display_name: str
    data_confidence: OfferDataConfidence
    published_at: datetime
    currency: str | None
    price_min_minor: int | None = Field(default=None, ge=0)
    price_max_minor: int | None = Field(default=None, ge=0)
    area_min_sqm: Decimal | None = Field(default=None, gt=0)
    area_max_sqm: Decimal | None = Field(default=None, gt=0)
    rooms_min: int | None = Field(default=None, ge=0)
    rooms_max: int | None = Field(default=None, ge=0)
    floor_label: str | None
    delivery_label: str | None
    matches_filters: bool


class LocationOfferPageResponse(BaseModel):
    """Selected-location items with explicit match/history context."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[OfferSummaryResponse, ...]
    matching_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    next_cursor: str | None


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


def present_facets(snapshot: FacetSnapshot) -> FilterFacetsResponse:
    """Present canonical facet values without deriving options in clients."""
    return FilterFacetsResponse(
        districts=snapshot.districts,
        rooms=snapshot.rooms,
        market_types=snapshot.market_types,
        content_types=snapshot.content_types,
        price_min_minor=snapshot.price_min_minor,
        price_max_minor=snapshot.price_max_minor,
        area_min_sqm=snapshot.area_min_sqm,
        area_max_sqm=snapshot.area_max_sqm,
        published_from=snapshot.published_from,
        published_to=snapshot.published_to,
    )


def present_location_offer_page(
    page: LocationOfferPage,
) -> LocationOfferPageResponse:
    """Present backend-decorated offers and explicit counts."""
    return LocationOfferPageResponse(
        items=tuple(
            OfferSummaryResponse(
                id=item.id,
                content_type=item.content_type,
                market_type=item.market_type,
                display_name=item.display_name,
                data_confidence=item.data_confidence,
                published_at=item.published_at,
                currency=item.currency,
                price_min_minor=item.price_min_minor,
                price_max_minor=item.price_max_minor,
                area_min_sqm=item.area_min_sqm,
                area_max_sqm=item.area_max_sqm,
                rooms_min=item.rooms_min,
                rooms_max=item.rooms_max,
                floor_label=item.floor_label,
                delivery_label=item.delivery_label,
                matches_filters=item.matches_filters,
            )
            for item in page.items
        ),
        matching_count=page.matching_count,
        total_count=page.total_count,
        next_cursor=page.next_cursor,
    )
