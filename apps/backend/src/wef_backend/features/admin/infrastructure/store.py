"""SQLAlchemy adapters for owner admin audits and reveal audit reads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from wef_backend.features.admin.application.admin_ops import (
    AdminAuditEvent,
    AdminOutcome,
    RevealAuditSummary,
)
from wef_backend.features.admin.infrastructure.models import AdminAuditEventRow
from wef_backend.features.contacts.infrastructure.models import ContactRevealRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyAdminAuditStore:
    """Persist and list redacted admin audit events."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the collaborator."""
        self._session_factory = session_factory

    async def record(self, event: AdminAuditEvent) -> None:
        """Persist one redacted admin audit event."""
        async with self._session_factory.begin() as session:
            session.add(
                AdminAuditEventRow(
                    id=event.id,
                    owner_user_id=event.owner_user_id,
                    target_user_id=event.target_user_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    action=event.action,
                    occurred_at=event.occurred_at,
                    request_id=event.request_id,
                    outcome=event.outcome.value,
                ),
            )

    async def list_recent(self, *, limit: int = 100) -> tuple[AdminAuditEvent, ...]:
        """Return recent audit rows newest-first."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(AdminAuditEventRow)
                    .order_by(AdminAuditEventRow.occurred_at.desc())
                    .limit(limit),
                )
            ).all()
        return tuple(
            AdminAuditEvent(
                id=row.id,
                owner_user_id=row.owner_user_id,
                target_user_id=row.target_user_id,
                target_type=row.target_type,
                target_id=row.target_id,
                action=row.action,
                occurred_at=row.occurred_at,
                request_id=row.request_id,
                outcome=AdminOutcome(row.outcome),
            )
            for row in rows
        )


class SQLAlchemyRevealAuditReader:
    """Read minimized contact reveal audits for the owner console."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the collaborator."""
        self._session_factory = session_factory

    async def list_recent(self, *, limit: int = 100) -> tuple[RevealAuditSummary, ...]:
        """Return recent audit rows newest-first."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(ContactRevealRow)
                    .order_by(ContactRevealRow.revealed_at.desc())
                    .limit(limit),
                )
            ).all()
        return tuple(
            RevealAuditSummary(
                id=row.id,
                user_id=row.user_id,
                offer_id=row.offer_id,
                outcome=row.outcome,
                revealed_at=row.revealed_at,
                request_id=row.request_id,
            )
            for row in rows
        )
