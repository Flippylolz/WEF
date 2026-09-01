"""Add durable source message parse issue ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0017"
down_revision: str | None = "20260831_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create append-only parse issue rows for ingestion reporting."""
    op.create_table(
        "source_message_parse_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_channel_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_revision_id", sa.Uuid(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("ingest_run_id", sa.Uuid(), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("is_candidate", sa.Boolean(), nullable=False),
        sa.Column("signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issue_outcome", sa.String(length=32), nullable=False),
        sa.Column("message_outcome", sa.String(length=32), nullable=False),
        sa.Column("boundary_band", sa.String(length=40), nullable=False),
        sa.Column("signal_combination", sa.String(length=128), nullable=False),
        sa.Column("text_excerpt_redacted", sa.Text(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "issue_outcome IN ('parser_miss', 'parser_incomplete')",
            name="ck_source_message_parse_issues_issue_outcome",
        ),
        sa.CheckConstraint(
            (
                "message_outcome IN "
                "('created', 'unchanged', 'revised', 'skipped_non_candidate')"
            ),
            name="ck_source_message_parse_issues_message_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["source_channel_id"],
            ["source_channels.id"],
            name="fk_source_message_parse_issues_channel_id_source_channels",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["source_messages.id"],
            name="fk_source_message_parse_issues_message_id_source_messages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_revision_id"],
            ["source_message_revisions.id"],
            name="fk_source_message_parse_issues_revision_id_source_message_revisions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["ingest_runs.id"],
            name="fk_source_message_parse_issues_run_id_ingest_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_source_message_parse_issues_offer_id_offers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_message_parse_issues_created",
        "source_message_parse_issues",
        ["created_at"],
    )
    op.create_index(
        "ix_source_message_parse_issues_outcome_created",
        "source_message_parse_issues",
        ["issue_outcome", "created_at"],
    )


def downgrade() -> None:
    """Drop parse issue ledger."""
    op.drop_index(
        "ix_source_message_parse_issues_outcome_created",
        table_name="source_message_parse_issues",
    )
    op.drop_index(
        "ix_source_message_parse_issues_created",
        table_name="source_message_parse_issues",
    )
    op.drop_table("source_message_parse_issues")
