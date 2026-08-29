"""SQLAlchemy adapter for the verbatim Telegram raw-event archive."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.telegram_events import (
    RawArchiveKind,
    RawArchiveOutcome,
    RawEventRecord,
)
from wef_backend.features.ingestion.infrastructure.models import TelegramRawEventRow

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_MAX_ATTEMPTS = 5


class SQLAlchemyRawEventArchive:
    """Land, claim, and reconcile raw events inside the application database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def land(
        self,
        *,
        event_kind: RawArchiveKind,
        channel_external_id: str,
        external_message_id: int,
        payload: Mapping[str, object],
        checksum: str,
    ) -> UUID:
        """Land one verbatim event idempotently and return its stable row id."""
        async with self._session_factory() as session, session.begin():
            statement = (
                insert(TelegramRawEventRow)
                .values(
                    id=uuid4(),
                    event_kind=event_kind,
                    channel_external_id=channel_external_id,
                    external_message_id=external_message_id,
                    payload_json=json.loads(json.dumps(payload)),
                    checksum=checksum,
                )
                .on_conflict_do_nothing(
                    constraint="uq_telegram_raw_events_dedupe",
                )
                .returning(TelegramRawEventRow.id)
            )
            inserted = await session.scalar(statement)
            if inserted is not None:
                return UUID(str(inserted))
            existing = await session.scalar(
                select(TelegramRawEventRow.id)
                .where(
                    TelegramRawEventRow.channel_external_id == channel_external_id,
                    TelegramRawEventRow.external_message_id == external_message_id,
                    TelegramRawEventRow.event_kind == event_kind,
                    TelegramRawEventRow.checksum == checksum,
                )
                .limit(1),
            )
            if existing is None:
                message = "raw event insert conflicted without a retrievable row"
                raise RuntimeError(message)
            return UUID(str(existing))

    async def unprocessed_batch(self, limit: int) -> Sequence[RawEventRecord]:
        """Return the oldest events that still need a terminal processing outcome."""
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(TelegramRawEventRow)
                    .where(
                        TelegramRawEventRow.processed_at.is_(None),
                        TelegramRawEventRow.attempts < _MAX_ATTEMPTS,
                    )
                    .order_by(TelegramRawEventRow.received_at, TelegramRawEventRow.id)
                    .limit(limit),
                )
            ).scalars()
            return tuple(
                RawEventRecord(
                    id=row.id,
                    event_kind=cast(RawArchiveKind, row.event_kind),
                    channel_external_id=row.channel_external_id,
                    external_message_id=row.external_message_id,
                    payload=cast("Mapping[str, object]", row.payload_json),
                    received_at=row.received_at,
                    attempts=row.attempts,
                )
                for row in rows
            )

    async def mark_attempt(
        self,
        event_id: UUID,
        *,
        outcome: RawArchiveOutcome,
        error_category: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record one processing attempt; failed events retry until the cap."""
        now = completed_at or datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(TelegramRawEventRow)
                .where(TelegramRawEventRow.id == event_id)
                .values(
                    attempts=TelegramRawEventRow.attempts + 1,
                    outcome=outcome,
                    last_error=error_category,
                    processed_at=now if outcome != "failed" else None,
                ),
            )

    async def failed_exhausted_count(self) -> int:
        """Return how many events permanently failed after the bounded retries."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(TelegramRawEventRow)
                .where(
                    TelegramRawEventRow.outcome == "failed",
                    TelegramRawEventRow.attempts >= _MAX_ATTEMPTS,
                ),
            )
            return int(value or 0)
