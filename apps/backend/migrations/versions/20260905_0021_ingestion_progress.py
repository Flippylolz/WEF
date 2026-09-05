"""Add monotonic channel progress and independently scheduled archive retries."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_0021"
down_revision: str | None = "20260905_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add state without resetting historical attempts or certifying unobserved history."""
    for name in ("data_failure_count", "deferral_count"):
        op.add_column(
            "telegram_raw_events", sa.Column(name, sa.Integer(), nullable=False, server_default="0")
        )
    op.add_column("telegram_raw_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column(
        "telegram_raw_events",
        sa.Column("retry_policy_version", sa.String(64), nullable=False, server_default=""),
    )
    op.create_table(
        "telegram_archive_exceptions",
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("telegram_raw_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "telegram_channel_progress",
        sa.Column(
            "source_channel_id",
            sa.Uuid(),
            sa.ForeignKey("source_channels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        *(
            sa.Column(name, sa.BigInteger(), nullable=False, server_default="0")
            for name in (
                "applied_high_water_id",
                "polled_through_id",
                "sweep_after_id",
                "sweep_upper_id",
            )
        ),
        sa.Column("sweep_token", sa.Uuid()),
        sa.Column("sweep_lease_until", sa.DateTime(timezone=True)),
        sa.Column("sweep_unknown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("history_limited", sa.Boolean(), nullable=False, server_default=sa.true()),
        *(
            sa.Column(name, sa.DateTime(timezone=True))
            for name in ("last_applied_at", "last_polled_at", "last_sweep_at", "source_retry_at")
        ),
        sa.CheckConstraint(
            "applied_high_water_id >= 0 AND polled_through_id >= 0 "
            "AND sweep_after_id >= 0 AND sweep_upper_id >= 0",
            name="ck_telegram_progress_nonnegative",
        ),
    )
    op.create_index(
        "ix_archive_due",
        "telegram_raw_events",
        ["channel_external_id", "next_attempt_at", "received_at", "id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    """Refuse to discard durable progress/retry evidence on an application rollback."""
    connection = op.get_bind()
    for table in ("telegram_channel_progress", "telegram_archive_exceptions"):
        if connection.scalar(sa.select(sa.exists().select_from(sa.table(table)))):
            msg = "ingestion progress evidence must be retained; roll forward"
            raise RuntimeError(msg)
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM telegram_raw_events "
            "WHERE data_failure_count > 0 OR deferral_count > 0 OR next_attempt_at IS NOT NULL)"
        )
    ):
        msg = "retry history must be retained; roll forward"
        raise RuntimeError(msg)
    op.drop_index("ix_archive_due", table_name="telegram_raw_events")
    op.drop_table("telegram_channel_progress")
    op.drop_table("telegram_archive_exceptions")
    for name in ("data_failure_count", "deferral_count", "next_attempt_at", "retry_policy_version"):
        op.drop_column("telegram_raw_events", name)
