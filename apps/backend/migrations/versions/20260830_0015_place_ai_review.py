"""Add minimized expiring place AI review runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0015"
down_revision: str | None = "20260829_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive place AI review schema."""
    op.create_table(
        "place_ai_review_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_revision_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_checksums", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("location_snapshot_version", sa.String(length=64), nullable=False),
        sa.Column("proposed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_input", sa.Integer(), nullable=True),
        sa.Column("token_output", sa.Integer(), nullable=True),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_outcome", sa.String(length=32), nullable=False),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("selected_source_count", sa.Integer(), nullable=False),
        sa.Column("omitted_source_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "state IN ('pending', 'applied', 'expired', 'failed')",
            name="ck_place_ai_review_runs_state",
        ),
        sa.CheckConstraint(
            "model = 'openai/gpt-oss-20b'",
            name="ck_place_ai_review_runs_model",
        ),
        sa.CheckConstraint(
            "provider_outcome IN ("
            "'succeeded', 'timeout', 'refusal', 'quota', 'rate_limited', "
            "'network', 'schema', 'disabled')",
            name="ck_place_ai_review_runs_provider_outcome",
        ),
        sa.CheckConstraint(
            "selected_source_count >= 0 AND omitted_source_count >= 0",
            name="ck_place_ai_review_runs_source_counts",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_place_ai_review_runs_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_place_ai_review_runs_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_place_ai_review_runs"),
    )
    op.create_index(
        "ix_place_ai_review_runs_owner_created",
        "place_ai_review_runs",
        ["owner_user_id", "created_at"],
    )
    op.create_index(
        "ix_place_ai_review_runs_location_state",
        "place_ai_review_runs",
        ["location_id", "state"],
    )
    op.create_index(
        "uq_place_ai_review_runs_pending_location",
        "place_ai_review_runs",
        ["location_id"],
        unique=True,
        postgresql_where=sa.text("state = 'pending'"),
    )


def downgrade() -> None:
    """Drop the place AI review schema."""
    op.drop_index(
        "uq_place_ai_review_runs_pending_location",
        table_name="place_ai_review_runs",
    )
    op.drop_index(
        "ix_place_ai_review_runs_location_state",
        table_name="place_ai_review_runs",
    )
    op.drop_index(
        "ix_place_ai_review_runs_owner_created",
        table_name="place_ai_review_runs",
    )
    op.drop_table("place_ai_review_runs")
