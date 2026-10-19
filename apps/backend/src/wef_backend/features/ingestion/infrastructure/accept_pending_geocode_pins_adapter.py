"""SQLAlchemy adapter that accepts in-scope pending geocode pins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from wef_backend.features.catalog.domain import LocationReviewStatus, OfferVisibility
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeProvider,
    SelectionReason,
    normalize_geocode_query,
    review_geocode_result,
)
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_PENDING_REASONS = (
    SelectionReason.LOW_PRECISION.value,
    SelectionReason.LOW_CONFIDENCE.value,
)


class SQLAlchemyAcceptPendingGeocodePinsAdapter:
    """Promote low-precision/confidence in-scope results onto location pins."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def accept_in_scope_pending_pins(self) -> int:
        """Recheck bounded pending candidates; never override the current policy."""
        async with self._session_factory() as session:
            latest = (
                select(
                    LocationGeocodeSelectionRow.location_id,
                    LocationGeocodeSelectionRow.geocode_result_id,
                    LocationGeocodeSelectionRow.reason_code,
                    func.row_number()
                    .over(
                        partition_by=LocationGeocodeSelectionRow.location_id,
                        order_by=LocationGeocodeSelectionRow.selection_version.desc(),
                    )
                    .label("rn"),
                )
            ).subquery()
            rows = (
                await session.execute(
                    select(LocationRow, GeocodeResultRow)
                    .join(latest, latest.c.location_id == LocationRow.id)
                    .join(GeocodeResultRow, GeocodeResultRow.id == latest.c.geocode_result_id)
                    .where(
                        latest.c.rn == 1,
                        latest.c.reason_code.in_(_PENDING_REASONS),
                        LocationRow.point.is_(None),
                        LocationRow.review_status == LocationReviewStatus.NEEDS_REVIEW.value,
                    )
                    .order_by(LocationRow.id)
                    .limit(25)
                )
            ).all()
        store = SQLAlchemyGeocodeStore(self._session_factory)
        accepted = 0
        for location, result in rows:
            key = GeocodeCacheKey(
                provider=GeocodeProvider(result.provider),
                normalized_query=result.query_normalized,
                normalizer_version=result.normalizer_version,
                scope_version=result.scope_version,
                request_version=result.request_version,
            )
            cached = await store.get_cached(key)
            if cached is None:
                continue
            query = normalize_geocode_query(location.display_address, location.district)
            decision = review_geocode_result(cached.result, query=query)
            if not decision.select_result:
                continue
            await store.select_for_location(
                location_id=location.id,
                cached=cached,
                decision=decision,
                actor_type="automatic_policy",
                actor_id=None,
            )
            async with self._session_factory() as session:
                selected = await session.get(LocationRow, location.id)
                if selected and selected.selected_geocode_result_id == cached.result_id:
                    accepted += 1
        return accepted

    async def count_map_eligible_locations(self) -> int:
        """Count accepted in-scope locations with a point and ≥1 visible offer."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(LocationRow)
                .where(
                    LocationRow.review_status == LocationReviewStatus.ACCEPTED.value,
                    LocationRow.out_of_scope.is_(False),
                    LocationRow.point.is_not(None),
                    LocationRow.id.in_(
                        select(OfferRow.location_id).where(
                            OfferRow.visibility == OfferVisibility.VISIBLE.value,
                        ),
                    ),
                )
            )
            return int(value or 0)

    async def count_needs_review_without_point(self) -> int:
        """Count remaining needs_review locations still lacking a point."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(LocationRow)
                .where(
                    LocationRow.review_status == LocationReviewStatus.NEEDS_REVIEW.value,
                    LocationRow.point.is_(None),
                )
            )
            return int(value or 0)

    async def count_ungeocoded(self) -> int:
        """Count ungeocoded locations."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(LocationRow)
                .where(LocationRow.review_status == LocationReviewStatus.UNGEOCODED.value)
            )
            return int(value or 0)
