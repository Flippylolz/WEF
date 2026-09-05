"""Add original-event receipts, source tombstones, and bounded archive recovery."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260905_0020"
down_revision: str | None = "20260902_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add evidence without altering or deleting retained source payloads."""
    op.create_table(
        "telegram_source_tombstones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_channel_id",
            sa.Uuid(),
            sa.ForeignKey("source_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_channel_id", "external_message_id"),
    )
    op.create_table(
        "telegram_archive_resolutions",
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("telegram_raw_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("disposition", sa.String(24), nullable=False),
        sa.Column("source_checksum", sa.String(64), nullable=False),
        sa.Column(
            "source_revision_id",
            sa.Uuid(),
            sa.ForeignKey("source_message_revisions.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "tombstone_id",
            sa.Uuid(),
            sa.ForeignKey("telegram_source_tombstones.id", ondelete="CASCADE"),
        ),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_outcome", sa.String(24)),
        sa.Column("previous_attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "disposition IN ('applied', 'already_canonical', 'non_candidate', "
            "'superseded', 'deleted')",
            name="ck_archive_resolution_disposition",
        ),
        sa.CheckConstraint(
            "(disposition = 'deleted' AND tombstone_id IS NOT NULL) OR "
            "(disposition = 'non_candidate') OR "
            "(disposition IN ('applied', 'already_canonical', 'superseded') "
            "AND source_revision_id IS NOT NULL)",
            name="ck_archive_resolution_evidence",
        ),
    )
    op.create_table(
        "telegram_archive_recovery",
        sa.Column("channel_external_id", sa.String(64), primary_key=True),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("canary_ids", postgresql.JSONB(), nullable=False),
        sa.Column("baseline_count", sa.BigInteger(), nullable=False),
        sa.Column("pause_reason", sa.String(64)),
        sa.Column("next_batch_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "phase IN ('canary', 'running', 'paused')", name="ck_archive_recovery_phase"
        ),
    )
    op.create_index(
        "ix_archive_channel_pending",
        "telegram_raw_events",
        ["channel_external_id", "received_at", "id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    """Permit an empty-schema rehearsal; never discard populated recovery evidence."""
    connection = op.get_bind()
    for table in (
        "telegram_archive_resolutions",
        "telegram_source_tombstones",
        "telegram_archive_recovery",
    ):
        if connection.scalar(sa.select(sa.exists().select_from(sa.table(table)))):
            msg = "archive recovery evidence must be retained; pause draining and roll forward"
            raise RuntimeError(msg)
    op.drop_index("ix_archive_channel_pending", table_name="telegram_raw_events")
    op.drop_table("telegram_archive_resolutions")
    op.drop_table("telegram_source_tombstones")
    op.drop_table("telegram_archive_recovery")
