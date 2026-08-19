"""Add catalog query indexes identified by the E12 audit."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0009"
down_revision: str | None = "20260815_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create additive indexes for location offer pages and price filtering."""
    op.create_index(
        "ix_offers_location_visible_published",
        "offers",
        ["location_id", "visibility", "published_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_offers_visible_price_range",
        "offers",
        ["visibility", "price_min_minor", "price_max_minor"],
        unique=False,
        postgresql_where=sa.text("visibility = 'visible'"),
    )


def downgrade() -> None:
    """Drop only the E12 catalog indexes."""
    op.drop_index("ix_offers_visible_price_range", table_name="offers")
    op.drop_index("ix_offers_location_visible_published", table_name="offers")
