"""Offer detail query use case and inward-owned port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from wef_backend.features.catalog.application.browse_catalog import OfferDataConfidence
from wef_backend.features.catalog.application.data_origin import DataOrigin, derive_data_origin
from wef_backend.features.catalog.application.map_query import ConfidenceIndicator
from wef_backend.features.catalog.application.offer_display_name import offer_display_name

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from wef_backend.features.catalog.domain import ContentType, MarketType, PropertyType

_HIGH_CONFIDENCE_SCORE = 0.90
_MEDIUM_CONFIDENCE_SCORE = 0.75

_VERIFIED_CHANNEL_USERNAME = "elestate_warszawa"


def confidence_indicator_from_score(score: float) -> ConfidenceIndicator:
    """Map a numeric extraction confidence to the public coarse indicator."""
    if score >= _HIGH_CONFIDENCE_SCORE:
        return ConfidenceIndicator.HIGH
    if score >= _MEDIUM_CONFIDENCE_SCORE:
        return ConfidenceIndicator.MEDIUM
    return ConfidenceIndicator.LOW


def build_verified_source_url(
    *,
    verified_link_base: str | None,
    username: str | None,
    external_message_id: int,
) -> str | None:
    """Build a verified Telegram message URL or return null when unverified."""
    if verified_link_base:
        return f"{verified_link_base.rstrip('/')}/{external_message_id}"
    if username == _VERIFIED_CHANNEL_USERNAME:
        return f"https://t.me/{username}/{external_message_id}"
    return None


def build_public_media_url(storage_key: str) -> str:
    """Return a same-origin opaque public media path."""
    normalized = storage_key.lstrip("/")
    return f"/media/{normalized}"


@dataclass(frozen=True, slots=True)
class LocationSummaryDTO:
    """Public location context for one offer."""

    id: UUID
    display_name: str
    display_address: str
    district: str | None
    coordinate_precision: str
    confidence: ConfidenceIndicator


@dataclass(frozen=True, slots=True)
class DevelopmentSummaryDTO:
    """Named development context when evidenced for the location."""

    id: UUID
    display_name: str
    name_confidence: ConfidenceIndicator


@dataclass(frozen=True, slots=True)
class OfferMediaDTO:
    """Ordered public media metadata for one associated asset."""

    media_asset_id: UUID
    position: int
    media_type: Literal["image", "video"]
    mime_type: str
    width: int | None
    height: int | None
    duration_seconds: int | None
    thumbnail_url: str | None
    content_url: str | None


@dataclass(frozen=True, slots=True)
class SourceHistoryEntryDTO:
    """One related source revision without exposing raw text."""

    source_message_id: UUID
    relationship: str
    published_at: datetime
    edited_at: datetime | None


@dataclass(frozen=True, slots=True)
class OfferDetailRecord:
    """Persistence-neutral public offer detail projection."""

    id: UUID
    content_type: ContentType
    market_type: MarketType
    property_type: PropertyType
    published_at: datetime
    currency: str | None
    price_min_minor: int | None
    price_max_minor: int | None
    parking_price_min_minor: int | None
    parking_price_max_minor: int | None
    parking_included_in_price: bool
    storage_price_min_minor: int | None
    storage_price_max_minor: int | None
    storage_included_in_price: bool
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None
    rooms_min: int | None
    rooms_max: int | None
    floor_label: str | None
    delivery_label: str | None
    public_source_text: str
    parser_version: str
    location: LocationSummaryDTO
    development: DevelopmentSummaryDTO | None
    field_confidence: tuple[tuple[str, ConfidenceIndicator], ...]
    media: tuple[OfferMediaDTO, ...]
    source_message_id: UUID | None
    verified_source_url: str | None
    source_history: tuple[SourceHistoryEntryDTO, ...]
    has_active_ai_origin: bool = False


@dataclass(frozen=True, slots=True)
class OfferDetailDTO:
    """Backend-decorated public offer detail."""

    id: UUID
    content_type: ContentType
    market_type: MarketType
    property_type: PropertyType
    display_name: str
    data_confidence: OfferDataConfidence
    published_at: datetime
    currency: str | None
    price_min_minor: int | None
    price_max_minor: int | None
    parking_price_min_minor: int | None
    parking_price_max_minor: int | None
    parking_included_in_price: bool
    storage_price_min_minor: int | None
    storage_price_max_minor: int | None
    storage_included_in_price: bool
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None
    rooms_min: int | None
    rooms_max: int | None
    floor_label: str | None
    delivery_label: str | None
    public_source_text: str
    parser_version: str
    location: LocationSummaryDTO
    development: DevelopmentSummaryDTO | None
    field_confidence: tuple[tuple[str, ConfidenceIndicator], ...]
    media: tuple[OfferMediaDTO, ...]
    source_message_id: UUID | None
    verified_source_url: str | None
    source_history: tuple[SourceHistoryEntryDTO, ...]
    data_origin: DataOrigin


class OfferDetailQueryPort(Protocol):
    """Public offer detail lookup contract."""

    async def query_offer_detail(self, offer_id: UUID) -> OfferDetailRecord | None:
        """Return one visible offer detail or null when absent/non-public."""
        ...


class GetOfferDetail:
    """Return one backend-decorated public offer detail."""

    def __init__(self, query_port: OfferDetailQueryPort) -> None:
        """Store the offer detail query port."""
        self._query_port = query_port

    async def __call__(self, offer_id: UUID) -> OfferDetailDTO | None:
        """Load and decorate one public offer detail."""
        record = await self._query_port.query_offer_detail(offer_id)
        if record is None:
            return None
        return self._decorate(record)

    @staticmethod
    def _decorate(record: OfferDetailRecord) -> OfferDetailDTO:
        """Own public labels and coarse completeness decisions."""
        complete = all(
            value is not None
            for value in (
                record.price_min_minor,
                record.price_max_minor,
                record.area_min_sqm,
                record.area_max_sqm,
                record.rooms_min,
                record.rooms_max,
            )
        )
        return OfferDetailDTO(
            id=record.id,
            content_type=record.content_type,
            market_type=record.market_type,
            property_type=record.property_type,
            display_name=offer_display_name(record.content_type, record.market_type),
            data_confidence=(
                OfferDataConfidence.COMPLETE if complete else OfferDataConfidence.PARTIAL
            ),
            published_at=record.published_at,
            currency=record.currency,
            price_min_minor=record.price_min_minor,
            price_max_minor=record.price_max_minor,
            parking_price_min_minor=record.parking_price_min_minor,
            parking_price_max_minor=record.parking_price_max_minor,
            parking_included_in_price=record.parking_included_in_price,
            storage_price_min_minor=record.storage_price_min_minor,
            storage_price_max_minor=record.storage_price_max_minor,
            storage_included_in_price=record.storage_included_in_price,
            area_min_sqm=record.area_min_sqm,
            area_max_sqm=record.area_max_sqm,
            rooms_min=record.rooms_min,
            rooms_max=record.rooms_max,
            floor_label=record.floor_label,
            delivery_label=record.delivery_label,
            public_source_text=record.public_source_text,
            parser_version=record.parser_version,
            location=record.location,
            development=record.development,
            field_confidence=record.field_confidence,
            media=record.media,
            source_message_id=record.source_message_id,
            verified_source_url=record.verified_source_url,
            source_history=record.source_history,
            data_origin=derive_data_origin(has_active_ai_origin=record.has_active_ai_origin),
        )


__all__ = [
    "DevelopmentSummaryDTO",
    "GetOfferDetail",
    "LocationSummaryDTO",
    "OfferDetailDTO",
    "OfferDetailQueryPort",
    "OfferDetailRecord",
    "OfferMediaDTO",
    "SourceHistoryEntryDTO",
    "build_public_media_url",
    "build_verified_source_url",
    "confidence_indicator_from_score",
]
