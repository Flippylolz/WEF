"""Add encrypted contact points and minimized reveal audits."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0011"
down_revision: str | None = "20260820_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive contacts schema."""
    op.create_table(
        "contact_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value_ciphertext", sa.Text(), nullable=False),
        sa.Column("masked_value", sa.String(length=128), nullable=False),
        sa.Column("fingerprint_hmac", sa.String(length=64), nullable=False),
        sa.Column(
            "is_revealable",
            sa.Boolean(),
            server_default=sa.text("true"),
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
        sa.CheckConstraint(
            "kind IN ('phone', 'telegram')",
            name="ck_contact_points_kind",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_contact_points_offer_id_offers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contact_points"),
    )
    op.create_index(
        "ix_contact_points_offer_id",
        "contact_points",
        ["offer_id"],
        unique=False,
    )
    op.create_index(
        "uq_contact_points_offer_kind_fingerprint",
        "contact_points",
        ["offer_id", "kind", "fingerprint_hmac"],
        unique=True,
    )
    op.create_table(
        "contact_reveals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column("contact_set_version", sa.String(length=32), nullable=False),
        sa.Column(
            "revealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('allowed', 'rate_limited', 'forbidden', 'unavailable')",
            name="ck_contact_reveals_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_contact_reveals_offer_id_offers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_contact_reveals_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contact_reveals"),
    )
    op.create_index(
        "ix_contact_reveals_user_revealed",
        "contact_reveals",
        ["user_id", "revealed_at"],
        unique=False,
    )
    op.create_index(
        "ix_contact_reveals_offer_revealed",
        "contact_reveals",
        ["offer_id", "revealed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the contacts schema."""
    op.drop_index("ix_contact_reveals_offer_revealed", table_name="contact_reveals")
    op.drop_index("ix_contact_reveals_user_revealed", table_name="contact_reveals")
    op.drop_table("contact_reveals")
    op.drop_index(
        "uq_contact_points_offer_kind_fingerprint",
        table_name="contact_points",
    )
    op.drop_index("ix_contact_points_offer_id", table_name="contact_points")
    op.drop_table("contact_points")
