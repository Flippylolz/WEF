"""Add minimized expiring ingestion AI parse runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0018"
down_revision: str | None = "20260901_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive ingestion AI parse schema."""
    op.create_table(
        "ingestion_ai_parse_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_revision_id", sa.Uuid(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("proposed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_input", sa.Integer(), nullable=True),
        sa.Column("token_output", sa.Integer(), nullable=True),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_outcome", sa.String(length=32), nullable=False),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "state IN ('pending', 'applied', 'expired', 'failed')",
            name="ck_ingestion_ai_parse_runs_state",
        ),
        sa.CheckConstraint(
            "model = 'openai/gpt-oss-20b'",
            name="ck_ingestion_ai_parse_runs_model",
        ),
        sa.CheckConstraint(
            "provider_outcome IN ("
            "'succeeded', 'timeout', 'refusal', 'quota', 'rate_limited', "
            "'network', 'schema', 'disabled')",
            name="ck_ingestion_ai_parse_runs_provider_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_ingestion_ai_parse_runs_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["source_messages.id"],
            name="fk_ingestion_ai_parse_runs_source_message_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_revision_id"],
            ["source_message_revisions.id"],
            name="fk_ingestion_ai_parse_runs_source_message_revision_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_ingestion_ai_parse_runs_offer_id_offers",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_ai_parse_runs"),
    )
    op.create_index(
        "ix_ingestion_ai_parse_runs_owner_created",
        "ingestion_ai_parse_runs",
        ["owner_user_id", "created_at"],
    )
    op.create_index(
        "ix_ingestion_ai_parse_runs_revision_state",
        "ingestion_ai_parse_runs",
        ["source_message_revision_id", "state"],
    )
    op.create_index(
        "uq_ingestion_ai_parse_runs_pending_revision",
        "ingestion_ai_parse_runs",
        ["source_message_revision_id"],
        unique=True,
        postgresql_where=sa.text("state = 'pending'"),
    )


def downgrade() -> None:
    """Drop the ingestion AI parse schema."""
    op.drop_index(
        "uq_ingestion_ai_parse_runs_pending_revision",
        table_name="ingestion_ai_parse_runs",
    )
    op.drop_index(
        "ix_ingestion_ai_parse_runs_revision_state",
        table_name="ingestion_ai_parse_runs",
    )
    op.drop_index(
        "ix_ingestion_ai_parse_runs_owner_created",
        table_name="ingestion_ai_parse_runs",
    )
    op.drop_table("ingestion_ai_parse_runs")
