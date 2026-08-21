"""Promote reviewed historical offers and retire synthetic M1 seed from public views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from wef_backend.features.catalog.domain import OfferVisibility

SYNTHETIC_PARSER_VERSION = "synthetic-m1-v1"
SYNTHETIC_LOCATION_IDS: tuple[UUID, ...] = (
    UUID("10000000-0000-4000-8000-000000000001"),
    UUID("10000000-0000-4000-8000-000000000002"),
    UUID("10000000-0000-4000-8000-000000000003"),
    UUID("10000000-0000-4000-8000-000000000004"),
)


@dataclass(frozen=True, slots=True)
class PromotePublicCatalogResult:
    """Counts from one public-visibility promotion run."""

    offers_promoted: int
    synthetic_offers_hidden: int
    synthetic_locations_rejected: int
    visible_offers: int
    map_eligible_locations: int


class PromotePublicCatalogPort(Protocol):
    """Persistence port for public catalog promotion."""

    async def promote_reviewed_offers(self) -> int:
        """Set needs_review→visible for every non-synthetic offer."""
        ...

    async def hide_synthetic_offers(self) -> int:
        """Hide offers created by the M1 synthetic seed parser version."""
        ...

    async def reject_synthetic_locations(self) -> int:
        """Mark synthetic M1 locations rejected so they cannot pin publicly."""
        ...

    async def count_visible_offers(self) -> int:
        """Count currently visible offers."""
        ...

    async def count_map_eligible_locations(self) -> int:
        """Count accepted in-scope locations with a point and ≥1 visible offer."""
        ...


@dataclass(frozen=True, slots=True)
class PromotePublicCatalog:
    """Hide synthetic seed and publish historical offers."""

    store: PromotePublicCatalogPort

    async def __call__(self) -> PromotePublicCatalogResult:
        """Apply promotion in store order and return reconciliation counts."""
        promoted = await self.store.promote_reviewed_offers()
        hidden = await self.store.hide_synthetic_offers()
        rejected = await self.store.reject_synthetic_locations()
        return PromotePublicCatalogResult(
            offers_promoted=promoted,
            synthetic_offers_hidden=hidden,
            synthetic_locations_rejected=rejected,
            visible_offers=await self.store.count_visible_offers(),
            map_eligible_locations=await self.store.count_map_eligible_locations(),
        )


__all__ = [
    "SYNTHETIC_LOCATION_IDS",
    "SYNTHETIC_PARSER_VERSION",
    "OfferVisibility",
    "PromotePublicCatalog",
    "PromotePublicCatalogPort",
    "PromotePublicCatalogResult",
]
