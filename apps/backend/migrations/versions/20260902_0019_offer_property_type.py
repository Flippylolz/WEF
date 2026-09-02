"""Add offer property_type column with legacy unknown default."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0019"
down_revision: str | None = "20260901_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the closed property-type vocabulary to offers."""
    op.add_column(
        "offers",
        sa.Column(
            "property_type",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_check_constraint(
        "ck_offers_property_type",
        "offers",
        "property_type IN ('apartment', 'house', 'semi_detached', 'unknown')",
    )
    op.alter_column("offers", "property_type", server_default=None)


def downgrade() -> None:
    """Drop the offer property-type column."""
    op.drop_constraint("ck_offers_property_type", "offers", type_="check")
    op.drop_column("offers", "property_type")
