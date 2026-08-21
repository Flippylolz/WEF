"""SQLAlchemy adapter that accepts in-scope pending geocode pins."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import func, select, update

from wef_backend.features.catalog.domain import LocationReviewStatus, OfferVisibility
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.domain.geocoding import (
    REVIEW_POLICY_VERSION,
    SelectionReason,
)
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_OPERATOR_ACTOR = "ad-034-accept-pending-pins"
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
        """Accept needs_review locations that already have in-scope coordinates."""
        async with self._session_factory() as session:
            latest = (
                select(
                    LocationGeocodeSelectionRow.location_id.label("location_id"),
                    LocationGeocodeSelectionRow.geocode_result_id.label("geocode_result_id"),
                    LocationGeocodeSelectionRow.selection_version.label("selection_version"),
                    LocationGeocodeSelectionRow.reason_code.label("reason_code"),
                    func.row_number()
                    .over(
                        partition_by=LocationGeocodeSelectionRow.location_id,
                        order_by=LocationGeocodeSelectionRow.selection_version.desc(),
                    )
                    .label("rn"),
                )
            ).subquery()
            eligible = (
                select(
                    LocationRow.id.label("location_id"),
                    LocationRow.review_status.label("from_state"),
                    latest.c.selection_version,
                    GeocodeResultRow.id.label("geocode_result_id"),
                    GeocodeResultRow.point,
                    GeocodeResultRow.precision,
                    GeocodeResultRow.confidence,
                )
                .join(latest, latest.c.location_id == LocationRow.id)
                .join(GeocodeResultRow, GeocodeResultRow.id == latest.c.geocode_result_id)
                .where(
                    latest.c.rn == 1,
                    LocationRow.point.is_(None),
                    LocationRow.review_status == LocationReviewStatus.NEEDS_REVIEW.value,
                    latest.c.reason_code.in_(_PENDING_REASONS),
                    GeocodeResultRow.within_scope.is_(True),
                    GeocodeResultRow.point.is_not(None),
                )
            )
            rows = (await session.execute(eligible)).all()
            now = datetime.now(UTC)
            for row in rows:
                session.add(
                    LocationGeocodeSelectionRow(
                        id=uuid4(),
                        location_id=row.location_id,
                        geocode_result_id=row.geocode_result_id,
                        from_state=row.from_state,
                        to_state=LocationReviewStatus.ACCEPTED.value,
                        reason_code=SelectionReason.MANUAL_ACCEPT.value,
                        actor_type="operator",
                        actor_id=_OPERATOR_ACTOR,
                        review_policy_version=REVIEW_POLICY_VERSION,
                        selection_version=int(row.selection_version) + 1,
                        decided_at=now,
                    ),
                )
                await session.execute(
                    update(LocationRow)
                    .where(LocationRow.id == row.location_id)
                    .values(
                        point=row.point,
                        precision=row.precision,
                        confidence=row.confidence,
                        review_status=LocationReviewStatus.ACCEPTED.value,
                        selected_geocode_result_id=row.geocode_result_id,
                        out_of_scope=False,
                        updated_at=now,
                    ),
                )
            await session.commit()
            return len(rows)

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
