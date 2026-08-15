"""Add durable complete-import leases and hosted-provider budgets.

Revision ID: 20260815_0007
Revises: 20260815_0006
Create Date: 2026-08-15 09:31:46
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260815_0007"
down_revision: str | None = "20260815_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add fenced run/checkpoint state and globally durable provider reservations."""
    op.create_table(
        "complete_import_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_channel_id", sa.Uuid(), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("source_size", sa.BigInteger(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkpoint_json", JSONB(), nullable=True),
        sa.Column("counts_json", JSONB(), nullable=True),
        sa.Column("pause_reason", sa.String(length=40), nullable=True),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'paused', 'failed', 'succeeded')",
            name="ck_complete_import_runs_status",
        ),
        sa.CheckConstraint(
            "stage IN ('preflight', 'persistence', 'geocode', 'media', 'verify')",
            name="ck_complete_import_runs_stage",
        ),
        sa.CheckConstraint("fencing_token > 0", name="ck_complete_import_runs_positive_fence"),
        sa.CheckConstraint("source_size >= 0", name="ck_complete_import_runs_source_size"),
        sa.ForeignKeyConstraint(["source_channel_id"], ["source_channels.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_channel_id",
            "source_checksum",
            "pipeline_version",
            name="uq_complete_import_runs_identity",
        ),
    )
    op.create_index(
        "ix_complete_import_runs_lease",
        "complete_import_runs",
        ["status", "lease_expires_at"],
        unique=False,
    )
    op.create_table(
        "provider_daily_budgets",
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("budget_date", sa.Date(), nullable=False),
        sa.Column("account_identity", sa.String(length=64), nullable=False),
        sa.Column("used_attempts", sa.Integer(), nullable=False),
        sa.Column("last_not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("used_attempts >= 0", name="ck_provider_daily_budgets_used"),
        sa.PrimaryKeyConstraint("provider", "budget_date", "account_identity"),
    )
    op.create_table(
        "provider_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("complete_import_run_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("budget_date", sa.Date(), nullable=False),
        sa.Column("account_identity", sa.String(length=64), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('reserved', 'succeeded', 'no_result', 'transient', 'quota', 'failed')",
            name="ck_provider_attempts_status",
        ),
        sa.ForeignKeyConstraint(
            ["complete_import_run_id"], ["complete_import_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_attempts_run_reserved",
        "provider_attempts",
        ["complete_import_run_id", "reserved_at"],
        unique=False,
    )
    op.create_index(
        "ix_provider_attempts_budget",
        "provider_attempts",
        ["provider", "budget_date", "account_identity"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only the additive complete-import coordination schema."""
    op.drop_index("ix_provider_attempts_budget", table_name="provider_attempts")
    op.drop_index("ix_provider_attempts_run_reserved", table_name="provider_attempts")
    op.drop_table("provider_attempts")
    op.drop_table("provider_daily_budgets")
    op.drop_index("ix_complete_import_runs_lease", table_name="complete_import_runs")
    op.drop_table("complete_import_runs")
