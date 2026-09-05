"""Add source-evidence evaluation identity and retained issue lifecycle."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260905_0021"
down_revision: str | None = "20260905_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep legacy issues intact and begin independent versioned evaluation."""
    op.create_table(
        "parse_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_message_id",
            sa.Uuid(),
            sa.ForeignKey("source_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_message_revision_id",
            sa.Uuid(),
            sa.ForeignKey("source_message_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parser_version", sa.String(40), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("recovery_eligible", sa.Boolean(), nullable=False),
        sa.Column("fields_json", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_message_revision_id",
            "parser_version",
            "policy_version",
            name="uq_parse_evaluation_identity",
        ),
        sa.CheckConstraint(
            "state IN ('open', 'resolved', 'superseded')", name="ck_parse_evaluation_state"
        ),
    )
    op.create_index(
        "ix_parse_evaluations_message", "parse_evaluations", ["source_message_id", "created_at"]
    )
    op.create_table(
        "parse_evaluation_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey("parse_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "caused_by_id",
            sa.Uuid(),
            sa.ForeignKey("parse_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("evaluation_id", "caused_by_id", name="uq_parse_evaluation_transition"),
    )


def downgrade() -> None:
    """Remove evaluation metadata only; ordinary runtime rollback retains it."""
    op.drop_table("parse_evaluation_transitions")
    op.drop_table("parse_evaluations")
