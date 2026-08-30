"""SQLAlchemy mapping for minimized place AI review runs."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from wef_backend.features.admin.infrastructure.models import AdminBase


class PlaceAiReviewRunRow(AdminBase):
    """Expiring structured place-review run without prompt or source bodies."""

    __tablename__ = "place_ai_review_runs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'applied', 'expired', 'failed')",
            name="ck_place_ai_review_runs_state",
        ),
        CheckConstraint(
            "model = 'openai/gpt-oss-20b'",
            name="ck_place_ai_review_runs_model",
        ),
        CheckConstraint(
            "provider_outcome IN ("
            "'succeeded', 'timeout', 'refusal', 'quota', 'rate_limited', "
            "'network', 'schema', 'disabled')",
            name="ck_place_ai_review_runs_provider_outcome",
        ),
        CheckConstraint(
            "selected_source_count >= 0 AND omitted_source_count >= 0",
            name="ck_place_ai_review_runs_source_counts",
        ),
        Index("ix_place_ai_review_runs_owner_created", "owner_user_id", "created_at"),
        Index("ix_place_ai_review_runs_location_state", "location_id", "state"),
        Index(
            "uq_place_ai_review_runs_pending_location",
            "location_id",
            unique=True,
            postgresql_where=text("state = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    location_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    state: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    source_revision_ids: Mapped[object] = mapped_column(JSONB)
    source_checksums: Mapped[object] = mapped_column(JSONB)
    location_snapshot_version: Mapped[str] = mapped_column(String(64))
    proposed_fields: Mapped[object] = mapped_column(JSONB)
    verdict: Mapped[str | None] = mapped_column(String(32))
    warnings: Mapped[object] = mapped_column(JSONB)
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)
    provider_latency_ms: Mapped[int | None] = mapped_column(Integer)
    provider_outcome: Mapped[str] = mapped_column(String(32))
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    selected_source_count: Mapped[int] = mapped_column(Integer)
    omitted_source_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_fields: Mapped[object] = mapped_column(JSONB)
