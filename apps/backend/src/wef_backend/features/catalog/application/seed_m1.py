"""Explicit deterministic M1 catalog seed interactor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.catalog.domain import (
    ContentType,
    CoordinatePrecision,
    LocationReviewStatus,
    MarketType,
    OfferVisibility,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID


class ProductionSeedError(RuntimeError):
    """Raised when synthetic data is requested in production."""


@dataclass(frozen=True, slots=True)
class SeedLocation:
    """Synthetic canonical location input."""

    id: UUID
    display_name: str
    display_address: str
    normalized_address: str
    normalized_address_hash: str
    district: str
    longitude: float
    latitude: float
    precision: CoordinatePrecision
    confidence: Decimal
    review_status: LocationReviewStatus = LocationReviewStatus.ACCEPTED


@dataclass(frozen=True, slots=True)
class SeedOffer:
    """Synthetic dated offer input."""

    id: UUID
    location_id: UUID
    content_type: ContentType
    market_type: MarketType
    visibility: OfferVisibility
    published_at: datetime
    currency: str | None
    price_min_minor: int | None
    price_max_minor: int | None
    area_min_sqm: Decimal | None
    area_max_sqm: Decimal | None
    rooms_min: int | None
    rooms_max: int | None
    floor_label: str | None
    delivery_label: str | None
    source_text_excerpt: str
    canonical_fingerprint: str
    parking_price_min_minor: int | None = None
    parking_price_max_minor: int | None = None
    parking_included_in_price: bool = False
    storage_price_min_minor: int | None = None
    storage_price_max_minor: int | None = None
    storage_included_in_price: bool = False


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Stable seed reconciliation counts."""

    locations: int
    offers: int


class CatalogSeedPort(Protocol):
    """Persistence contract owned by the seed use case."""

    async def upsert_seed(
        self,
        locations: Sequence[SeedLocation],
        offers: Sequence[SeedOffer],
    ) -> SeedResult:
        """Converge the canonical fixture in one transaction."""
        ...


class SeedM1Catalog:
    """Guard and persist the explicit M1 synthetic fixture."""

    def __init__(
        self,
        seed_port: CatalogSeedPort,
        *,
        environment: str,
        allow_production: bool = False,
    ) -> None:
        """Store the persistence port and runtime safety boundary."""
        self._seed_port = seed_port
        self._environment = environment
        self._allow_production = allow_production

    async def __call__(
        self,
        locations: Sequence[SeedLocation],
        offers: Sequence[SeedOffer],
    ) -> SeedResult:
        """Reject production without explicit rehearsal opt-in and converge records."""
        if self._environment == "production" and not self._allow_production:
            message = "Synthetic M1 seed is disabled in production"
            raise ProductionSeedError(message)
        return await self._seed_port.upsert_seed(locations, offers)
