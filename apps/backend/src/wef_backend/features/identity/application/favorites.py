"""Account-scoped favorite location use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class FavoriteLocationView:
    """One favorited location summary for list responses."""

    location_id: UUID
    display_name: str
    display_address: str
    district: str | None
    created_at: str


class FavoriteStore(Protocol):
    """Persistence contract for starred locations."""

    async def list_favorites(self, user_id: UUID) -> tuple[FavoriteLocationView, ...]:
        """Return favorites newest-first with public location labels."""
        ...

    async def add_favorite(self, user_id: UUID, location_id: UUID) -> bool:
        """Star one public location; return False when the location is absent."""
        ...

    async def remove_favorite(self, user_id: UUID, location_id: UUID) -> None:
        """Remove one starred location idempotently."""
        ...


class ListFavoriteLocations:
    """List starred locations for one account."""

    def __init__(self, store: FavoriteStore) -> None:
        """Store the favorite persistence port."""
        self._store = store

    async def __call__(self, user_id: UUID) -> tuple[FavoriteLocationView, ...]:
        """Return favorites newest-first for one account."""
        return await self._store.list_favorites(user_id)


class AddFavoriteLocation:
    """Star one location for an account."""

    def __init__(self, store: FavoriteStore) -> None:
        """Store the favorite persistence port."""
        self._store = store

    async def __call__(self, user_id: UUID, location_id: UUID) -> bool:
        """Star one public location for the account."""
        return await self._store.add_favorite(user_id, location_id)


class RemoveFavoriteLocation:
    """Remove one starred location."""

    def __init__(self, store: FavoriteStore) -> None:
        """Store the favorite persistence port."""
        self._store = store

    async def __call__(self, user_id: UUID, location_id: UUID) -> None:
        """Remove one starred location idempotently."""
        await self._store.remove_favorite(user_id, location_id)


@dataclass(frozen=True, slots=True)
class FavoriteService:
    """Bundle favorite interactors for composition."""

    list_favorites: ListFavoriteLocations
    add_favorite: AddFavoriteLocation
    remove_favorite: RemoveFavoriteLocation
