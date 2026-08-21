"""PostgreSQL implementation of public catalog promotion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import CursorResult, func, select, update

from wef_backend.features.catalog.application.promote_public_catalog import (
    SYNTHETIC_LOCATION_IDS,
    SYNTHETIC_PARSER_VERSION,
)
from wef_backend.features.catalog.domain import LocationReviewStatus, OfferVisibility
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyPromotePublicCatalogAdapter:
    """Promote historical offers and retire synthetic M1 seed rows."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def promote_reviewed_offers(self) -> int:
        """Publish every non-synthetic needs_review offer."""
        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(OfferRow)
                    .where(
                        OfferRow.visibility == OfferVisibility.NEEDS_REVIEW.value,
                        OfferRow.parser_version != SYNTHETIC_PARSER_VERSION,
                    )
                    .values(visibility=OfferVisibility.VISIBLE.value)
                ),
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def hide_synthetic_offers(self) -> int:
        """Hide any remaining synthetic seed offers from public APIs."""
        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(OfferRow)
                    .where(
                        OfferRow.parser_version == SYNTHETIC_PARSER_VERSION,
                        OfferRow.visibility != OfferVisibility.HIDDEN.value,
                    )
                    .values(visibility=OfferVisibility.HIDDEN.value)
                ),
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def reject_synthetic_locations(self) -> int:
        """Reject synthetic locations so they drop out of map eligibility."""
        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(LocationRow)
                    .where(
                        LocationRow.id.in_(SYNTHETIC_LOCATION_IDS),
                        LocationRow.review_status != LocationReviewStatus.REJECTED.value,
                    )
                    .values(review_status=LocationReviewStatus.REJECTED.value)
                ),
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def count_visible_offers(self) -> int:
        """Count visible offers after promotion."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(OfferRow)
                .where(OfferRow.visibility == OfferVisibility.VISIBLE.value)
            )
            return int(value or 0)

    async def count_map_eligible_locations(self) -> int:
        """Count locations that can appear as public map pins."""
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
