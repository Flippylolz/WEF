"""Sanitized E26 regression shapes, never evidence of a production repair."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.application.seed_m1 import SeedLocation, SeedOffer
from wef_backend.features.catalog.domain import CoordinatePrecision, LocationReviewStatus


def e26_fixture() -> tuple[tuple[SeedLocation, ...], tuple[SeedOffer, ...]]:
    """Retain representative coordinates without source text or private records."""
    locations, offers = m1_fixture()
    cases = (
        (
            "Ostrzycka",
            21.0805269,
            52.2342096,
            CoordinatePrecision.STREET,
            "0.50",
            LocationReviewStatus.ACCEPTED,
        ),
        (
            "Jugosłowiańska January",
            21.091919,
            52.225418,
            CoordinatePrecision.DISTRICT,
            "0.48",
            LocationReviewStatus.ACCEPTED,
        ),
        (
            "Jugosłowiańska May",
            21.068753,
            52.2463822,
            CoordinatePrecision.BUILDING,
            "1.00",
            LocationReviewStatus.NEEDS_REVIEW,
        ),
        (
            "Nearby building",
            21.0825269,
            52.2342096,
            CoordinatePrecision.BUILDING,
            "0.99",
            LocationReviewStatus.ACCEPTED,
        ),
    )
    seeded_locations, seeded_offers = [], []
    for index, (name, longitude, latitude, precision, confidence, review) in enumerate(cases, 1):
        location_id = UUID(f"e2600000-0000-4000-8000-{index:012d}")
        fingerprint = sha256(f"synthetic-e26-{index}".encode()).hexdigest()
        seeded_locations.append(
            replace(
                locations[0],
                id=location_id,
                display_name=f"Synthetic {name}",
                display_address=f"Synthetic {name}, Praga-Południe",
                normalized_address=f"synthetic e26 {index}",
                normalized_address_hash=fingerprint,
                district="praga-poludnie",
                longitude=longitude,
                latitude=latitude,
                precision=precision,
                confidence=Decimal(confidence),
                review_status=review,
            )
        )
        seeded_offers.append(
            replace(
                offers[0],
                id=UUID(f"e2610000-0000-4000-8000-{index:012d}"),
                location_id=location_id,
                canonical_fingerprint=fingerprint,
                published_at=datetime(2026, 1, index, tzinfo=UTC),
                source_text_excerpt=f"Invented {name} regression; no production repair claim.",
            )
        )
    return tuple(seeded_locations), tuple(seeded_offers)
