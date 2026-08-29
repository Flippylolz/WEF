"""Account-scoped visit baselines and viewed-offer history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.identity.application.identity import Clock


@dataclass(frozen=True, slots=True)
class AccountVisitView:
    """Stable timestamps for one idempotent browser visit."""

    visit_id: UUID
    current_visit_at: datetime
    previous_visit_at: datetime | None


@dataclass(frozen=True, slots=True)
class ViewedOfferView:
    """One account's bounded view history for a public offer."""

    offer_id: UUID
    first_viewed_at: datetime
    last_viewed_at: datetime
    view_count: int


class ViewHistoryStore(Protocol):
    """Persistence contract for account visit and offer-view state."""

    async def start_visit(
        self,
        *,
        user_id: UUID,
        visit_id: UUID,
        started_at: datetime,
    ) -> AccountVisitView:
        """Create or replay one browser visit and return its stable baseline."""
        ...

    async def mark_offer_viewed(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        viewed_at: datetime,
    ) -> ViewedOfferView | None:
        """Record a public offer view or return null when the offer is not public."""
        ...

    async def list_viewed_offers(
        self,
        user_id: UUID,
    ) -> tuple[ViewedOfferView, ...]:
        """Return the account's most recently viewed public offers."""
        ...


class StartAccountVisit:
    """Start one idempotent authenticated browser visit."""

    def __init__(self, store: ViewHistoryStore, clock: Clock) -> None:
        """Store persistence and time dependencies."""
        self._store = store
        self._clock = clock

    async def __call__(self, *, user_id: UUID, visit_id: UUID) -> AccountVisitView:
        """Return a stable previous-visit baseline for this browser visit id."""
        return await self._store.start_visit(
            user_id=user_id,
            visit_id=visit_id,
            started_at=self._clock.now(),
        )


class MarkOfferViewed:
    """Record that one authenticated account opened a public offer."""

    def __init__(self, store: ViewHistoryStore, clock: Clock) -> None:
        """Store persistence and time dependencies."""
        self._store = store
        self._clock = clock

    async def __call__(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
    ) -> ViewedOfferView | None:
        """Record and return the account's updated offer-view state."""
        return await self._store.mark_offer_viewed(
            user_id=user_id,
            offer_id=offer_id,
            viewed_at=self._clock.now(),
        )


class ListViewedOffers:
    """List one authenticated account's viewed offers."""

    def __init__(self, store: ViewHistoryStore) -> None:
        """Store the view-history persistence port."""
        self._store = store

    async def __call__(self, user_id: UUID) -> tuple[ViewedOfferView, ...]:
        """Return most-recent-first view history."""
        return await self._store.list_viewed_offers(user_id)


@dataclass(frozen=True, slots=True)
class ViewHistoryService:
    """Bundle account visit and offer-view interactors for composition."""

    start_visit: StartAccountVisit
    mark_offer_viewed: MarkOfferViewed
    list_viewed_offers: ListViewedOffers
