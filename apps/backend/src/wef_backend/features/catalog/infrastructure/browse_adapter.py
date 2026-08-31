"""SQLAlchemy adapters for facets, location offers, and viewport listings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from sqlalchemy import and_, case, func, or_, select

from wef_backend.features.catalog.application import (
    FacetQueryPort,
    FacetSnapshot,
    ListingBrowseRecord,
    ListingCursor,
    ListingLocationContext,
    LocationOfferQueryPort,
    MapFilters,
    OfferBrowseRecord,
    OfferBrowseSnapshot,
    OfferCursor,
    ViewportListingQueryPort,
    ViewportListingSnapshot,
)
from wef_backend.features.catalog.domain import (
    ContentType,
    LocationReviewStatus,
    MarketType,
    OfferVisibility,
)
from wef_backend.features.catalog.infrastructure.active_ai_origin import active_ai_origin_exists
from wef_backend.features.catalog.infrastructure.map_query_adapter import (
    SQLAlchemyMapQueryAdapter,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.domain.geocoding import canonical_warsaw_district


def _canonical_district_facets(values: Sequence[object]) -> tuple[str, ...]:
    """Collapse raw stored district spellings onto the reviewed canonical list."""
    facets: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        canonical = canonical_warsaw_district(str(value))
        if canonical is not None and canonical not in seen:
            seen.add(canonical)
            facets.append(canonical)
    return tuple(sorted(facets))


if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.elements import ColumnElement


class SQLAlchemyCatalogBrowseAdapter(
    FacetQueryPort,
    LocationOfferQueryPort,
    ViewportListingQueryPort,
):
    """Aggregate visible facets and deterministic browse pages."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy async session factory."""
        self._session_factory = session_factory

    async def query_facets(self) -> FacetSnapshot:
        """Return visible/in-scope canonical options and dataset bounds."""
        base = self._visible_base()
        bounds_statement = (
            select(
                func.min(OfferRow.price_min_minor),
                func.max(OfferRow.price_max_minor),
                func.min(OfferRow.area_min_sqm),
                func.max(OfferRow.area_max_sqm),
                func.min(OfferRow.rooms_min),
                func.max(OfferRow.rooms_max),
                func.min(OfferRow.published_at),
                func.max(OfferRow.published_at),
            )
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*base)
        )
        district_statement = (
            select(LocationRow.district)
            .join(OfferRow, OfferRow.location_id == LocationRow.id)
            .where(*base, LocationRow.district.is_not(None))
            .distinct()
            .order_by(LocationRow.district)
        )
        market_statement = (
            select(OfferRow.market_type)
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*base)
            .distinct()
            .order_by(OfferRow.market_type)
        )
        content_statement = (
            select(OfferRow.content_type)
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*base)
            .distinct()
            .order_by(OfferRow.content_type)
        )
        async with self._session_factory() as session:
            bounds = (await session.execute(bounds_statement)).one()
            districts = _canonical_district_facets(
                (await session.scalars(district_statement)).all(),
            )
            markets = tuple(
                MarketType(value) for value in (await session.scalars(market_statement)).all()
            )
            contents = tuple(
                ContentType(value) for value in (await session.scalars(content_statement)).all()
            )
        room_min, room_max = bounds[4], bounds[5]
        rooms = tuple(
            range(room_min, room_max + 1) if room_min is not None and room_max is not None else ()
        )
        return FacetSnapshot(
            districts=districts,
            rooms=rooms,
            market_types=markets,
            content_types=contents,
            price_min_minor=bounds[0],
            price_max_minor=bounds[1],
            area_min_sqm=bounds[2],
            area_max_sqm=bounds[3],
            published_from=bounds[6],
            published_to=bounds[7],
        )

    async def query_location_offers(
        self,
        *,
        location_id: UUID,
        filters: MapFilters,
        include_non_matching: bool,
        cursor: OfferCursor | None,
        limit: int,
    ) -> OfferBrowseSnapshot:
        """Return a matches-first page plus matching/total counts."""
        base = (*self._visible_base(), LocationRow.id == location_id)
        matching_conditions = SQLAlchemyMapQueryAdapter.filter_conditions(filters)
        matches = and_(*matching_conditions)
        match_rank = case((matches, 1), else_=0)
        page_conditions: list[ColumnElement[bool]] = list(base)
        if not include_non_matching:
            page_conditions.append(matches)
        if cursor is not None:
            page_conditions.append(
                self._after_cursor(
                    match_rank=match_rank,
                    cursor=cursor,
                ),
            )
        page_statement = (
            select(
                OfferRow.id,
                OfferRow.content_type,
                OfferRow.market_type,
                OfferRow.published_at,
                OfferRow.currency,
                OfferRow.price_min_minor,
                OfferRow.price_max_minor,
                OfferRow.parking_price_min_minor,
                OfferRow.parking_price_max_minor,
                OfferRow.parking_included_in_price,
                OfferRow.storage_price_min_minor,
                OfferRow.storage_price_max_minor,
                OfferRow.storage_included_in_price,
                OfferRow.area_min_sqm,
                OfferRow.area_max_sqm,
                OfferRow.rooms_min,
                OfferRow.rooms_max,
                OfferRow.floor_label,
                OfferRow.delivery_label,
                match_rank.label("match_rank"),
                active_ai_origin_exists(OfferRow.id).label("has_active_ai_origin"),
            )
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*page_conditions)
            .order_by(
                match_rank.desc(),
                OfferRow.published_at.desc(),
                OfferRow.id.desc(),
            )
            .limit(limit)
        )
        count_statement = (
            select(
                func.count(OfferRow.id).filter(matches),
                func.count(OfferRow.id),
            )
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*base)
        )
        location_statement = select(LocationRow.id).where(
            LocationRow.id == location_id,
            LocationRow.review_status == LocationReviewStatus.ACCEPTED.value,
            LocationRow.out_of_scope.is_(False),
            LocationRow.point.is_not(None),
        )
        async with self._session_factory() as session:
            location_exists = (await session.scalar(location_statement)) is not None
            matching_count, total_count = (await session.execute(count_statement)).one()
            rows = (await session.execute(page_statement)).all()
        return OfferBrowseSnapshot(
            location_exists=location_exists,
            records=tuple(
                OfferBrowseRecord(
                    id=row.id,
                    content_type=ContentType(row.content_type),
                    market_type=MarketType(row.market_type),
                    published_at=row.published_at,
                    currency=row.currency,
                    price_min_minor=row.price_min_minor,
                    price_max_minor=row.price_max_minor,
                    parking_price_min_minor=row.parking_price_min_minor,
                    parking_price_max_minor=row.parking_price_max_minor,
                    parking_included_in_price=row.parking_included_in_price,
                    storage_price_min_minor=row.storage_price_min_minor,
                    storage_price_max_minor=row.storage_price_max_minor,
                    storage_included_in_price=row.storage_included_in_price,
                    area_min_sqm=row.area_min_sqm,
                    area_max_sqm=row.area_max_sqm,
                    rooms_min=row.rooms_min,
                    rooms_max=row.rooms_max,
                    floor_label=row.floor_label,
                    delivery_label=row.delivery_label,
                    matches_filters=bool(row.match_rank),
                    has_active_ai_origin=bool(row.has_active_ai_origin),
                )
                for row in rows
            ),
            matching_count=int(matching_count),
            total_count=int(total_count),
        )

    async def query_viewport_listings(
        self,
        *,
        filters: MapFilters,
        cursor: ListingCursor | None,
        limit: int,
    ) -> ViewportListingSnapshot:
        """Return a newest-first filtered page plus the filtered count."""
        conditions = SQLAlchemyMapQueryAdapter.filter_conditions(filters)
        page_conditions: list[ColumnElement[bool]] = list(conditions)
        if cursor is not None:
            page_conditions.append(self._after_listing_cursor(cursor))
        page_statement = (
            select(
                OfferRow.id,
                OfferRow.content_type,
                OfferRow.market_type,
                OfferRow.published_at,
                OfferRow.currency,
                OfferRow.price_min_minor,
                OfferRow.price_max_minor,
                OfferRow.parking_price_min_minor,
                OfferRow.parking_price_max_minor,
                OfferRow.parking_included_in_price,
                OfferRow.storage_price_min_minor,
                OfferRow.storage_price_max_minor,
                OfferRow.storage_included_in_price,
                OfferRow.area_min_sqm,
                OfferRow.area_max_sqm,
                OfferRow.rooms_min,
                OfferRow.rooms_max,
                OfferRow.floor_label,
                OfferRow.delivery_label,
                LocationRow.id.label("location_id"),
                LocationRow.display_name.label("location_display_name"),
                LocationRow.display_address.label("location_display_address"),
                LocationRow.district.label("location_district"),
                LocationRow.precision.label("location_precision"),
                LocationRow.confidence.label("location_confidence"),
                func.ST_X(LocationRow.point).label("location_longitude"),
                func.ST_Y(LocationRow.point).label("location_latitude"),
                active_ai_origin_exists(OfferRow.id).label("has_active_ai_origin"),
            )
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*page_conditions)
            .order_by(
                OfferRow.published_at.desc(),
                OfferRow.id.desc(),
            )
            .limit(limit)
        )
        count_statement = (
            select(func.count(OfferRow.id))
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(*conditions)
        )
        async with self._session_factory() as session:
            matching_count = await session.scalar(count_statement)
            rows = (await session.execute(page_statement)).all()
        return ViewportListingSnapshot(
            records=tuple(
                ListingBrowseRecord(
                    id=row.id,
                    content_type=ContentType(row.content_type),
                    market_type=MarketType(row.market_type),
                    published_at=row.published_at,
                    currency=row.currency,
                    price_min_minor=row.price_min_minor,
                    price_max_minor=row.price_max_minor,
                    parking_price_min_minor=row.parking_price_min_minor,
                    parking_price_max_minor=row.parking_price_max_minor,
                    parking_included_in_price=row.parking_included_in_price,
                    storage_price_min_minor=row.storage_price_min_minor,
                    storage_price_max_minor=row.storage_price_max_minor,
                    storage_included_in_price=row.storage_included_in_price,
                    area_min_sqm=row.area_min_sqm,
                    area_max_sqm=row.area_max_sqm,
                    rooms_min=row.rooms_min,
                    rooms_max=row.rooms_max,
                    floor_label=row.floor_label,
                    delivery_label=row.delivery_label,
                    location=ListingLocationContext(
                        id=row.location_id,
                        display_name=row.location_display_name,
                        display_address=row.location_display_address,
                        district=row.location_district,
                        precision=row.location_precision,
                        confidence=row.location_confidence,
                        longitude=float(row.location_longitude),
                        latitude=float(row.location_latitude),
                    ),
                    has_active_ai_origin=bool(row.has_active_ai_origin),
                )
                for row in rows
            ),
            matching_count=int(matching_count or 0),
        )

    @staticmethod
    def _visible_base() -> tuple[ColumnElement[bool], ...]:
        """Return public catalog gates shared by both browse queries."""
        return (
            LocationRow.review_status == LocationReviewStatus.ACCEPTED.value,
            LocationRow.out_of_scope.is_(False),
            LocationRow.point.is_not(None),
            OfferRow.visibility == OfferVisibility.VISIBLE.value,
        )

    @staticmethod
    def _after_cursor(
        *,
        match_rank: ColumnElement[int],
        cursor: OfferCursor,
    ) -> ColumnElement[bool]:
        """Return rows after a descending rank/time/UUID position."""
        return or_(
            match_rank < cursor.match_rank,
            and_(
                match_rank == cursor.match_rank,
                OfferRow.published_at < cursor.published_at,
            ),
            and_(
                match_rank == cursor.match_rank,
                OfferRow.published_at == cursor.published_at,
                OfferRow.id < cursor.offer_id,
            ),
        )

    @staticmethod
    def _after_listing_cursor(cursor: ListingCursor) -> ColumnElement[bool]:
        """Return rows after a descending publication-time/UUID position."""
        return or_(
            OfferRow.published_at < cursor.published_at,
            and_(
                OfferRow.published_at == cursor.published_at,
                OfferRow.id < cursor.offer_id,
            ),
        )
