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
    ViewportListingPage,
)
from wef_backend.features.catalog.application.offer_detail import OfferDetailDTO
from wef_backend.features.catalog.application.quick_filters import QuickFilterPreset
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


class QuickFilterPresetResponse(BaseModel):
    """One server-defined quick filter preset."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label_key: str


class QuickFilterListResponse(BaseModel):
    """Supported quick filter presets in stable order."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[QuickFilterPresetResponse, ...]


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
    parking_price_min_minor: int | None = Field(default=None, ge=0)
    parking_price_max_minor: int | None = Field(default=None, ge=0)
    parking_included_in_price: bool = False
    storage_price_min_minor: int | None = Field(default=None, ge=0)
    storage_price_max_minor: int | None = Field(default=None, ge=0)
    storage_included_in_price: bool = False
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


class ListingLocationResponse(BaseModel):
    """Public parent location context for one viewport listing card."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    display_name: str
    display_address: str
    district: str | None
    coordinate_precision: str
    confidence: ConfidenceIndicator
    geometry: PointGeometry


class ViewportListingItemResponse(BaseModel):
    """Dated filter-matching viewport listing summary."""

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
    parking_price_min_minor: int | None = Field(default=None, ge=0)
    parking_price_max_minor: int | None = Field(default=None, ge=0)
    parking_included_in_price: bool = False
    storage_price_min_minor: int | None = Field(default=None, ge=0)
    storage_price_max_minor: int | None = Field(default=None, ge=0)
    storage_included_in_price: bool = False
    area_min_sqm: Decimal | None = Field(default=None, gt=0)
    area_max_sqm: Decimal | None = Field(default=None, gt=0)
    rooms_min: int | None = Field(default=None, ge=0)
    rooms_max: int | None = Field(default=None, ge=0)
    floor_label: str | None
    delivery_label: str | None
    location: ListingLocationResponse


class ViewportListingPageResponse(BaseModel):
    """Viewport items with the filtered total and opaque continuation."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[ViewportListingItemResponse, ...]
    matching_count: int = Field(ge=0)
    next_cursor: str | None


class LocationSummaryResponse(BaseModel):
    """Public location context for one offer."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    display_name: str
    display_address: str
    district: str | None
    coordinate_precision: str
    confidence: ConfidenceIndicator


class DevelopmentSummaryResponse(BaseModel):
    """Named development context when evidenced for the location."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    display_name: str
    name_confidence: ConfidenceIndicator


class FieldConfidenceEntryResponse(BaseModel):
    """One backend-owned field confidence indicator."""

    model_config = ConfigDict(extra="forbid")

    field: str
    confidence: ConfidenceIndicator


class OfferMediaResponse(BaseModel):
    """Ordered public media metadata for one associated asset."""

    model_config = ConfigDict(extra="forbid")

    media_asset_id: UUID
    position: int = Field(ge=0)
    media_type: Literal["image", "video"]
    mime_type: str
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_seconds: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None
    content_url: str | None


class SourceHistoryEntryResponse(BaseModel):
    """One related source revision without exposing raw text."""

    model_config = ConfigDict(extra="forbid")

    source_message_id: UUID
    relationship: str
    published_at: datetime
    edited_at: datetime | None


class OfferDetailResponse(BaseModel):
    """Full public offer detail with masked text and verified source action."""

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
    parking_price_min_minor: int | None = Field(default=None, ge=0)
    parking_price_max_minor: int | None = Field(default=None, ge=0)
    parking_included_in_price: bool = False
    storage_price_min_minor: int | None = Field(default=None, ge=0)
    storage_price_max_minor: int | None = Field(default=None, ge=0)
    storage_included_in_price: bool = False
    area_min_sqm: Decimal | None = Field(default=None, gt=0)
    area_max_sqm: Decimal | None = Field(default=None, gt=0)
    rooms_min: int | None = Field(default=None, ge=0)
    rooms_max: int | None = Field(default=None, ge=0)
    floor_label: str | None
    delivery_label: str | None
    public_source_text: str
    parser_version: str
    location: LocationSummaryResponse
    development: DevelopmentSummaryResponse | None
    field_confidence: tuple[FieldConfidenceEntryResponse, ...]
    media: tuple[OfferMediaResponse, ...]
    source_message_id: UUID | None
    verified_source_url: str | None
    source_history: tuple[SourceHistoryEntryResponse, ...]


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
                parking_price_min_minor=item.parking_price_min_minor,
                parking_price_max_minor=item.parking_price_max_minor,
                parking_included_in_price=item.parking_included_in_price,
                storage_price_min_minor=item.storage_price_min_minor,
                storage_price_max_minor=item.storage_price_max_minor,
                storage_included_in_price=item.storage_included_in_price,
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


