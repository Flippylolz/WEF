"""Add batch offer enrichment provenance tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0016"
down_revision: str | None = "20260830_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH_STATES = (
    "queued",
    "running",
    "paused",
    "completed",
    "failed",
    "reverting",
    "reverted",
)
_ITEM_STATES = ("queued", "processing", "succeeded", "skipped", "failed")
_ITEM_OUTCOMES = (
    "applied",
    "no_missing",
    "no_evidence",
    "conflict",
    "invalid",
    "stale",
    "below_threshold",
    "provider_failed",
    "disabled",
)
_EVENT_OUTCOMES = (
    "proposed",
    "applied",
    "skipped",
    "invalidated",
    "rolled_back",
    "parser_confirmed",
    "parser_conflicting",
)
_ORIGIN_KINDS = ("parser", "ai")
_ORIGIN_STATES = ("active", "stale", "conflicting")
_FIELD_NAMES = (
    "market_type",
    "currency",
    "apartment_price_min",
    "apartment_price_max",
    "parking_price_min",
    "parking_price_max",
    "parking_included_in_price",
    "storage_price_min",
    "storage_price_max",
    "storage_included_in_price",
    "area_min_sqm",
    "area_max_sqm",
    "rooms_min",
    "rooms_max",
    "floor_label",
    "delivery_label",
)


def upgrade() -> None:
    """Create additive offer AI enrichment provenance tables."""
    op.create_table(
        "offer_ai_enrichment_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("checkpoint_ordinal", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("applied_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("failure_category", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{item}'" for item in _BATCH_STATES) + ")",
            name="ck_offer_ai_enrichment_batches_state",
        ),
        sa.CheckConstraint(
            "model = 'openai/gpt-oss-20b'",
            name="ck_offer_ai_enrichment_batches_model",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0 AND candidate_count <= 200",
            name="ck_offer_ai_enrichment_batches_candidate_count",
        ),
        sa.CheckConstraint(
            "checkpoint_ordinal >= 0 AND processed_count >= 0 "
            "AND applied_count >= 0 AND skipped_count >= 0 AND failed_count >= 0",
            name="ck_offer_ai_enrichment_batches_counts",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_offer_ai_enrichment_batches_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_offer_ai_enrichment_batches"),
    )
    op.create_index(
        "ix_offer_ai_enrichment_batches_owner_state",
        "offer_ai_enrichment_batches",
        ["owner_user_id", "state"],
    )
    op.create_table(
        "offer_ai_enrichment_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("provider_called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{item}'" for item in _ITEM_STATES) + ")",
            name="ck_offer_ai_enrichment_items_state",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ("
            + ", ".join(f"'{item}'" for item in _ITEM_OUTCOMES)
            + ")",
            name="ck_offer_ai_enrichment_items_outcome",
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND attempt_count >= 0",
            name="ck_offer_ai_enrichment_items_counts",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["offer_ai_enrichment_batches.id"],
            name="fk_offer_ai_enrichment_items_batch_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_offer_ai_enrichment_items_offer_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_offer_ai_enrichment_items"),
        sa.UniqueConstraint(
            "batch_id",
            "offer_id",
            name="uq_offer_ai_enrichment_items_batch_offer",
        ),
        sa.UniqueConstraint(
            "batch_id",
            "ordinal",
            name="uq_offer_ai_enrichment_items_batch_ordinal",
        ),
    )
    op.create_index(
        "ix_offer_ai_enrichment_items_batch_state",
        "offer_ai_enrichment_items",
        ["batch_id", "state", "ordinal"],
    )
    op.create_table(
        "offer_ai_field_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("batch_item_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("proposed_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("applied_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("source_message_revision_id", sa.Uuid(), nullable=True),
        sa.Column("source_start", sa.Integer(), nullable=True),
        sa.Column("source_end", sa.Integer(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("token_input", sa.Integer(), nullable=True),
        sa.Column("token_output", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN (" + ", ".join(f"'{item}'" for item in _EVENT_OUTCOMES) + ")",
            name="ck_offer_ai_field_events_outcome",
        ),
        sa.CheckConstraint(
            "field_name IN (" + ", ".join(f"'{item}'" for item in _FIELD_NAMES) + ")",
            name="ck_offer_ai_field_events_field_name",
        ),
        sa.CheckConstraint(
            "source_start IS NULL OR (source_start >= 0 AND source_end > source_start)",
            name="ck_offer_ai_field_events_offsets",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["offer_ai_enrichment_batches.id"],
            name="fk_offer_ai_field_events_batch_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_item_id"],
            ["offer_ai_enrichment_items.id"],
            name="fk_offer_ai_field_events_batch_item_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_offer_ai_field_events_offer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_revision_id"],
            ["source_message_revisions.id"],
            name="fk_offer_ai_field_events_revision_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_offer_ai_field_events"),
    )
    op.create_index(
        "ix_offer_ai_field_events_offer_field",
        "offer_ai_field_events",
        ["offer_id", "field_name", "created_at"],
    )
    op.create_table(
        "offer_field_origins",
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("value_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("canonical_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=True),
        sa.Column("field_event_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "origin IN (" + ", ".join(f"'{item}'" for item in _ORIGIN_KINDS) + ")",
            name="ck_offer_field_origins_origin",
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{item}'" for item in _ORIGIN_STATES) + ")",
            name="ck_offer_field_origins_state",
        ),
        sa.CheckConstraint(
            "field_name IN (" + ", ".join(f"'{item}'" for item in _FIELD_NAMES) + ")",
            name="ck_offer_field_origins_field_name",
        ),
        sa.CheckConstraint(
            "(origin = 'ai' AND field_event_id IS NOT NULL) "
            "OR (origin = 'parser' AND field_event_id IS NULL)",
            name="ck_offer_field_origins_event_match",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name="fk_offer_field_origins_offer_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["field_event_id"],
            ["offer_ai_field_events.id"],
            name="fk_offer_field_origins_field_event_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_revision_id"],
            ["source_message_revisions.id"],
            name="fk_offer_field_origins_revision_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "offer_id",
            "field_name",
            name="pk_offer_field_origins",
        ),
    )


def downgrade() -> None:
    """Drop offer AI enrichment provenance tables."""
    op.drop_table("offer_field_origins")
    op.drop_index("ix_offer_ai_field_events_offer_field", table_name="offer_ai_field_events")
    op.drop_table("offer_ai_field_events")
    op.drop_index(
        "ix_offer_ai_enrichment_items_batch_state",
        table_name="offer_ai_enrichment_items",
    )
    op.drop_table("offer_ai_enrichment_items")
    op.drop_index(
        "ix_offer_ai_enrichment_batches_owner_state",
        table_name="offer_ai_enrichment_batches",
    )
    op.drop_table("offer_ai_enrichment_batches")
