"""Invented Warsaw fixture used only for M1 verification."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from wef_backend.features.catalog.application.seed_m1 import SeedLocation, SeedOffer
from wef_backend.features.catalog.domain import (
    ContentType,
    CoordinatePrecision,
    MarketType,
    OfferVisibility,
    PropertyType,
)


def _fingerprint(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def m1_fixture() -> tuple[tuple[SeedLocation, ...], tuple[SeedOffer, ...]]:
    """Return stable invented records with no source-derived content."""
    center_id = UUID("10000000-0000-4000-8000-000000000001")
    wola_id = UUID("10000000-0000-4000-8000-000000000002")
    mokotow_id = UUID("10000000-0000-4000-8000-000000000003")
    praga_id = UUID("10000000-0000-4000-8000-000000000004")

    locations = (
        SeedLocation(
            id=center_id,
            display_name="Synthetic Central Residence",
            display_address="Synthetic address 1, Śródmieście",
            normalized_address="synthetic address 1 srodmiescie warszawa",
            normalized_address_hash=_fingerprint("synthetic-center"),
            district="srodmiescie",
            longitude=21.0122,
            latitude=52.2297,
            precision=CoordinatePrecision.BUILDING,
            confidence=Decimal("0.99"),
        ),
        SeedLocation(
            id=wola_id,
            display_name="Synthetic Wola Gardens",
            display_address="Synthetic address 2, Wola",
            normalized_address="synthetic address 2 wola warszawa",
            normalized_address_hash=_fingerprint("synthetic-wola"),
            district="wola",
            longitude=20.9582,
            latitude=52.2323,
            precision=CoordinatePrecision.STREET,
            confidence=Decimal("0.88"),
        ),
        SeedLocation(
            id=mokotow_id,
            display_name="Synthetic Mokotów Point",
            display_address="Synthetic address 3, Mokotów",
            normalized_address="synthetic address 3 mokotow warszawa",
            normalized_address_hash=_fingerprint("synthetic-mokotow"),
            district="mokotow",
            longitude=21.0225,
            latitude=52.1939,
            precision=CoordinatePrecision.BUILDING,
            confidence=Decimal("0.96"),
        ),
        SeedLocation(
            id=praga_id,
            display_name="Synthetic Praga District Homes",
            display_address="Synthetic district point, Praga-Północ",
            normalized_address="synthetic district praga polnoc warszawa",
            normalized_address_hash=_fingerprint("synthetic-praga"),
            district="praga-polnoc",
            longitude=21.0588,
            latitude=52.2546,
            precision=CoordinatePrecision.DISTRICT,
            confidence=Decimal("0.70"),
        ),
    )

    offers = (
        SeedOffer(
            id=UUID("20000000-0000-4000-8000-000000000001"),
            location_id=center_id,
            content_type=ContentType.DEVELOPMENT,
            market_type=MarketType.PRIMARY,
            property_type=PropertyType.UNKNOWN,
            visibility=OfferVisibility.VISIBLE,
            published_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            currency="PLN",
            price_min_minor=80_000_000,
            price_max_minor=125_000_000,
            parking_price_min_minor=4_500_000,
            parking_price_max_minor=4_500_000,
            storage_price_min_minor=1_200_000,
            storage_price_max_minor=1_200_000,
            area_min_sqm=Decimal("35.00"),
            area_max_sqm=Decimal("71.50"),
            rooms_min=1,
            rooms_max=3,
            floor_label=None,
            delivery_label="Synthetic Q4 2027",
            source_text_excerpt="Synthetic development fixture in central Warsaw.",
            canonical_fingerprint=_fingerprint("synthetic-offer-center-development"),
        ),
        SeedOffer(
            id=UUID("20000000-0000-4000-8000-000000000002"),
            location_id=center_id,
            content_type=ContentType.UNIT,
            market_type=MarketType.SECONDARY,
            property_type=PropertyType.APARTMENT,
            visibility=OfferVisibility.VISIBLE,
            published_at=datetime(2026, 7, 18, 9, 30, tzinfo=UTC),
            currency="PLN",
            price_min_minor=105_000_000,
            price_max_minor=105_000_000,
            parking_price_min_minor=7_500_000,
            parking_price_max_minor=7_500_000,
            storage_price_min_minor=1_200_000,
            storage_price_max_minor=1_200_000,
            area_min_sqm=Decimal("48.20"),
            area_max_sqm=Decimal("48.20"),
            rooms_min=2,
            rooms_max=2,
            floor_label="Synthetic floor 4",
            delivery_label=None,
            source_text_excerpt="Synthetic two-room unit fixture.",
            canonical_fingerprint=_fingerprint("synthetic-offer-center-unit"),
        ),
        SeedOffer(
            id=UUID("20000000-0000-4000-8000-000000000003"),
            location_id=wola_id,
            content_type=ContentType.DEVELOPMENT,
            market_type=MarketType.PRIMARY,
            property_type=PropertyType.SEMI_DETACHED,
            visibility=OfferVisibility.VISIBLE,
            published_at=datetime(2026, 7, 25, 12, 15, tzinfo=UTC),
            currency="PLN",
            price_min_minor=69_000_000,
            price_max_minor=99_000_000,
            parking_price_min_minor=3_000_000,
            parking_price_max_minor=3_000_000,
            storage_included_in_price=True,
            area_min_sqm=Decimal("29.50"),
            area_max_sqm=Decimal("58.00"),
            rooms_min=1,
            rooms_max=3,
            floor_label=None,
            delivery_label="Synthetic Q2 2028",
            source_text_excerpt="Synthetic primary-market fixture in Wola.",
            canonical_fingerprint=_fingerprint("synthetic-offer-wola"),
        ),
        SeedOffer(
            id=UUID("20000000-0000-4000-8000-000000000004"),
            location_id=mokotow_id,
            content_type=ContentType.UNIT,
            market_type=MarketType.SECONDARY,
            property_type=PropertyType.APARTMENT,
            visibility=OfferVisibility.VISIBLE,
            published_at=datetime(2026, 6, 30, 16, 45, tzinfo=UTC),
            currency="PLN",
            price_min_minor=149_000_000,
            price_max_minor=149_000_000,
            parking_price_min_minor=5_000_000,
            parking_price_max_minor=5_000_000,
            storage_price_min_minor=2_500_000,
            storage_price_max_minor=2_500_000,
            area_min_sqm=Decimal("72.00"),
            area_max_sqm=Decimal("72.00"),
            rooms_min=3,
            rooms_max=3,
            floor_label="Synthetic floor 2",
            delivery_label=None,
            source_text_excerpt="Synthetic three-room unit fixture in Mokotów.",
            canonical_fingerprint=_fingerprint("synthetic-offer-mokotow"),
        ),
        SeedOffer(
            id=UUID("20000000-0000-4000-8000-000000000005"),
            location_id=praga_id,
            content_type=ContentType.DEVELOPMENT,
            market_type=MarketType.UNKNOWN,
            property_type=PropertyType.HOUSE,
            visibility=OfferVisibility.VISIBLE,
            published_at=datetime(2026, 8, 5, 8, 0, tzinfo=UTC),
            currency=None,
            price_min_minor=None,
            price_max_minor=None,
            area_min_sqm=None,
            area_max_sqm=None,
            rooms_min=None,
            rooms_max=None,
            floor_label=None,
            delivery_label=None,
            source_text_excerpt="Synthetic low-precision district fixture.",
            canonical_fingerprint=_fingerprint("synthetic-offer-praga"),
        ),
    )
    return locations, offers
