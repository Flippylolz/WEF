"""Create pseudonymous accounts and opaque auth sessions.

Revision ID: 20260814_0003
Revises: 20260813_0002
Create Date: 2026-08-14 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0003"
down_revision: str | None = "20260813_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive identity schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username_normalized", sa.String(length=64), nullable=False),
        sa.Column("username_display", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "must_change_password",
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('user', 'owner')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username_normalized", name="uq_users_username_normalized"),
    )
    op.create_index(
        "ix_users_role_active",
        "users",
        ["role", "is_active"],
        unique=False,
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_auth_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_sessions_user_active",
        "auth_sessions",
        ["user_id", "revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the identity schema when invoked explicitly."""
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_role_active", table_name="users")
    op.drop_table("users")
