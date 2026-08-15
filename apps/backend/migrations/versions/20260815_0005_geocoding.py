"""Create provider-neutral geocode cache and review lineage.

Revision ID: 20260815_0005
Revises: 20260815_0004
Create Date: 2026-08-15 06:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260815_0005"
down_revision: str | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cache, fenced miss claims, selected result, and lineage."""
    op.create_table(
        "geocode_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("query_original", sa.String(length=240), nullable=False),
        sa.Column("query_normalized", sa.String(length=240), nullable=False),
        sa.Column("normalizer_version", sa.String(length=40), nullable=False),
        sa.Column("scope_version", sa.String(length=40), nullable=False),
        sa.Column("request_version", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("provider_result_id", sa.String(length=240), nullable=True),
        sa.Column("point", Geometry("POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("display_name", sa.String(length=320), nullable=True),
        sa.Column("precision", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("within_scope", sa.Boolean(), nullable=True),
        sa.Column("response_json", JSONB(), nullable=False),
        sa.Column("attribution_text", sa.String(length=320), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "precision IN ('building', 'street', 'district', 'city', 'unknown')",
            name="ck_geocode_results_precision",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_geocode_results_confidence",
        ),
        sa.CheckConstraint(
            "(point IS NULL) = (within_scope IS NULL OR error_code IS NOT NULL)",
            name="ck_geocode_results_point_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_hash", name="uq_geocode_results_query_hash"),
    )
    op.create_index(
        "ix_geocode_results_provider_attempted",
        "geocode_results",
        ["provider", "attempted_at"],
        unique=False,
    )
    op.create_table(
        "geocode_miss_claims",
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_geocode_result_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("fencing_token > 0", name="ck_geocode_claims_positive_fence"),
        sa.ForeignKeyConstraint(
            ["completed_geocode_result_id"],
            ["geocode_results.id"],
            name="fk_geocode_claims_completed_result",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("query_hash"),
    )
    op.create_index(
        "ix_geocode_claims_lease_expiry",
        "geocode_miss_claims",
        ["lease_expires_at"],
        unique=False,
    )
    op.add_column("locations", sa.Column("selected_geocode_result_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_locations_selected_geocode_result",
        "locations",
        "geocode_results",
        ["selected_geocode_result_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "location_geocode_selections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("geocode_result_id", sa.Uuid(), nullable=True),
        sa.Column("from_state", sa.String(length=16), nullable=False),
        sa.Column("to_state", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=True),
        sa.Column("review_policy_version", sa.String(length=40), nullable=False),
        sa.Column("selection_version", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_state IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_location_selections_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_location_selections_to_state",
        ),
        sa.CheckConstraint("selection_version > 0", name="ck_location_selections_version"),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_location_geocode_selections_location",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["geocode_result_id"],
            ["geocode_results.id"],
            name="fk_location_geocode_selections_result",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "location_id",
            "selection_version",
            name="uq_location_geocode_selection_version",
        ),
    )
    op.create_index(
        "ix_location_geocode_selections_location",
        "location_geocode_selections",
        ["location_id", "decided_at"],
        unique=False,
    )
    op.create_index(
        "ix_location_geocode_selections_result",
        "location_geocode_selections",
        ["geocode_result_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only the additive geocoding schema when explicitly invoked."""
    op.drop_index("ix_location_geocode_selections_result", table_name="location_geocode_selections")
    op.drop_index(
        "ix_location_geocode_selections_location", table_name="location_geocode_selections"
    )
    op.drop_table("location_geocode_selections")
    op.drop_constraint("fk_locations_selected_geocode_result", "locations", type_="foreignkey")
    op.drop_column("locations", "selected_geocode_result_id")
    op.drop_index("ix_geocode_claims_lease_expiry", table_name="geocode_miss_claims")
    op.drop_table("geocode_miss_claims")
    op.drop_index("ix_geocode_results_provider_attempted", table_name="geocode_results")
    op.drop_table("geocode_results")
