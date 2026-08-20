"""Add minimized owner administration audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0012"
down_revision: str | None = "20260820_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive admin audit schema."""
    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('allowed', 'denied', 'failed')",
            name="ck_admin_audit_events_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_admin_audit_events_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_admin_audit_events_target_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_admin_audit_events"),
    )
    op.create_index(
        "ix_admin_audit_events_owner_occurred",
        "admin_audit_events",
        ["owner_user_id", "occurred_at"],
    )
    op.create_index(
        "ix_admin_audit_events_target_occurred",
        "admin_audit_events",
        ["target_user_id", "occurred_at"],
    )


def downgrade() -> None:
    """Drop the admin audit schema."""
    op.drop_index(
        "ix_admin_audit_events_target_occurred",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_owner_occurred",
        table_name="admin_audit_events",
    )
    op.drop_table("admin_audit_events")
