"""SQLAlchemy persistence for account visit and viewed-offer history."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.identity.application.view_history import (
    AccountVisitView,
    ViewedOfferView,
    ViewHistoryStore,
)
from wef_backend.features.identity.infrastructure.view_history_models import (
    AccountVisitRow,
    ViewedOfferRow,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_MAX_VISITS_PER_ACCOUNT = 50
_MAX_VIEWED_OFFERS_RESPONSE = 500
_PUBLIC_OFFER = text(
    "SELECT 1 FROM offers o "
    "JOIN locations l ON l.id = o.location_id "
    "WHERE o.id = :offer_id "
    "AND o.visibility = 'visible' "
    "AND l.review_status = 'accepted' "
    "AND l.out_of_scope = false "
    "AND l.point IS NOT NULL "
    "LIMIT 1",
)


class SQLAlchemyViewHistoryStore(ViewHistoryStore):
    """Persist bounded account visits and public offer views."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the async session factory."""
        self._session_factory = session_factory

    async def start_visit(
        self,
        *,
        user_id: UUID,
        visit_id: UUID,
        started_at: datetime,
    ) -> AccountVisitView:
        """Create one visit once and keep its previous baseline stable on replay."""
        async with self._session_factory() as session, session.begin():
            existing = await session.scalar(
                select(AccountVisitRow).where(
                    AccountVisitRow.user_id == user_id,
                    AccountVisitRow.visit_id == visit_id,
                ),
            )
            if existing is None:
                previous_visit_at = await session.scalar(
                    select(AccountVisitRow.started_at)
                    .where(AccountVisitRow.user_id == user_id)
                    .order_by(
                        AccountVisitRow.started_at.desc(),
                        AccountVisitRow.visit_id.desc(),
                    )
                    .limit(1),
                )
                await session.execute(
                    insert(AccountVisitRow)
                    .values(
                        user_id=user_id,
                        visit_id=visit_id,
                        started_at=started_at,
                        previous_visit_at=previous_visit_at,
                    )
                    .on_conflict_do_nothing(index_elements=["user_id", "visit_id"]),
                )
                existing = await session.scalar(
                    select(AccountVisitRow).where(
                        AccountVisitRow.user_id == user_id,
                        AccountVisitRow.visit_id == visit_id,
                    ),
                )
                await self._prune_old_visits(session, user_id)
            if existing is None:  # pragma: no cover - database invariant guard
                msg = "visit insert did not produce a row"
                raise RuntimeError(msg)
            return AccountVisitView(
                visit_id=existing.visit_id,
                current_visit_at=existing.started_at,
                previous_visit_at=existing.previous_visit_at,
            )

    async def mark_offer_viewed(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        viewed_at: datetime,
    ) -> ViewedOfferView | None:
        """Upsert one public offer view while preserving its first-view timestamp."""
        async with self._session_factory() as session, session.begin():
            exists = await session.scalar(_PUBLIC_OFFER, {"offer_id": offer_id})
            if exists is None:
                return None
            statement = (
                insert(ViewedOfferRow)
                .values(
                    user_id=user_id,
                    offer_id=offer_id,
                    first_viewed_at=viewed_at,
                    last_viewed_at=viewed_at,
                    view_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "offer_id"],
                    set_={
                        "last_viewed_at": viewed_at,
                        "view_count": ViewedOfferRow.view_count + 1,
                    },
                )
                .returning(ViewedOfferRow)
            )
            row = (await session.execute(statement)).scalar_one()
            return self._viewed_offer(row)

    async def list_viewed_offers(
        self,
        user_id: UUID,
    ) -> tuple[ViewedOfferView, ...]:
        """Return recent history only for offers that remain public."""
        statement = text(
            "SELECT v.offer_id, v.first_viewed_at, v.last_viewed_at, v.view_count "
            "FROM viewed_offers v "
            "JOIN offers o ON o.id = v.offer_id "
            "JOIN locations l ON l.id = o.location_id "
            "WHERE v.user_id = :user_id "
            "AND o.visibility = 'visible' "
            "AND l.review_status = 'accepted' "
            "AND l.out_of_scope = false "
            "AND l.point IS NOT NULL "
            "ORDER BY v.last_viewed_at DESC, v.offer_id "
            "LIMIT :limit",
        )
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    statement,
                    {"user_id": user_id, "limit": _MAX_VIEWED_OFFERS_RESPONSE},
                )
            ).all()
        return tuple(
            ViewedOfferView(
                offer_id=row.offer_id,
                first_viewed_at=row.first_viewed_at,
                last_viewed_at=row.last_viewed_at,
                view_count=row.view_count,
            )
            for row in rows
        )

    @staticmethod
    async def _prune_old_visits(session: AsyncSession, user_id: UUID) -> None:
        retained_ids = (
            select(AccountVisitRow.visit_id)
            .where(AccountVisitRow.user_id == user_id)
            .order_by(
                AccountVisitRow.started_at.desc(),
                AccountVisitRow.visit_id.desc(),
            )
            .limit(_MAX_VISITS_PER_ACCOUNT)
        )
        await session.execute(
            delete(AccountVisitRow).where(
                AccountVisitRow.user_id == user_id,
                AccountVisitRow.visit_id.not_in(retained_ids),
            ),
        )

    @staticmethod
    def _viewed_offer(row: ViewedOfferRow) -> ViewedOfferView:
        return ViewedOfferView(
            offer_id=row.offer_id,
            first_viewed_at=row.first_viewed_at,
            last_viewed_at=row.last_viewed_at,
            view_count=row.view_count,
        )
