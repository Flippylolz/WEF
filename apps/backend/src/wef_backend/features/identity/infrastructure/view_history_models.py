"""Authenticated visit and viewed-offer persistence models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wef_backend.features.identity.infrastructure.models import IdentityBase


class AccountVisitRow(IdentityBase):
    """One idempotent browser visit with its captured prior-visit baseline."""

    __tablename__ = "account_visits"
    __table_args__ = (Index("ix_account_visits_user_started", "user_id", "started_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    visit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ViewedOfferRow(IdentityBase):
    """One account's aggregate view state for one public offer."""

    __tablename__ = "viewed_offers"
    __table_args__ = (
        CheckConstraint("view_count >= 1", name="ck_viewed_offers_count_positive"),
        Index("ix_viewed_offers_user_last_viewed", "user_id", "last_viewed_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    offer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    first_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    view_count: Mapped[int] = mapped_column(BigInteger, default=1)
