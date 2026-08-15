"""Create class-separated media storage, attempts, derivatives, and associations.

Revision ID: 20260815_0006
Revises: 20260815_0005
Create Date: 2026-08-15 06:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260815_0006"
down_revision: str | None = "20260815_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add replay-safe media persistence with storage-class constraints."""
    op.create_table(
        "stored_media_objects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_backend", sa.String(length=24), nullable=False),
        sa.Column("storage_key", sa.String(length=320), nullable=False),
        sa.Column("storage_class", sa.String(length=24), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "storage_class IN ('restricted_original', 'public_derivative')",
            name="ck_stored_media_objects_class",
        ),
        sa.CheckConstraint("byte_size >= 0", name="ck_stored_media_objects_size"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "storage_class", name="uq_stored_media_object_class_identity"),
        sa.UniqueConstraint(
            "storage_backend", "storage_key", name="uq_stored_media_objects_backend_key"
        ),
        sa.UniqueConstraint(
            "storage_backend",
            "storage_class",
            "checksum_sha256",
            "byte_size",
            name="uq_stored_media_objects_class_checksum",
        ),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("source_ordinal", sa.Integer(), nullable=False),
        sa.Column("source_descriptor_json", JSONB(), nullable=False),
        sa.Column("stored_object_id", sa.Uuid(), nullable=False),
        sa.Column("stored_object_storage_class", sa.String(length=24), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("source_ordinal >= 0", name="ck_media_assets_ordinal"),
        sa.CheckConstraint(
            "stored_object_storage_class = 'restricted_original'",
            name="ck_media_assets_restricted_class",
        ),
        sa.CheckConstraint("media_type IN ('image', 'video')", name="ck_media_assets_type"),
        sa.ForeignKeyConstraint(["source_message_id"], ["source_messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["stored_object_id", "stored_object_storage_class"],
            ["stored_media_objects.id", "stored_media_objects.storage_class"],
            name="fk_media_assets_restricted_object",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_message_id", "source_ordinal", name="uq_media_assets_source_ordinal"
        ),
    )
    op.create_table(
        "media_disposition_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.Uuid(), nullable=False),
        sa.Column("source_ordinal", sa.Integer(), nullable=False),
        sa.Column("source_message_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_descriptor_identity", sa.String(length=64), nullable=False),
        sa.Column("observation_status", sa.String(length=24), nullable=False),
        sa.Column("observation_reason_code", sa.String(length=40), nullable=False),
        sa.Column("observed_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("observed_byte_size", sa.BigInteger(), nullable=True),
        sa.Column("content_identity", sa.String(length=80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("verifier_version", sa.String(length=40), nullable=False),
        sa.Column("association_version", sa.String(length=40), nullable=False),
        sa.Column("disposition", sa.String(length=24), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_ordinal >= 0", name="ck_media_dispositions_ordinal"),
        sa.CheckConstraint("attempt_number > 0", name="ck_media_dispositions_attempt"),
        sa.CheckConstraint(
            "observation_status IN ('read_observed', 'unread_unavailable', 'unread_rejected')",
            name="ck_media_dispositions_observation",
        ),
        sa.CheckConstraint(
            "disposition IN ('stored', 'missing', 'rejected', 'unsupported', 'unassociated')",
            name="ck_media_dispositions_disposition",
        ),
        sa.CheckConstraint(
            "(observation_status = 'read_observed' AND observed_checksum_sha256 IS NOT NULL) "
            "OR (observation_status != 'read_observed' AND observed_checksum_sha256 IS NULL)",
            name="ck_media_dispositions_checksum_observation",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "source_message_revision_id"],
            ["source_message_revisions.source_message_id", "source_message_revisions.id"],
            name="fk_media_dispositions_revision_same_message",
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_message_id",
            "source_ordinal",
            "source_message_revision_id",
            "source_descriptor_identity",
            "content_identity",
            "verifier_version",
            "association_version",
            "attempt_number",
            name="uq_media_disposition_replay_attempt",
        ),
    )
    op.create_index(
        "ix_media_dispositions_source",
        "media_disposition_attempts",
        ["source_message_id", "source_ordinal"],
        unique=False,
    )
    op.create_table(
        "media_derivatives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("stored_object_id", sa.Uuid(), nullable=False),
        sa.Column("stored_object_storage_class", sa.String(length=24), nullable=False),
        sa.Column("variant", sa.String(length=40), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "stored_object_storage_class = 'public_derivative'",
            name="ck_media_derivatives_public_class",
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["stored_object_id", "stored_object_storage_class"],
            ["stored_media_objects.id", "stored_media_objects.storage_class"],
            name="fk_media_derivatives_public_object",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_asset_id", "variant", name="uq_media_derivatives_variant"),
    )
    op.create_table(
        "media_derivative_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("variant", sa.String(length=40), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("transform_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("source_object_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("media_derivative_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_media_derivative_attempts_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')",
            name="ck_media_derivative_attempts_status",
        ),
        sa.CheckConstraint(
            "(status = 'succeeded' AND media_derivative_id IS NOT NULL AND reason_code IS NULL) "
            "OR (status = 'failed' AND media_derivative_id IS NULL AND reason_code IS NOT NULL) "
            "OR (status = 'pending' AND media_derivative_id IS NULL AND reason_code IS NULL)",
            name="ck_media_derivative_attempts_terminal_shape",
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["media_derivative_id"], ["media_derivatives.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_asset_id",
            "variant",
            "attempt_number",
            name="uq_media_derivative_attempt_number",
        ),
    )
    op.create_table(
        "offer_media",
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("association_rule", sa.String(length=24), nullable=False),
        sa.Column("association_confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_offer_media_position"),
        sa.CheckConstraint(
            "association_rule IN "
            "('same_message', 'explicit_group', 'reply', 'time_burst', 'manual')",
            name="ck_offer_media_rule",
        ),
        sa.CheckConstraint(
            "association_confidence >= 0 AND association_confidence <= 1",
            name="ck_offer_media_confidence",
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("offer_id", "media_asset_id"),
        sa.UniqueConstraint("offer_id", "media_asset_id", name="uq_offer_media_asset"),
        sa.UniqueConstraint("offer_id", "position", name="uq_offer_media_position"),
    )


def downgrade() -> None:
    """Remove only the additive media schema when explicitly invoked."""
    op.drop_table("offer_media")
    op.drop_table("media_derivative_attempts")
    op.drop_table("media_derivatives")
    op.drop_index("ix_media_dispositions_source", table_name="media_disposition_attempts")
    op.drop_table("media_disposition_attempts")
    op.drop_table("media_assets")
    op.drop_table("stored_media_objects")
