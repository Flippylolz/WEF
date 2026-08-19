"""SQLAlchemy mappings for canonical M1 catalog persistence."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from decimal import Decimal  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement  # noqa: TC002 - resolved by SQLAlchemy
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
    text as sa_text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CatalogBase(DeclarativeBase):
    """Declarative metadata owned by catalog infrastructure."""


class LocationRow(CatalogBase):
    """Canonical map location with nullable reviewed coordinates."""

    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint(
            "precision IN ('building', 'street', 'district', 'city', 'unknown')",
            name="ck_locations_precision",
        ),
        CheckConstraint(
            "review_status IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_locations_review_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_locations_confidence",
        ),
        CheckConstraint(
            "review_status != 'accepted' OR (point IS NOT NULL AND out_of_scope = false)",
            name="ck_locations_accepted_public_point",
        ),
        Index("ix_locations_point_gist", "point", postgresql_using="gist"),
        Index("ix_locations_public_scope", "review_status", "out_of_scope", "district"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    display_address: Mapped[str] = mapped_column(Text)
    normalized_address: Mapped[str] = mapped_column(Text)
    normalized_address_hash: Mapped[str] = mapped_column(String(64), unique=True)
    selected_geocode_result_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    district: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(80), default="Warszawa")
    country_code: Mapped[str] = mapped_column(String(2), default="PL")
    point: Mapped[WKBElement | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
    )
    precision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    review_status: Mapped[str] = mapped_column(String(16))
    out_of_scope: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfferRow(CatalogBase):
    """Dated canonical proposition without an availability claim."""

    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('development', 'unit')",
            name="ck_offers_content_type",
        ),
        CheckConstraint(
            "market_type IN ('primary', 'secondary', 'unknown')",
            name="ck_offers_market_type",
        ),
        CheckConstraint(
            "visibility IN ('visible', 'needs_review', 'hidden')",
            name="ck_offers_visibility",
        ),
        CheckConstraint(
            "price_min_minor IS NULL OR price_max_minor IS NULL "
            "OR price_min_minor <= price_max_minor",
            name="ck_offers_price_range",
        ),
        CheckConstraint(
            "area_min_sqm IS NULL OR area_max_sqm IS NULL OR area_min_sqm <= area_max_sqm",
            name="ck_offers_area_range",
        ),
        CheckConstraint(
            "rooms_min IS NULL OR rooms_max IS NULL OR rooms_min <= rooms_max",
            name="ck_offers_rooms_range",
        ),
        CheckConstraint(
            "price_min_minor IS NULL OR price_min_minor >= 0",
            name="ck_offers_price_min_nonnegative",
        ),
        CheckConstraint(
            "(parking_price_min_minor IS NULL AND parking_price_max_minor IS NULL) "
            "OR (parking_price_min_minor IS NOT NULL "
            "AND parking_price_max_minor IS NOT NULL "
            "AND parking_price_min_minor >= 0 "
            "AND parking_price_min_minor <= parking_price_max_minor)",
            name="ck_offers_parking_price_range",
        ),
        CheckConstraint(
            "NOT parking_included_in_price "
            "OR (parking_price_min_minor IS NULL "
            "AND parking_price_max_minor IS NULL)",
            name="ck_offers_parking_included_without_amount",
        ),
        CheckConstraint(
            "(storage_price_min_minor IS NULL AND storage_price_max_minor IS NULL) "
            "OR (storage_price_min_minor IS NOT NULL "
            "AND storage_price_max_minor IS NOT NULL "
            "AND storage_price_min_minor >= 0 "
            "AND storage_price_min_minor <= storage_price_max_minor)",
            name="ck_offers_storage_price_range",
        ),
        CheckConstraint(
            "NOT storage_included_in_price "
            "OR (storage_price_min_minor IS NULL "
            "AND storage_price_max_minor IS NULL)",
            name="ck_offers_storage_included_without_amount",
        ),
        CheckConstraint(
            "area_min_sqm IS NULL OR area_min_sqm > 0",
            name="ck_offers_area_min_positive",
        ),
        CheckConstraint(
            "rooms_min IS NULL OR rooms_min > 0",
            name="ck_offers_rooms_min_positive",
        ),
        Index("ix_offers_location", "location_id"),
        Index("ix_offers_publication", "visibility", "published_at", "id"),
        Index(
            "ix_offers_location_visible_published",
            "location_id",
            "visibility",
            "published_at",
            "id",
        ),
        Index(
            "ix_offers_visible_price_range",
            "visibility",
            "price_min_minor",
            "price_max_minor",
            postgresql_where=sa_text("visibility = 'visible'"),
        ),
        Index("ix_offers_filter_groups", "content_type", "market_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    location_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
    )
    content_type: Mapped[str] = mapped_column(String(16))
    market_type: Mapped[str] = mapped_column(String(16))
    visibility: Mapped[str] = mapped_column(String(16))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latest_source_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str | None] = mapped_column(String(3))
    price_min_minor: Mapped[int | None] = mapped_column(BigInteger)
    price_max_minor: Mapped[int | None] = mapped_column(BigInteger)
    parking_price_min_minor: Mapped[int | None] = mapped_column(BigInteger)
    parking_price_max_minor: Mapped[int | None] = mapped_column(BigInteger)
    parking_included_in_price: Mapped[bool] = mapped_column(default=False)
    storage_price_min_minor: Mapped[int | None] = mapped_column(BigInteger)
    storage_price_max_minor: Mapped[int | None] = mapped_column(BigInteger)
    storage_included_in_price: Mapped[bool] = mapped_column(default=False)
    area_min_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    area_max_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    rooms_min: Mapped[int | None] = mapped_column(SmallInteger)
    rooms_max: Mapped[int | None] = mapped_column(SmallInteger)
    floor_label: Mapped[str | None] = mapped_column(String(80))
    delivery_label: Mapped[str | None] = mapped_column(String(80))
    source_text_excerpt: Mapped[str] = mapped_column(String(280))
    source_text_public_masked: Mapped[str] = mapped_column(Text)
    canonical_fingerprint: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
