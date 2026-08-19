"""Add favorite locations keyed by account."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0010"
down_revision: str | None = "20260819_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive favorites schema."""
    op.create_table(
        "favorite_locations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_favorite_locations_location_id_locations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_favorite_locations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "location_id", name="pk_favorite_locations"),
    )
    op.create_index(
        "ix_favorite_locations_user_created",
        "favorite_locations",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the favorites schema."""
    op.drop_index("ix_favorite_locations_user_created", table_name="favorite_locations")
    op.drop_table("favorite_locations")
