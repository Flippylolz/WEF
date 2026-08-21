"""Operator acceptance of in-scope pending geocode pins for public map visibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AcceptPendingGeocodePinsResult:
    """Counts from one pending-pin acceptance run."""

    locations_accepted: int
    map_eligible_locations: int
    remaining_needs_review_without_point: int
    remaining_ungeocoded: int


class AcceptPendingGeocodePinsPort(Protocol):
    """Persistence for promoting reviewed-but-unpinned geocode results."""

    async def accept_in_scope_pending_pins(self) -> int:
        """Accept needs_review locations that already have in-scope coordinates."""
        ...

    async def count_map_eligible_locations(self) -> int:
        """Count accepted in-scope locations with a point and ≥1 visible offer."""
        ...

    async def count_needs_review_without_point(self) -> int:
        """Count remaining needs_review locations still lacking a point."""
        ...

    async def count_ungeocoded(self) -> int:
        """Count ungeocoded locations."""
        ...


@dataclass(frozen=True, slots=True)
class AcceptPendingGeocodePins:
    """Promote low-precision/low-confidence in-scope results onto location pins."""

    store: AcceptPendingGeocodePinsPort

    async def __call__(self) -> AcceptPendingGeocodePinsResult:
        """Accept pending pins and return reconciliation counts."""
        accepted = await self.store.accept_in_scope_pending_pins()
        return AcceptPendingGeocodePinsResult(
            locations_accepted=accepted,
            map_eligible_locations=await self.store.count_map_eligible_locations(),
            remaining_needs_review_without_point=(
                await self.store.count_needs_review_without_point()
            ),
            remaining_ungeocoded=await self.store.count_ungeocoded(),
        )