def present_viewport_listing_page(
    page: ViewportListingPage,
) -> ViewportListingPageResponse:
    """Present backend-decorated viewport listings and the filtered total."""
    return ViewportListingPageResponse(
        items=tuple(
            ViewportListingItemResponse(
                id=item.id,
                content_type=item.content_type,
                market_type=item.market_type,
                display_name=item.display_name,
                data_confidence=item.data_confidence,
                published_at=item.published_at,
                currency=item.currency,
                price_min_minor=item.price_min_minor,
                price_max_minor=item.price_max_minor,
                parking_price_min_minor=item.parking_price_min_minor,
                parking_price_max_minor=item.parking_price_max_minor,
                parking_included_in_price=item.parking_included_in_price,
                storage_price_min_minor=item.storage_price_min_minor,
                storage_price_max_minor=item.storage_price_max_minor,
                storage_included_in_price=item.storage_included_in_price,
                area_min_sqm=item.area_min_sqm,
                area_max_sqm=item.area_max_sqm,
                rooms_min=item.rooms_min,
                rooms_max=item.rooms_max,
                floor_label=item.floor_label,
                delivery_label=item.delivery_label,
                location=ListingLocationResponse(
                    id=item.location.id,
                    display_name=item.location.display_name,
                    display_address=item.location.display_address,
                    district=item.location.district,
                    coordinate_precision=item.location.precision,
                    confidence=item.location.confidence_indicator,
                    geometry=PointGeometry(
                        coordinates=(item.location.longitude, item.location.latitude),
                    ),
                ),
            )
            for item in page.items
        ),
        matching_count=page.matching_count,
        next_cursor=page.next_cursor,
    )


def present_quick_filters(
    presets: tuple[QuickFilterPreset, ...],
) -> QuickFilterListResponse:
    """Present quick-filter metadata without client-side preset lists."""
    return QuickFilterListResponse(
        items=tuple(
            QuickFilterPresetResponse(id=preset.id, label_key=preset.label_key)
            for preset in presets
        ),
    )


def present_offer_detail(detail: OfferDetailDTO) -> OfferDetailResponse:
    """Present one public offer detail without exposing persistence internals."""
    return OfferDetailResponse(
        id=detail.id,
        content_type=detail.content_type,
        market_type=detail.market_type,
        display_name=detail.display_name,
        data_confidence=detail.data_confidence,
        published_at=detail.published_at,
        currency=detail.currency,
        price_min_minor=detail.price_min_minor,
        price_max_minor=detail.price_max_minor,
        parking_price_min_minor=detail.parking_price_min_minor,
        parking_price_max_minor=detail.parking_price_max_minor,
        parking_included_in_price=detail.parking_included_in_price,
        storage_price_min_minor=detail.storage_price_min_minor,
        storage_price_max_minor=detail.storage_price_max_minor,
        storage_included_in_price=detail.storage_included_in_price,
        area_min_sqm=detail.area_min_sqm,
        area_max_sqm=detail.area_max_sqm,
        rooms_min=detail.rooms_min,
        rooms_max=detail.rooms_max,
        floor_label=detail.floor_label,
        delivery_label=detail.delivery_label,
        public_source_text=detail.public_source_text,
        parser_version=detail.parser_version,
        location=LocationSummaryResponse(
            id=detail.location.id,
            display_name=detail.location.display_name,
            display_address=detail.location.display_address,
            district=detail.location.district,
            coordinate_precision=detail.location.coordinate_precision,
            confidence=detail.location.confidence,
        ),
        development=(
            DevelopmentSummaryResponse(
                id=detail.development.id,
                display_name=detail.development.display_name,
                name_confidence=detail.development.name_confidence,
            )
            if detail.development is not None
            else None
        ),
        field_confidence=tuple(
            FieldConfidenceEntryResponse(field=field, confidence=confidence)
            for field, confidence in detail.field_confidence
        ),
        media=tuple(
            OfferMediaResponse(
                media_asset_id=item.media_asset_id,
                position=item.position,
                media_type=item.media_type,
                mime_type=item.mime_type,
                width=item.width,
                height=item.height,
                duration_seconds=item.duration_seconds,
                thumbnail_url=item.thumbnail_url,
                content_url=item.content_url,
            )
            for item in detail.media
        ),
        source_message_id=detail.source_message_id,
        verified_source_url=detail.verified_source_url,
        source_history=tuple(
            SourceHistoryEntryResponse(
                source_message_id=item.source_message_id,
                relationship=item.relationship,
                published_at=item.published_at,
                edited_at=item.edited_at,
            )
            for item in detail.source_history
        ),
    )
