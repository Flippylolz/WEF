"""SQLAlchemy persistence for favorite locations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.identity.application.favorites import (
    FavoriteLocationView,
    FavoriteStore,
)
from wef_backend.features.identity.infrastructure.favorite_models import FavoriteLocationRow

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_PUBLIC_LOCATION = text(
    "SELECT 1 FROM locations "
    "WHERE id = :location_id "
    "AND review_status = 'accepted' "
    "AND out_of_scope = false "
    "LIMIT 1",
)


class SQLAlchemyFavoriteStore(FavoriteStore):
    """FavoriteStore using SQL joins without cross-feature ORM imports."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the async SQLAlchemy session factory."""
        self._session_factory = session_factory

    async def list_favorites(self, user_id: UUID) -> tuple[FavoriteLocationView, ...]:
        """Return favorites newest-first with public location labels."""
        statement = text(
            "SELECT f.location_id, f.created_at, l.display_name, l.display_address, l.district "
            "FROM favorite_locations f "
            "JOIN locations l ON l.id = f.location_id "
            "WHERE f.user_id = :user_id "
            "AND l.review_status = 'accepted' "
            "AND l.out_of_scope = false "
            "ORDER BY f.created_at DESC, f.location_id",
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement, {"user_id": user_id})).all()
        return tuple(
            FavoriteLocationView(
                location_id=row.location_id,
                display_name=row.display_name,
                display_address=row.display_address,
                district=row.district,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        )

    async def add_favorite(self, user_id: UUID, location_id: UUID) -> bool:
        """Star one accepted public location; return False when absent."""
        async with self._session_factory() as session:
            exists = await session.scalar(
                _PUBLIC_LOCATION,
                {"location_id": location_id},
            )
            if exists is None:
                return False
            await session.execute(
                insert(FavoriteLocationRow)
                .values(user_id=user_id, location_id=location_id)
                .on_conflict_do_nothing(index_elements=["user_id", "location_id"]),
            )
            await session.commit()
            return True

    async def remove_favorite(self, user_id: UUID, location_id: UUID) -> None:
        """Remove one starred location idempotently."""
        async with self._session_factory() as session:
            row = await session.scalar(
                select(FavoriteLocationRow)
                .where(
                    FavoriteLocationRow.user_id == user_id,
                    FavoriteLocationRow.location_id == location_id,
                )
                .limit(1),
            )
            if row is not None:
                await session.delete(row)
                await session.commit()
