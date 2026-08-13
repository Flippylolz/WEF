"""Create canonical M1 locations and dated offers.

Revision ID: 20260812_0001
Revises:
Create Date: 2026-08-12 22:44:16
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the forward-only M1 catalog schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("display_address", sa.String(length=240), nullable=False),
        sa.Column("normalized_address", sa.String(length=240), nullable=False),
        sa.Column("normalized_address_hash", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=True),
        sa.Column(
            "city",
            sa.String(length=80),
            server_default=sa.text("'Warszawa'"),
            nullable=False,
        ),
        sa.Column(
            "country_code",
            sa.String(length=2),
            server_default=sa.text("'PL'"),
            nullable=False,
        ),
        sa.Column(
            "point",
            geoalchemy2.Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
            ),
            nullable=True,
        ),
        sa.Column("precision", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("review_status", sa.String(length=16), nullable=False),
        sa.Column(
            "out_of_scope",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "precision IN ('building', 'street', 'district', 'city', 'unknown')",
            name="ck_locations_precision",
        ),
        sa.CheckConstraint(
            "review_status IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_locations_review_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_locations_confidence",
        ),
        sa.CheckConstraint(
            "review_status != 'accepted' OR (point IS NOT NULL AND out_of_scope = false)",
            name="ck_locations_accepted_public_point",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_address_hash",
            name="uq_locations_normalized_address_hash",
        ),
    )
    op.create_index(
        "ix_locations_point_gist",
        "locations",
        ["point"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_locations_public_scope",
        "locations",
        ["review_status", "out_of_scope", "district"],
        unique=False,
    )

    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("market_type", sa.String(length=16), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_source_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("price_min_minor", sa.BigInteger(), nullable=True),
        sa.Column("price_max_minor", sa.BigInteger(), nullable=True),
        sa.Column("area_min_sqm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("area_max_sqm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("rooms_min", sa.SmallInteger(), nullable=True),
        sa.Column("rooms_max", sa.SmallInteger(), nullable=True),
        sa.Column("floor_label", sa.String(length=80), nullable=True),
        sa.Column("delivery_label", sa.String(length=80), nullable=True),
        sa.Column("source_text_excerpt", sa.String(length=280), nullable=False),
        sa.Column("source_text_public_masked", sa.Text(), nullable=False),
        sa.Column("canonical_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_type IN ('development', 'unit')",
            name="ck_offers_content_type",
        ),
        sa.CheckConstraint(
            "market_type IN ('primary', 'secondary', 'unknown')",
            name="ck_offers_market_type",
        ),
        sa.CheckConstraint(
            "visibility IN ('visible', 'needs_review', 'hidden')",
            name="ck_offers_visibility",
        ),
        sa.CheckConstraint(
            "price_min_minor IS NULL OR price_max_minor IS NULL "
            "OR price_min_minor <= price_max_minor",
            name="ck_offers_price_range",
        ),
        sa.CheckConstraint(
            "area_min_sqm IS NULL OR area_max_sqm IS NULL OR area_min_sqm <= area_max_sqm",
            name="ck_offers_area_range",
        ),
        sa.CheckConstraint(
            "rooms_min IS NULL OR rooms_max IS NULL OR rooms_min <= rooms_max",
            name="ck_offers_rooms_range",
        ),
        sa.CheckConstraint(
            "price_min_minor IS NULL OR price_min_minor >= 0",
            name="ck_offers_price_min_nonnegative",
        ),
        sa.CheckConstraint(
            "area_min_sqm IS NULL OR area_min_sqm > 0",
            name="ck_offers_area_min_positive",
        ),
        sa.CheckConstraint(
            "rooms_min IS NULL OR rooms_min > 0",
            name="ck_offers_rooms_min_positive",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_offers_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offers_location", "offers", ["location_id"], unique=False)
    op.create_index(
        "ix_offers_publication",
        "offers",
        ["visibility", "published_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_offers_filter_groups",
        "offers",
        ["content_type", "market_type"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the M1 catalog schema when invoked explicitly."""
    op.drop_index("ix_offers_filter_groups", table_name="offers")
    op.drop_index("ix_offers_publication", table_name="offers")
    op.drop_index("ix_offers_location", table_name="offers")
    op.drop_table("offers")
    op.drop_index("ix_locations_public_scope", table_name="locations")
    op.drop_index(
        "ix_locations_point_gist",
        table_name="locations",
        postgresql_using="gist",
    )
    op.drop_table("locations")
