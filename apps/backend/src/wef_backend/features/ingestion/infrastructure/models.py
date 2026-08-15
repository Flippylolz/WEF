"""SQLAlchemy mappings for historical ingestion persistence."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from decimal import Decimal  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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
