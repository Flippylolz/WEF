"""Create historical ingestion persistence schema.

Revision ID: 20260815_0004
Revises: 20260814_0003
Create Date: 2026-08-15 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260815_0004"
down_revision: str | None = "20260814_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the additive ingestion persistence schema."""
    op.create_table(
        "source_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=True),
        sa.Column("verified_link_base", sa.String(length=240), nullable=True),
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
            "platform IN ('telegram')",
            name="ck_source_channels_platform",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "external_id", name="uq_source_channels_identity"),
    )

    op.create_table(
        "source_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_channel_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("entities_json", JSONB(), nullable=False),
        sa.Column("raw_payload_json", JSONB(), nullable=False),
        sa.Column("raw_checksum", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_channel_id"],
            ["source_channels.id"],
            name="fk_source_messages_channel_id_source_channels",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_channel_id",
            "external_message_id",
            name="uq_source_messages_channel_message",
        ),
    )

    op.create_table(
        "source_message_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("entities_json", JSONB(), nullable=False),
        sa.Column("raw_payload_json", JSONB(), nullable=False),
        sa.Column("raw_checksum", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["source_messages.id"],
            name="fk_source_message_revisions_message_id_source_messages",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "revision_number > 0",
            name="ck_source_message_revisions_positive",
        ),
        sa.UniqueConstraint(
            "source_message_id",
            "revision_number",
            name="uq_source_message_revisions_number",
        ),
        sa.UniqueConstraint(
            "source_message_id",
            "id",
            name="uq_source_message_revisions_message_identity",
        ),
    )

    op.create_foreign_key(
        "fk_source_messages_current_revision_same_message",
        "source_messages",
        "source_message_revisions",
        ["id", "current_revision_id"],
        ["source_message_id", "id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "developments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("normalized_name", sa.String(length=160), nullable=False),
        sa.Column("name_confidence", sa.Numeric(precision=3, scale=2), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_developments_location_id_locations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("location_id", "normalized_name", name="uq_developments_location_name"),
    )
    op.create_index("ix_developments_location", "developments", ["location_id"], unique=False)

    op.create_table(
        "offer_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_revision_id", sa.Uuid(), nullable=False),
        sa.Column("relationship", sa.String(length=24), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("extraction_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_offer_sources_offer_id_offers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["source_messages.id"],
            name="fk_offer_sources_message_id_source_messages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "source_message_revision_id"],
            ["source_message_revisions.source_message_id", "source_message_revisions.id"],
            name="fk_offer_sources_revision_same_message",
        ),
        sa.CheckConstraint(
            "relationship IN ('primary', 'repost', 'update', 'possible_duplicate')",
            name="ck_offer_sources_relationship",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_offer_sources_confidence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "offer_id",
            "source_message_revision_id",
            name="uq_offer_sources_offer_revision",
        ),
    )
    op.create_index(
        "ix_offer_sources_message",
        "offer_sources",
        ["source_message_id"],
        unique=False,
    )
    op.create_index("ix_offer_sources_offer", "offer_sources", ["offer_id"], unique=False)

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_channel_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("checkpoint_json", JSONB(), nullable=True),
        sa.Column("counts_json", JSONB(), nullable=True),
        sa.Column("report_storage_key", sa.String(length=240), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_sha", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_channel_id"],
            ["source_channels.id"],
            name="fk_ingest_runs_channel_id_source_channels",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "mode IN ('dry_run', 'historical', 'reprocess', 'media_verify', 'live')",
            name="ck_ingest_runs_mode",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_ingest_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingest_runs_channel_started",
        "ingest_runs",
        ["source_channel_id", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the ingestion persistence schema when invoked explicitly."""
    op.drop_index("ix_ingest_runs_channel_started", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_index("ix_offer_sources_offer", table_name="offer_sources")
    op.drop_index("ix_offer_sources_message", table_name="offer_sources")
    op.drop_table("offer_sources")
    op.drop_index("ix_developments_location", table_name="developments")
    op.drop_table("developments")
    op.drop_constraint(
        "fk_source_messages_current_revision_same_message",
        "source_messages",
        type_="foreignkey",
    )
    op.drop_table("source_message_revisions")
    op.drop_table("source_messages")
    op.drop_table("source_channels")
