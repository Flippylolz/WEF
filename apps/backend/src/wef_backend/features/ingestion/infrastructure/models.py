"""SQLAlchemy mappings for historical ingestion persistence."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from decimal import Decimal  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement  # noqa: TC002 - resolved by SQLAlchemy
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class IngestionBase(DeclarativeBase):
    """Declarative metadata owned by ingestion infrastructure."""


class SourceChannelRow(IngestionBase):
    """One Telegram source channel by stable platform identity."""

    __tablename__ = "source_channels"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_source_channels_identity"),
        CheckConstraint(
            "platform IN ('telegram')",
            name="ck_source_channels_platform",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    platform: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(160))
    username: Mapped[str | None] = mapped_column(String(80))
    verified_link_base: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SourceMessageRevisionRow(IngestionBase):
    """Immutable complete snapshot of one source message version."""

    __tablename__ = "source_message_revisions"
    __table_args__ = (
        UniqueConstraint(
            "source_message_id",
            "revision_number",
            name="uq_source_message_revisions_number",
        ),
        UniqueConstraint(
            "source_message_id",
            "id",
            name="uq_source_message_revisions_message_identity",
        ),
        CheckConstraint("revision_number > 0", name="ck_source_message_revisions_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_messages.id", ondelete="CASCADE"),
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message_type: Mapped[str] = mapped_column(String(32))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text_original: Mapped[str] = mapped_column(Text)
    entities_json: Mapped[object] = mapped_column(JSONB)
    raw_payload_json: Mapped[object] = mapped_column(JSONB)
    raw_checksum: Mapped[str] = mapped_column(String(64))


class SourceMessageRow(IngestionBase):
    """Current projection of one source message with its live revision pointer."""

    __tablename__ = "source_messages"
    __table_args__ = (
        UniqueConstraint(
            "source_channel_id",
            "external_message_id",
            name="uq_source_messages_channel_message",
        ),
        ForeignKeyConstraint(
            ["id", "current_revision_id"],
            ["source_message_revisions.source_message_id", "source_message_revisions.id"],
            name="fk_source_messages_current_revision_same_message",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_channels.id", ondelete="RESTRICT"),
    )
    external_message_id: Mapped[int] = mapped_column(BigInteger)
    current_revision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    message_type: Mapped[str] = mapped_column(String(32))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text_original: Mapped[str] = mapped_column(Text)
    entities_json: Mapped[object] = mapped_column(JSONB)
    raw_payload_json: Mapped[object] = mapped_column(JSONB)
    raw_checksum: Mapped[str] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DevelopmentRow(IngestionBase):
    """Named project evidenced by the source, grouped under one location."""

    __tablename__ = "developments"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "normalized_name",
            name="uq_developments_location_name",
        ),
        Index("ix_developments_location", "location_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    location_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    display_name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(160))
    name_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfferSourceRow(IngestionBase):
    """Revision-anchored exact relationship between an offer and its source."""

    __tablename__ = "offer_sources"
    __table_args__ = (
        UniqueConstraint(
            "offer_id",
            "source_message_revision_id",
            name="uq_offer_sources_offer_revision",
        ),
        ForeignKeyConstraint(
            ["source_message_id", "source_message_revision_id"],
            ["source_message_revisions.source_message_id", "source_message_revisions.id"],
            name="fk_offer_sources_revision_same_message",
        ),
        CheckConstraint(
            "relationship IN ('primary', 'repost', 'update', 'possible_duplicate')",
            name="ck_offer_sources_relationship",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_offer_sources_confidence",
        ),
        Index("ix_offer_sources_message", "source_message_id"),
        Index("ix_offer_sources_offer", "offer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    source_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_messages.id", ondelete="RESTRICT"),
    )
    source_message_revision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_message_revisions.id", ondelete="RESTRICT"),
    )
    relationship: Mapped[str] = mapped_column(String(24))
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    extraction_json: Mapped[object] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IngestRunRow(IngestionBase):
    """One reconciled ingestion run with its resumable checkpoint."""

    __tablename__ = "ingest_runs"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('dry_run', 'historical', 'reprocess', 'media_verify', 'live')",
            name="ck_ingest_runs_mode",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_ingest_runs_status",
        ),
        Index("ix_ingest_runs_channel_started", "source_channel_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_channels.id", ondelete="RESTRICT"),
    )
    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    source_checksum: Mapped[str | None] = mapped_column(String(64))
    parser_version: Mapped[str] = mapped_column(String(40))
    checkpoint_json: Mapped[object | None] = mapped_column(JSONB)
    counts_json: Mapped[object | None] = mapped_column(JSONB)
    report_storage_key: Mapped[str | None] = mapped_column(String(240))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_sha: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(Text)


class CompleteImportRunRow(IngestionBase):
    """Durable fenced state for one exact source/pipeline import."""

    __tablename__ = "complete_import_runs"
    __table_args__ = (
        UniqueConstraint(
            "source_channel_id",
            "source_checksum",
            "pipeline_version",
            name="uq_complete_import_runs_identity",
        ),
        CheckConstraint(
            "status IN ('running', 'paused', 'failed', 'succeeded')",
            name="ck_complete_import_runs_status",
        ),
        CheckConstraint(
            "stage IN ('preflight', 'persistence', 'geocode', 'media', 'verify')",
            name="ck_complete_import_runs_stage",
        ),
        CheckConstraint("fencing_token > 0", name="ck_complete_import_runs_positive_fence"),
        CheckConstraint("source_size >= 0", name="ck_complete_import_runs_source_size"),
        Index("ix_complete_import_runs_lease", "status", "lease_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_channels.id", ondelete="RESTRICT"),
    )
    source_checksum: Mapped[str] = mapped_column(String(64))
    source_size: Mapped[int] = mapped_column(BigInteger)
    pipeline_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16))
    stage: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[str] = mapped_column(String(64))
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checkpoint_json: Mapped[object | None] = mapped_column(JSONB)
    counts_json: Mapped[object | None] = mapped_column(JSONB)
    pause_reason: Mapped[str | None] = mapped_column(String(40))
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderDailyBudgetRow(IngestionBase):
    """Cross-process daily provider budget and globally spaced call slot."""

    __tablename__ = "provider_daily_budgets"
    __table_args__ = (CheckConstraint("used_attempts >= 0", name="ck_provider_daily_budgets_used"),)

    provider: Mapped[str] = mapped_column(String(24), primary_key=True)
    budget_date: Mapped[date] = mapped_column(Date, primary_key=True)
    account_identity: Mapped[str] = mapped_column(String(64), primary_key=True)
    used_attempts: Mapped[int] = mapped_column(Integer)
    last_not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProviderAttemptRow(IngestionBase):
    """Non-sensitive ledger for every reserved hosted-provider attempt."""

    __tablename__ = "provider_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'succeeded', 'no_result', 'transient', 'quota', 'failed')",
            name="ck_provider_attempts_status",
        ),
        Index("ix_provider_attempts_run_reserved", "complete_import_run_id", "reserved_at"),
        Index("ix_provider_attempts_budget", "provider", "budget_date", "account_identity"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    complete_import_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("complete_import_runs.id", ondelete="CASCADE"),
    )
    provider: Mapped[str] = mapped_column(String(24))
    budget_date: Mapped[date] = mapped_column(Date)
    account_identity: Mapped[str] = mapped_column(String(64))
    query_hash: Mapped[str] = mapped_column(String(64))
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    error_code: Mapped[str | None] = mapped_column(String(32))
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GeocodeResultRow(IngestionBase):
    """Provider-neutral durable query cache and audit result."""

    __tablename__ = "geocode_results"
    __table_args__ = (
        CheckConstraint(
            "precision IN ('building', 'street', 'district', 'city', 'unknown')",
            name="ck_geocode_results_precision",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_geocode_results_confidence",
        ),
        CheckConstraint(
            "(point IS NULL) = (within_scope IS NULL OR error_code IS NOT NULL)",
            name="ck_geocode_results_point_scope",
        ),
        Index("ix_geocode_results_provider_attempted", "provider", "attempted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    query_hash: Mapped[str] = mapped_column(String(64), unique=True)
    query_original: Mapped[str] = mapped_column(String(240))
    query_normalized: Mapped[str] = mapped_column(String(240))
    normalizer_version: Mapped[str] = mapped_column(String(40))
    scope_version: Mapped[str] = mapped_column(String(40))
    request_version: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(24))
    provider_result_id: Mapped[str | None] = mapped_column(String(240))
    point: Mapped[WKBElement | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
    )
    display_name: Mapped[str | None] = mapped_column(String(320))
    precision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    within_scope: Mapped[bool | None]
    response_json: Mapped[object] = mapped_column(JSONB)
    attribution_text: Mapped[str] = mapped_column(String(320))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(32))


class GeocodeMissClaimRow(IngestionBase):
    """Fenced cross-process ownership of an identical cache miss."""

    __tablename__ = "geocode_miss_claims"
    __table_args__ = (
        CheckConstraint("fencing_token > 0", name="ck_geocode_claims_positive_fence"),
        Index("ix_geocode_claims_lease_expiry", "lease_expires_at"),
    )

    query_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64))
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_geocode_result_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("geocode_results.id", ondelete="SET NULL"),
    )


class LocationGeocodeSelectionRow(IngestionBase):
    """Append-only location review and selected-result lineage."""

    __tablename__ = "location_geocode_selections"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "selection_version",
            name="uq_location_geocode_selection_version",
        ),
        CheckConstraint("selection_version > 0", name="ck_location_selections_version"),
        CheckConstraint(
            "from_state IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_location_selections_from_state",
        ),
        CheckConstraint(
            "to_state IN ('accepted', 'needs_review', 'rejected', 'ungeocoded')",
            name="ck_location_selections_to_state",
        ),
        Index("ix_location_geocode_selections_location", "location_id", "decided_at"),
        Index("ix_location_geocode_selections_result", "geocode_result_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    location_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    geocode_result_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("geocode_results.id", ondelete="RESTRICT"),
    )
    from_state: Mapped[str] = mapped_column(String(16))
    to_state: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(40))
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str | None] = mapped_column(String(160))
    review_policy_version: Mapped[str] = mapped_column(String(40))
    selection_version: Mapped[int] = mapped_column(Integer)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StoredMediaObjectRow(IngestionBase):
    """Class-scoped verified physical media object."""

    __tablename__ = "stored_media_objects"
    __table_args__ = (
        UniqueConstraint("id", "storage_class", name="uq_stored_media_object_class_identity"),
        UniqueConstraint(
            "storage_backend",
            "storage_key",
            name="uq_stored_media_objects_backend_key",
        ),
        UniqueConstraint(
            "storage_backend",
            "storage_class",
            "checksum_sha256",
            "byte_size",
            name="uq_stored_media_objects_class_checksum",
        ),
        CheckConstraint(
            "storage_class IN ('restricted_original', 'public_derivative')",
            name="ck_stored_media_objects_class",
        ),
        CheckConstraint("byte_size >= 0", name="ck_stored_media_objects_size"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    storage_backend: Mapped[str] = mapped_column(String(24))
    storage_key: Mapped[str] = mapped_column(String(320))
    storage_class: Mapped[str] = mapped_column(String(24))
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(80))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MediaAssetRow(IngestionBase):
    """Source-owned logical media item referencing a restricted object."""

    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint(
            "source_message_id",
            "source_ordinal",
            name="uq_media_assets_source_ordinal",
        ),
        ForeignKeyConstraint(
            ["stored_object_id", "stored_object_storage_class"],
            ["stored_media_objects.id", "stored_media_objects.storage_class"],
            name="fk_media_assets_restricted_object",
            ondelete="RESTRICT",
        ),
        CheckConstraint("source_ordinal >= 0", name="ck_media_assets_ordinal"),
        CheckConstraint(
            "stored_object_storage_class = 'restricted_original'",
            name="ck_media_assets_restricted_class",
        ),
        CheckConstraint("media_type IN ('image', 'video')", name="ck_media_assets_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_messages.id", ondelete="RESTRICT"),
    )
    source_ordinal: Mapped[int] = mapped_column(Integer)
    source_descriptor_json: Mapped[object] = mapped_column(JSONB)
    stored_object_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    stored_object_storage_class: Mapped[str] = mapped_column(String(24))
    media_type: Mapped[str] = mapped_column(String(16))
    mime_type: Mapped[str] = mapped_column(String(80))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MediaDispositionAttemptRow(IngestionBase):
    """Versioned read/unread original disposition attempt."""

    __tablename__ = "media_disposition_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_message_id", "source_message_revision_id"],
            ["source_message_revisions.source_message_id", "source_message_revisions.id"],
            name="fk_media_dispositions_revision_same_message",
        ),
        UniqueConstraint(
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
        CheckConstraint("source_ordinal >= 0", name="ck_media_dispositions_ordinal"),
        CheckConstraint("attempt_number > 0", name="ck_media_dispositions_attempt"),
        CheckConstraint(
            "observation_status IN ('read_observed', 'unread_unavailable', 'unread_rejected')",
            name="ck_media_dispositions_observation",
        ),
        CheckConstraint(
            "disposition IN ('stored', 'missing', 'rejected', 'unsupported', 'unassociated')",
            name="ck_media_dispositions_disposition",
        ),
        CheckConstraint(
            "(observation_status = 'read_observed' AND observed_checksum_sha256 IS NOT NULL) "
            "OR (observation_status != 'read_observed' AND observed_checksum_sha256 IS NULL)",
            name="ck_media_dispositions_checksum_observation",
        ),
        Index("ix_media_dispositions_source", "source_message_id", "source_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_message_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    source_ordinal: Mapped[int] = mapped_column(Integer)
    source_message_revision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    source_descriptor_identity: Mapped[str] = mapped_column(String(64))
    observation_status: Mapped[str] = mapped_column(String(24))
    observation_reason_code: Mapped[str] = mapped_column(String(40))
    observed_checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    observed_byte_size: Mapped[int | None] = mapped_column(BigInteger)
    content_identity: Mapped[str] = mapped_column(String(80))
    attempt_number: Mapped[int] = mapped_column(Integer)
    verifier_version: Mapped[str] = mapped_column(String(40))
    association_version: Mapped[str] = mapped_column(String(40))
    disposition: Mapped[str] = mapped_column(String(24))
    reason_code: Mapped[str] = mapped_column(String(40))
    media_asset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MediaDerivativeRow(IngestionBase):
    """Successful versioned public derivative of one source asset."""

    __tablename__ = "media_derivatives"
    __table_args__ = (
        UniqueConstraint("media_asset_id", "variant", name="uq_media_derivatives_variant"),
        ForeignKeyConstraint(
            ["stored_object_id", "stored_object_storage_class"],
            ["stored_media_objects.id", "stored_media_objects.storage_class"],
            name="fk_media_derivatives_public_object",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "stored_object_storage_class = 'public_derivative'",
            name="ck_media_derivatives_public_class",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
    )
    stored_object_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    stored_object_storage_class: Mapped[str] = mapped_column(String(24))
    variant: Mapped[str] = mapped_column(String(40))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MediaDerivativeAttemptRow(IngestionBase):
    """Independent auditable derivative generation attempt."""

    __tablename__ = "media_derivative_attempts"
    __table_args__ = (
        UniqueConstraint(
            "media_asset_id",
            "variant",
            "attempt_number",
            name="uq_media_derivative_attempt_number",
        ),
        CheckConstraint("attempt_number > 0", name="ck_media_derivative_attempts_positive"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')",
            name="ck_media_derivative_attempts_status",
        ),
        CheckConstraint(
            "(status = 'succeeded' AND media_derivative_id IS NOT NULL AND reason_code IS NULL) "
            "OR (status = 'failed' AND media_derivative_id IS NULL AND reason_code IS NOT NULL) "
            "OR (status = 'pending' AND media_derivative_id IS NULL AND reason_code IS NULL)",
            name="ck_media_derivative_attempts_terminal_shape",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
    )
    variant: Mapped[str] = mapped_column(String(40))
    attempt_number: Mapped[int] = mapped_column(Integer)
    transform_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str | None] = mapped_column(String(40))
    source_object_checksum_sha256: Mapped[str] = mapped_column(String(64))
    media_derivative_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_derivatives.id", ondelete="RESTRICT"),
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OfferMediaRow(IngestionBase):
    """Ordered offer association preserving the E2 evidence rule."""

    __tablename__ = "offer_media"
    __table_args__ = (
        UniqueConstraint("offer_id", "media_asset_id", name="uq_offer_media_asset"),
        UniqueConstraint("offer_id", "position", name="uq_offer_media_position"),
        CheckConstraint("position >= 0", name="ck_offer_media_position"),
        CheckConstraint(
            "association_rule IN "
            "('same_message', 'explicit_group', 'reply', 'time_burst', 'manual')",
            name="ck_offer_media_rule",
        ),
        CheckConstraint(
            "association_confidence >= 0 AND association_confidence <= 1",
            name="ck_offer_media_confidence",
        ),
    )

    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    association_rule: Mapped[str] = mapped_column(String(24))
    association_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))


class SourceMessageParseIssueRow(IngestionBase):
    """Append-only parse miss/incomplete ledger for ingestion reporting."""

    __tablename__ = "source_message_parse_issues"
    __table_args__ = (
        CheckConstraint(
            "issue_outcome IN ('parser_miss', 'parser_incomplete')",
            name="ck_source_message_parse_issues_issue_outcome",
        ),
        CheckConstraint(
            (
                "message_outcome IN "
                "('created', 'unchanged', 'revised', 'skipped_non_candidate')"
            ),
            name="ck_source_message_parse_issues_message_outcome",
        ),
        Index("ix_source_message_parse_issues_created", "created_at"),
        Index(
            "ix_source_message_parse_issues_outcome_created",
            "issue_outcome",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_channels.id", ondelete="RESTRICT"),
    )
    source_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_messages.id", ondelete="RESTRICT"),
    )
    source_message_revision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_message_revisions.id", ondelete="RESTRICT"),
    )
    external_message_id: Mapped[int] = mapped_column(BigInteger)
    ingest_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ingest_runs.id", ondelete="RESTRICT"),
    )
    parser_version: Mapped[str] = mapped_column(String(40))
    score: Mapped[int] = mapped_column(Integer)
    threshold: Mapped[int] = mapped_column(Integer)
    is_candidate: Mapped[bool] = mapped_column(Boolean)
    signals_json: Mapped[object] = mapped_column(JSONB)
    warnings_json: Mapped[object] = mapped_column(JSONB)
    issue_outcome: Mapped[str] = mapped_column(String(32))
    message_outcome: Mapped[str] = mapped_column(String(32))
    boundary_band: Mapped[str] = mapped_column(String(40))
    signal_combination: Mapped[str] = mapped_column(String(128))
    text_excerpt_redacted: Mapped[str] = mapped_column(Text)
    offer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )


class TelegramRawEventRow(IngestionBase):
    """Verbatim landed live event retained independently of canonical state."""

    __tablename__ = "telegram_raw_events"
    __table_args__ = (
        UniqueConstraint(
            "channel_external_id",
            "external_message_id",
            "event_kind",
            "checksum",
            name="uq_telegram_raw_events_dedupe",
        ),
        CheckConstraint(
            "event_kind IN ('new', 'edit', 'delete')",
            name="ck_telegram_raw_events_kind",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('processed', 'failed', 'skipped_non_candidate')",
            name="ck_telegram_raw_events_outcome",
        ),
        Index(
            "ix_telegram_raw_events_pending",
            "received_at",
            postgresql_where=sa_text("processed_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_kind: Mapped[str] = mapped_column(String(16))
    channel_external_id: Mapped[str] = mapped_column(String(64))
    external_message_id: Mapped[int] = mapped_column(BigInteger)
    payload_json: Mapped[object] = mapped_column(JSONB)
    checksum: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(24))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(64))
