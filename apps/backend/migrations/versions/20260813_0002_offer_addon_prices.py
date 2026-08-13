"""Add parking and storage price components to offers.

Revision ID: 20260813_0002
Revises: 20260812_0001
Create Date: 2026-08-13 18:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0002"
down_revision: str | None = "20260812_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add independently displayable parking and storage prices."""
    op.add_column(
        "offers",
        sa.Column("parking_price_min_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "offers",
        sa.Column("parking_price_max_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "offers",
        sa.Column(
            "parking_included_in_price",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "offers",
        sa.Column("storage_price_min_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "offers",
        sa.Column("storage_price_max_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "offers",
        sa.Column(
            "storage_included_in_price",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_offers_parking_price_range",
        "offers",
        "(parking_price_min_minor IS NULL AND parking_price_max_minor IS NULL) "
        "OR (parking_price_min_minor IS NOT NULL "
        "AND parking_price_max_minor IS NOT NULL "
        "AND parking_price_min_minor >= 0 "
        "AND parking_price_min_minor <= parking_price_max_minor)",
    )
    op.create_check_constraint(
        "ck_offers_parking_included_without_amount",
        "offers",
        "NOT parking_included_in_price "
        "OR (parking_price_min_minor IS NULL AND parking_price_max_minor IS NULL)",
    )
    op.create_check_constraint(
        "ck_offers_storage_price_range",
        "offers",
        "(storage_price_min_minor IS NULL AND storage_price_max_minor IS NULL) "
        "OR (storage_price_min_minor IS NOT NULL "
        "AND storage_price_max_minor IS NOT NULL "
        "AND storage_price_min_minor >= 0 "
        "AND storage_price_min_minor <= storage_price_max_minor)",
    )
    op.create_check_constraint(
        "ck_offers_storage_included_without_amount",
        "offers",
        "NOT storage_included_in_price "
        "OR (storage_price_min_minor IS NULL AND storage_price_max_minor IS NULL)",
    )

    synthetic_prices = (
        ("20000000-0000-4000-8000-000000000001", 4_500_000, 1_200_000, False),
        ("20000000-0000-4000-8000-000000000002", 7_500_000, 1_200_000, False),
        ("20000000-0000-4000-8000-000000000003", 3_000_000, None, True),
        ("20000000-0000-4000-8000-000000000004", 5_000_000, 2_500_000, False),
    )
    statement = sa.text(
        "UPDATE offers SET "
        "parking_price_min_minor = :parking_price, "
        "parking_price_max_minor = :parking_price, "
        "storage_price_min_minor = :storage_price, "
        "storage_price_max_minor = :storage_price, "
        "storage_included_in_price = :storage_included "
        "WHERE id = CAST(:offer_id AS uuid) "
        "AND parser_version = 'synthetic-m1-v1'",
    )
    for offer_id, parking_price, storage_price, storage_included in synthetic_prices:
        op.execute(
            statement.bindparams(
                offer_id=offer_id,
                parking_price=parking_price,
                storage_price=storage_price,
                storage_included=storage_included,
            ),
        )


def downgrade() -> None:
    """Remove add-on price components when explicitly requested."""
    op.drop_constraint(
        "ck_offers_storage_included_without_amount",
        "offers",
        type_="check",
    )
    op.drop_constraint("ck_offers_storage_price_range", "offers", type_="check")
    op.drop_constraint(
        "ck_offers_parking_included_without_amount",
        "offers",
        type_="check",
    )
    op.drop_constraint("ck_offers_parking_price_range", "offers", type_="check")
    op.drop_column("offers", "storage_included_in_price")
    op.drop_column("offers", "storage_price_max_minor")
    op.drop_column("offers", "storage_price_min_minor")
    op.drop_column("offers", "parking_included_in_price")
    op.drop_column("offers", "parking_price_max_minor")
    op.drop_column("offers", "parking_price_min_minor")
