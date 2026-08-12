"""SQLAlchemy/PostGIS grouped map query implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased

from wef_backend.features.catalog.application import (
    MapFilters,
    MapLocationRecord,
    MapQueryPort,
    MapQuerySnapshot,
)
from wef_backend.features.catalog.domain import LocationReviewStatus, OfferVisibility
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.elements import ColumnElement


class SQLAlchemyMapQueryAdapter(MapQueryPort):
    """Apply M1 filter semantics and group matches in PostgreSQL."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def query_map(self, filters: MapFilters) -> MapQuerySnapshot:
        """Return accepted in-scope points with matching and total counts."""
        conditions = self._conditions(filters)
        total_offer = aliased(OfferRow)
        total_offer_count = (
            select(func.count(total_offer.id))
            .where(
                total_offer.location_id == LocationRow.id,
                total_offer.visibility == OfferVisibility.VISIBLE.value,
            )
            .correlate(LocationRow)
            .scalar_subquery()
        )
        statement = (
            select(
                LocationRow.id,
                func.ST_X(LocationRow.point).label("longitude"),
                func.ST_Y(LocationRow.point).label("latitude"),
                LocationRow.display_name,
                LocationRow.display_address,
                LocationRow.district,
                LocationRow.precision,
                LocationRow.confidence,
                func.count(OfferRow.id).label("matching_offer_count"),
                total_offer_count.label("total_offer_count"),
                func.max(OfferRow.published_at).label("latest_published_at"),
                func.min(OfferRow.price_min_minor).label("price_min_minor"),
                func.max(OfferRow.price_max_minor).label("price_max_minor"),
                func.min(OfferRow.area_min_sqm).label("area_min_sqm"),
                func.max(OfferRow.area_max_sqm).label("area_max_sqm"),
                func.max(OfferRow.updated_at).label("data_version"),
            )
            .join(OfferRow, OfferRow.location_id == LocationRow.id)
            .where(*conditions)
            .group_by(
                LocationRow.id,
                LocationRow.point,
                LocationRow.display_name,
                LocationRow.display_address,
                LocationRow.district,
                LocationRow.precision,
                LocationRow.confidence,
            )
            .order_by(LocationRow.id)
        )

        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()

        records = tuple(
            MapLocationRecord(
                id=row.id,
                longitude=float(row.longitude),
                latitude=float(row.latitude),
                display_name=row.display_name,
                display_address=row.display_address,
                district=row.district,
                precision=row.precision,
                confidence=row.confidence,
                matching_offer_count=int(row.matching_offer_count),
                total_offer_count=int(row.total_offer_count),
                latest_published_at=row.latest_published_at,
                price_min_minor=row.price_min_minor,
                price_max_minor=row.price_max_minor,
                area_min_sqm=row.area_min_sqm,
                area_max_sqm=row.area_max_sqm,
            )
            for row in rows
        )
        versions = tuple(row.data_version for row in rows if row.data_version is not None)
        return MapQuerySnapshot(
            records=records,
            data_version=max(versions, default=None),
        )

    @staticmethod
    def _conditions(filters: MapFilters) -> tuple[ColumnElement[bool], ...]:
        """Build one SQL predicate set for all M1 filter groups."""
        required: tuple[ColumnElement[bool], ...] = (
            LocationRow.review_status == LocationReviewStatus.ACCEPTED.value,
            LocationRow.out_of_scope.is_(False),
            LocationRow.point.is_not(None),
            OfferRow.visibility == OfferVisibility.VISIBLE.value,
            func.ST_Intersects(
                LocationRow.point,
                func.ST_MakeEnvelope(
                    filters.bbox.min_lng,
                    filters.bbox.min_lat,
                    filters.bbox.max_lng,
                    filters.bbox.max_lat,
                    4326,
                ),
            ),
        )
        return (
            required
            + SQLAlchemyMapQueryAdapter._range_conditions(filters)
            + SQLAlchemyMapQueryAdapter._group_conditions(filters)
            + SQLAlchemyMapQueryAdapter._date_conditions(filters)
        )

    @staticmethod
    def _range_conditions(filters: MapFilters) -> tuple[ColumnElement[bool], ...]:
        """Build inclusive overlap predicates for requested numeric ranges."""
        conditions: list[ColumnElement[bool]] = []
        if filters.price_min is not None:
            conditions.append(OfferRow.price_max_minor >= filters.price_min)
        if filters.price_max is not None:
            conditions.append(OfferRow.price_min_minor <= filters.price_max)
        if filters.area_min is not None:
            conditions.append(OfferRow.area_max_sqm >= filters.area_min)
        if filters.area_max is not None:
            conditions.append(OfferRow.area_min_sqm <= filters.area_max)
        return tuple(conditions)

    @staticmethod
    def _group_conditions(filters: MapFilters) -> tuple[ColumnElement[bool], ...]:
        """Build OR-within-group predicates for repeated values."""
        conditions: list[ColumnElement[bool]] = []
        if filters.rooms:
            conditions.append(
                or_(
                    *(
                        and_(
                            OfferRow.rooms_min <= room,
                            OfferRow.rooms_max >= room,
                        )
                        for room in filters.rooms
                    ),
                ),
            )
        if filters.districts:
            conditions.append(LocationRow.district.in_(filters.districts))
        if filters.market_types:
            conditions.append(
                OfferRow.market_type.in_(tuple(item.value for item in filters.market_types)),
            )
        if filters.content_types:
            conditions.append(
                OfferRow.content_type.in_(tuple(item.value for item in filters.content_types)),
            )
        return tuple(conditions)

    @staticmethod
    def _date_conditions(filters: MapFilters) -> tuple[ColumnElement[bool], ...]:
        """Build inclusive publication-time predicates."""
        conditions: list[ColumnElement[bool]] = []
        if filters.published_from is not None:
            conditions.append(OfferRow.published_at >= filters.published_from)
        if filters.published_to is not None:
            conditions.append(OfferRow.published_at <= filters.published_to)
        return tuple(conditions)
