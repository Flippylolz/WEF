"""PostgreSQL implementation of the deterministic catalog seed port."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.catalog.application import (
    CatalogSeedPort,
    SeedLocation,
    SeedOffer,
    SeedResult,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyCatalogSeedAdapter(CatalogSeedPort):
    """Converge synthetic locations and offers in one transaction."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def upsert_seed(
        self,
        locations: Sequence[SeedLocation],
        offers: Sequence[SeedOffer],
    ) -> SeedResult:
        """Upsert all fixture records using stable primary keys."""
        location_values = [
            {
                "id": item.id,
                "display_name": item.display_name,
                "display_address": item.display_address,
                "normalized_address": item.normalized_address,
                "normalized_address_hash": item.normalized_address_hash,
                "district": item.district,
                "city": "Warszawa",
                "country_code": "PL",
                "point": cast(
                    "WKBElement",
                    WKTElement(f"POINT({item.longitude} {item.latitude})", srid=4326),
                ),
                "precision": item.precision.value,
                "confidence": item.confidence,
                "review_status": item.review_status.value,
                "out_of_scope": False,
            }
            for item in locations
        ]
        offer_values = [
            {
                "id": item.id,
                "location_id": item.location_id,
                "content_type": item.content_type.value,
                "market_type": item.market_type.value,
                "visibility": item.visibility.value,
                "published_at": item.published_at,
                "latest_source_at": item.published_at,
                "currency": item.currency,
                "price_min_minor": item.price_min_minor,
                "price_max_minor": item.price_max_minor,
                "parking_price_min_minor": item.parking_price_min_minor,
                "parking_price_max_minor": item.parking_price_max_minor,
                "parking_included_in_price": item.parking_included_in_price,
                "storage_price_min_minor": item.storage_price_min_minor,
                "storage_price_max_minor": item.storage_price_max_minor,
                "storage_included_in_price": item.storage_included_in_price,
                "area_min_sqm": item.area_min_sqm,
                "area_max_sqm": item.area_max_sqm,
                "rooms_min": item.rooms_min,
                "rooms_max": item.rooms_max,
                "floor_label": item.floor_label,
                "delivery_label": item.delivery_label,
                "source_text_excerpt": item.source_text_excerpt,
                "source_text_public_masked": item.source_text_excerpt,
                "canonical_fingerprint": item.canonical_fingerprint,
                "parser_version": "synthetic-m1-v1",
            }
            for item in offers
        ]

        async with self._session_factory.begin() as session:
            location_insert = insert(LocationRow).values(location_values)
            await session.execute(
                location_insert.on_conflict_do_update(
                    index_elements=[LocationRow.id],
                    set_={
                        "display_name": location_insert.excluded.display_name,
                        "display_address": location_insert.excluded.display_address,
                        "normalized_address": location_insert.excluded.normalized_address,
                        "normalized_address_hash": (
                            location_insert.excluded.normalized_address_hash
                        ),
                        "district": location_insert.excluded.district,
                        "point": location_insert.excluded.point,
                        "precision": location_insert.excluded.precision,
                        "confidence": location_insert.excluded.confidence,
                        "review_status": location_insert.excluded.review_status,
                        "out_of_scope": location_insert.excluded.out_of_scope,
                        "updated_at": func.now(),
                    },
                ),
            )

            offer_insert = insert(OfferRow).values(offer_values)
            await session.execute(
                offer_insert.on_conflict_do_update(
                    index_elements=[OfferRow.id],
                    set_={
                        "location_id": offer_insert.excluded.location_id,
                        "content_type": offer_insert.excluded.content_type,
                        "market_type": offer_insert.excluded.market_type,
                        "visibility": offer_insert.excluded.visibility,
                        "published_at": offer_insert.excluded.published_at,
                        "latest_source_at": offer_insert.excluded.latest_source_at,
                        "currency": offer_insert.excluded.currency,
                        "price_min_minor": offer_insert.excluded.price_min_minor,
                        "price_max_minor": offer_insert.excluded.price_max_minor,
                        "parking_price_min_minor": (offer_insert.excluded.parking_price_min_minor),
                        "parking_price_max_minor": (offer_insert.excluded.parking_price_max_minor),
                        "parking_included_in_price": (
                            offer_insert.excluded.parking_included_in_price
                        ),
                        "storage_price_min_minor": (offer_insert.excluded.storage_price_min_minor),
                        "storage_price_max_minor": (offer_insert.excluded.storage_price_max_minor),
                        "storage_included_in_price": (
                            offer_insert.excluded.storage_included_in_price
                        ),
                        "area_min_sqm": offer_insert.excluded.area_min_sqm,
                        "area_max_sqm": offer_insert.excluded.area_max_sqm,
                        "rooms_min": offer_insert.excluded.rooms_min,
                        "rooms_max": offer_insert.excluded.rooms_max,
                        "floor_label": offer_insert.excluded.floor_label,
                        "delivery_label": offer_insert.excluded.delivery_label,
                        "source_text_excerpt": offer_insert.excluded.source_text_excerpt,
                        "source_text_public_masked": (
                            offer_insert.excluded.source_text_public_masked
                        ),
                        "canonical_fingerprint": (offer_insert.excluded.canonical_fingerprint),
                        "parser_version": offer_insert.excluded.parser_version,
                        "updated_at": func.now(),
                    },
                ),
            )

        return SeedResult(locations=len(locations), offers=len(offers))
