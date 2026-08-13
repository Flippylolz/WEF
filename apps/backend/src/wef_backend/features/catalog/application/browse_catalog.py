"""Facet and selected-location offer browsing use cases."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from decimal import Decimal

    from wef_backend.features.catalog.application.map_query import MapFilters
    from wef_backend.features.catalog.domain import ContentType, MarketType

_CURSOR_VERSION = 1
_MAX_CURSOR_LENGTH = 512


class CursorError(ValueError):
    """Raised when an opaque pagination cursor is malformed."""


class OfferDataConfidence(StrEnum):
    """Coarse completeness indicator for offer summaries."""

    PARTIAL = "partial"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class OfferCursor:
    """Versioned deterministic position in the selected-location order."""

    match_rank: int
    published_at: datetime
    offer_id: UUID


class CursorCodec:
    """Encode bounded ordering values without exposing transport structure."""

    @staticmethod
    def encode(cursor: OfferCursor) -> str:
        """Encode a cursor as unpadded URL-safe base64."""
        payload = json.dumps(
            [
                _CURSOR_VERSION,
                cursor.match_rank,
                cursor.published_at.isoformat(),
                str(cursor.offer_id),
            ],
            separators=(",", ":"),
        ).encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def decode(value: str | None) -> OfferCursor | None:
        """Decode and strictly validate a bounded cursor."""
        if value is None:
            return None
        if not value or len(value) > _MAX_CURSOR_LENGTH:
            message = "cursor is invalid"
            raise CursorError(message)
        try:
            padding = "=" * (-len(value) % 4)
            raw = base64.b64decode(
                value + padding,
                altchars=b"-_",
                validate=True,
            )
            version, match_rank, published_at, offer_id = json.loads(raw)
            decoded = OfferCursor(
                match_rank=int(match_rank),
                published_at=datetime.fromisoformat(str(published_at)),
                offer_id=UUID(str(offer_id)),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            message = "cursor is invalid"
            raise CursorError(message) from error
        if version != _CURSOR_VERSION or decoded.match_rank not in (0, 1):
            message = "cursor is invalid"
            raise CursorError(message)
        if decoded.published_at.tzinfo is None:
            message = "cursor is invalid"
            raise CursorError(message)
        return decoded


@dataclass(frozen=True, slots=True)
class FacetSnapshot:
    """Canonical public options and visible dataset bounds."""

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


class FacetQueryPort(Protocol):
    """Visible catalog facet aggregation contract."""

    async def query_facets(self) -> FacetSnapshot:
        """Return canonical visible options and bounds."""
        ...


class QueryFacets:
    """Return backend-owned canonical filter options."""

    def __init__(self, query_port: FacetQueryPort) -> None:
        """Store the facet aggregation port."""
        self._query_port = query_port

    async def __call__(self) -> FacetSnapshot:
        """Return the current visible facet snapshot."""
        return await self._query_port.query_facets()


@dataclass(frozen=True, slots=True)
class OfferBrowseRecord:
    """Persistence-neutral selected-location offer row."""

    id: UUID
    content_type: ContentType
    market_type: MarketType
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
    matches_filters: bool

    @property
    def match_rank(self) -> int:
        """Return the ordering rank for matches-first pagination."""
        return int(self.matches_filters)


@dataclass(frozen=True, slots=True)
class OfferBrowseSnapshot:
    """One bounded page candidate set and aggregate context."""

    location_exists: bool
    records: tuple[OfferBrowseRecord, ...]
    matching_count: int
    total_count: int


class LocationOfferQueryPort(Protocol):
    """Selected-location offer collection contract."""

    async def query_location_offers(
        self,
        *,
        location_id: UUID,
        filters: MapFilters,
        include_non_matching: bool,
        cursor: OfferCursor | None,
        limit: int,
    ) -> OfferBrowseSnapshot:
        """Return at most limit-plus-one ordered records and counts."""
        ...


@dataclass(frozen=True, slots=True)
class OfferSummaryDTO:
    """Backend-decorated dated offer summary."""

    id: UUID
    content_type: ContentType
    market_type: MarketType
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
    matches_filters: bool


@dataclass(frozen=True, slots=True)
class LocationOfferPage:
    """Selected-location page and matching/history context."""

    location_exists: bool
    items: tuple[OfferSummaryDTO, ...]
    matching_count: int
    total_count: int
    next_cursor: str | None


class BrowseLocationOffers:
    """Return a deterministic backend-decorated selected-location page."""

    def __init__(self, query_port: LocationOfferQueryPort) -> None:
        """Store the selected-location query port."""
        self._query_port = query_port

    async def __call__(
        self,
        *,
        location_id: UUID,
        filters: MapFilters,
        include_non_matching: bool,
        cursor: str | None,
        limit: int,
    ) -> LocationOfferPage:
        """Decode pagination, execute one query, and decorate summaries."""
        decoded_cursor = CursorCodec.decode(cursor)
        snapshot = await self._query_port.query_location_offers(
            location_id=location_id,
            filters=filters,
            include_non_matching=include_non_matching,
            cursor=decoded_cursor,
            limit=limit + 1,
        )
        visible_records = snapshot.records[:limit]
        next_cursor = None
        if len(snapshot.records) > limit:
            last = visible_records[-1]
            next_cursor = CursorCodec.encode(
                OfferCursor(
                    match_rank=last.match_rank,
                    published_at=last.published_at,
                    offer_id=last.id,
                ),
            )
        return LocationOfferPage(
            location_exists=snapshot.location_exists,
            items=tuple(self._decorate(record) for record in visible_records),
            matching_count=snapshot.matching_count,
            total_count=snapshot.total_count,
            next_cursor=next_cursor,
        )

    @staticmethod
    def _decorate(record: OfferBrowseRecord) -> OfferSummaryDTO:
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
        return OfferSummaryDTO(
            id=record.id,
            content_type=record.content_type,
            market_type=record.market_type,
            display_name=f"{record.content_type.value} · {record.market_type.value}",
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
            matches_filters=record.matches_filters,
        )
