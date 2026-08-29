"""Add bounded account visits and viewed-offer history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_0013"
down_revision: str | None = "20260820_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create additive account visit and viewed-offer tables."""
    op.create_table(
        "account_visits",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_visit_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_visits_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "visit_id", name="pk_account_visits"),
    )
    op.create_index(
        "ix_account_visits_user_started",
        "account_visits",
        ["user_id", "started_at"],
    )
    op.create_table(
        "viewed_offers",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("view_count", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "view_count >= 1",
            name="ck_viewed_offers_count_positive",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_viewed_offers_offer_id_offers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_viewed_offers_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "offer_id", name="pk_viewed_offers"),
    )
    op.create_index(
        "ix_viewed_offers_user_last_viewed",
        "viewed_offers",
        ["user_id", "last_viewed_at"],
    )


def downgrade() -> None:
    """Drop only view-history tables and indexes."""
    op.drop_index("ix_viewed_offers_user_last_viewed", table_name="viewed_offers")
    op.drop_table("viewed_offers")
    op.drop_index("ix_account_visits_user_started", table_name="account_visits")
    op.drop_table("account_visits")
