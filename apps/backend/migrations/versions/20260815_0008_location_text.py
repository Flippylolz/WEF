"""Preserve source-derived location text without truncation.

Revision ID: 20260815_0008
Revises: 20260815_0007
Create Date: 2026-08-15 15:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0008"
down_revision: str | None = "20260815_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Widen location text fields so complete imports preserve source values."""
    op.alter_column(
        "locations",
        "display_name",
        existing_type=sa.String(length=160),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "locations",
        "display_address",
        existing_type=sa.String(length=240),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "locations",
        "normalized_address",
        existing_type=sa.String(length=240),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore legacy limits, failing safely if rows no longer fit."""
    op.alter_column(
        "locations",
        "normalized_address",
        existing_type=sa.Text(),
        type_=sa.String(length=240),
        existing_nullable=False,
    )
    op.alter_column(
        "locations",
        "display_address",
        existing_type=sa.Text(),
        type_=sa.String(length=240),
        existing_nullable=False,
    )
    op.alter_column(
        "locations",
        "display_name",
        existing_type=sa.Text(),
        type_=sa.String(length=160),
        existing_nullable=False,
    )
