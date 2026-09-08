"""Track newly canonical owners independently of the chronological media scan."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0027"
down_revision: str | None = "20260906_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a discovery receipt; existing galleries and work remain untouched."""
    op.add_column(
        "offer_sources",
        sa.Column(
            "media_recovery_discovered", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        "ix_offer_sources_media_undiscovered",
        "offer_sources",
        ["source_message_id"],
        postgresql_where=sa.text("relationship = 'primary' AND NOT media_recovery_discovered"),
    )


def downgrade() -> None:
    """Remove only discovery metadata, retaining every source and media asset."""
    op.drop_index("ix_offer_sources_media_undiscovered", table_name="offer_sources")
    op.drop_column("offer_sources", "media_recovery_discovered")
