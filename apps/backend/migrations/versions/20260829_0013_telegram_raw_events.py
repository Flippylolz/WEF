"""Add the verbatim Telegram raw-event archive."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_0013"
down_revision: str | None = "20260820_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive raw-event archive schema."""
    op.create_table(
        "telegram_raw_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_kind", sa.String(length=16), nullable=False),
        sa.Column("channel_external_id", sa.String(length=64), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=24), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_telegram_raw_events"),
        sa.CheckConstraint(
            "event_kind IN ('new', 'edit', 'delete')",
            name="ck_telegram_raw_events_kind",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('processed', 'failed', 'skipped_non_candidate')",
            name="ck_telegram_raw_events_outcome",
        ),
        sa.UniqueConstraint(
            "channel_external_id",
            "external_message_id",
            "event_kind",
            "checksum",
            name="uq_telegram_raw_events_dedupe",
        ),
    )
    op.create_index(
        "ix_telegram_raw_events_pending",
        "telegram_raw_events",
        ["received_at"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    """Drop the raw-event archive; landed-but-unprocessed events are re-landable."""
    op.drop_index("ix_telegram_raw_events_pending", table_name="telegram_raw_events")
    op.drop_table("telegram_raw_events")
