"""SQLAlchemy mappings for encrypted contacts and reveal audits."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ContactsBase(DeclarativeBase):
    """Declarative metadata owned by contacts infrastructure."""


class ContactPointRow(ContactsBase):
    """Encrypted contact extracted from an offer source message."""

    __tablename__ = "contact_points"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('phone', 'telegram')",
            name="ck_contact_points_kind",
        ),
        Index(
            "uq_contact_points_offer_kind_fingerprint",
            "offer_id",
            "kind",
            "fingerprint_hmac",
            unique=True,
        ),
        Index("ix_contact_points_offer_id", "offer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    offer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
    )
    source_message_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(16))
    value_ciphertext: Mapped[str] = mapped_column(Text)
    masked_value: Mapped[str] = mapped_column(String(128))
    fingerprint_hmac: Mapped[str] = mapped_column(String(64))
    is_revealable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ContactRevealRow(ContactsBase):
    """Minimized audit row for one contact reveal attempt."""

    __tablename__ = "contact_reveals"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('allowed', 'rate_limited', 'forbidden', 'unavailable')",
            name="ck_contact_reveals_outcome",
        ),
        Index("ix_contact_reveals_user_revealed", "user_id", "revealed_at"),
        Index("ix_contact_reveals_offer_revealed", "offer_id", "revealed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    offer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
    )
    source_message_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    contact_set_version: Mapped[str] = mapped_column(String(32))
    revealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(16))
