"""SQLAlchemy mapping for offer AI enrichment provenance."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from wef_backend.features.admin.infrastructure.models import AdminBase


class OfferAiEnrichmentBatchRow(AdminBase):
    """Owner-authorized missing-field autofill cohort."""

    __tablename__ = "offer_ai_enrichment_batches"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'running', 'paused', 'completed', 'failed', "
            "'reverting', 'reverted')",
            name="ck_offer_ai_enrichment_batches_state",
        ),
        CheckConstraint(
            "model = 'openai/gpt-oss-20b'",
            name="ck_offer_ai_enrichment_batches_model",
        ),
        Index("ix_offer_ai_enrichment_batches_owner_state", "owner_user_id", "state"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    scope_json: Mapped[object] = mapped_column(JSONB)
    candidate_count: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16))
    checkpoint_ordinal: Mapped[int] = mapped_column(Integer)
    processed_count: Mapped[int] = mapped_column(Integer)
    applied_count: Mapped[int] = mapped_column(Integer)
    skipped_count: Mapped[int] = mapped_column(Integer)
    failed_count: Mapped[int] = mapped_column(Integer)
    failure_category: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfferAiEnrichmentItemRow(AdminBase):
    """Immutable batch-scope row for one offer."""

    __tablename__ = "offer_ai_enrichment_items"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'processing', 'succeeded', 'skipped', 'failed')",
            name="ck_offer_ai_enrichment_items_state",
        ),
        UniqueConstraint("batch_id", "offer_id", name="uq_offer_ai_enrichment_items_batch_offer"),
        UniqueConstraint(
            "batch_id",
            "ordinal",
            name="uq_offer_ai_enrichment_items_batch_ordinal",
        ),
        Index("ix_offer_ai_enrichment_items_batch_state", "batch_id", "state", "ordinal"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    ordinal: Mapped[int] = mapped_column(Integer)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16))
    outcome: Mapped[str | None] = mapped_column(String(32))
    attempt_count: Mapped[int] = mapped_column(Integer)
    provider_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfferAiFieldEventRow(AdminBase):
    """Append-only field lifecycle event without evidence text."""

    __tablename__ = "offer_ai_field_events"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('proposed', 'applied', 'skipped', 'invalidated', "
            "'rolled_back', 'parser_confirmed', 'parser_conflicting')",
            name="ck_offer_ai_field_events_outcome",
        ),
        Index("ix_offer_ai_field_events_offer_field", "offer_id", "field_name", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    batch_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    field_name: Mapped[str] = mapped_column(String(64))
    proposed_value: Mapped[object | None] = mapped_column(JSONB)
    applied_value: Mapped[object | None] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(64))
    source_message_revision_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    source_start: Mapped[int | None] = mapped_column(Integer)
    source_end: Mapped[int | None] = mapped_column(Integer)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64))
    parser_version: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[str | None] = mapped_column(String(16))
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    actor_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfferFieldOriginRow(AdminBase):
    """Current canonical origin for one offer field."""

    __tablename__ = "offer_field_origins"
    __table_args__ = (
        CheckConstraint(
            "origin IN ('parser', 'ai')",
            name="ck_offer_field_origins_origin",
        ),
        CheckConstraint(
            "state IN ('active', 'stale', 'conflicting')",
            name="ck_offer_field_origins_state",
        ),
        CheckConstraint(
            "(origin = 'ai' AND field_event_id IS NOT NULL) "
            "OR (origin = 'parser' AND field_event_id IS NULL)",
            name="ck_offer_field_origins_event_match",
        ),
    )

    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    origin: Mapped[str] = mapped_column(String(16))
    value_fingerprint: Mapped[str] = mapped_column(String(64))
    canonical_value: Mapped[object] = mapped_column(JSONB)
    source_revision_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    parser_version: Mapped[str | None] = mapped_column(String(40))
    field_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("offer_ai_field_events.id"),
    )
    state: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
