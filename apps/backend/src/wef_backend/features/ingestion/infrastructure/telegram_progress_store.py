"""Atomic channel progress writes independent of run completion order."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.telegram_progress import ChannelProgress, SweepBatch
from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    SourceMessageRow,
    TelegramChannelProgressRow,
    TelegramRawEventRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def advance_applied(session: AsyncSession, channel_id: UUID, external_id: int) -> None:
    """Keep applied high-water in the same transaction as canonical state."""
    highest = await session.scalar(
        select(func.max(SourceMessageRow.external_message_id)).where(
            SourceMessageRow.source_channel_id == channel_id
        )
    )
    statement = insert(TelegramChannelProgressRow).values(
        source_channel_id=channel_id,
        applied_high_water_id=max(external_id, int(highest or 0), 0),
        last_applied_at=datetime.now(UTC),
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["source_channel_id"],
            set_={
                "applied_high_water_id": func.greatest(
                    TelegramChannelProgressRow.applied_high_water_id,
                    statement.excluded.applied_high_water_id,
                ),
                "last_applied_at": statement.excluded.last_applied_at,
            },
        )
    )


class SQLAlchemyTelegramProgressStore:
    """Monotonic writes plus short row-locked sweep transactions; no provider calls."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the shared async session factory."""
        self._session_factory = session_factory

    async def _channel(self, session: AsyncSession, external_id: str) -> UUID | None:
        value = await session.scalar(
            select(SourceChannelRow.id).where(
                SourceChannelRow.platform == "telegram",
                SourceChannelRow.external_id == external_id,
            )
        )
        return None if value is None else UUID(str(value))

    async def channel_progress(self, *, channel_external_id: str) -> ChannelProgress:
        """Read only; legacy sources have no certified traversal boundary."""
        async with self._session_factory() as session:
            channel_id = await self._channel(session, channel_external_id)
            if channel_id is None:
                return ChannelProgress()
            row = await session.get(TelegramChannelProgressRow, channel_id)
            if row is None:
                highest = await session.scalar(
                    select(func.max(SourceMessageRow.external_message_id)).where(
                        SourceMessageRow.source_channel_id == channel_id
                    )
                )
                return ChannelProgress(applied_high_water_id=int(highest or 0))
            pending = await session.scalar(
                select(TelegramRawEventRow.id)
                .where(
                    TelegramRawEventRow.channel_external_id == channel_external_id,
                    TelegramRawEventRow.processed_at.is_(None),
                )
                .limit(1)
            )
            return ChannelProgress(
                row.applied_high_water_id,
                row.polled_through_id,
                row.history_limited
                or pending is not None
                or row.polled_through_id < row.applied_high_water_id,
                row.source_retry_at,
                row.last_applied_at,
                row.last_polled_at,
                row.last_sweep_at,
            )

    async def advance_live_checkpoint(self, *, channel_external_id: str, external_id: int) -> int:
        """Only the polling coordinator calls this after durable batch outcomes."""
        async with self._session_factory() as session, session.begin():
            channel_id = await self._channel(session, channel_external_id)
            if channel_id is None:
                return 0
            highest = await session.scalar(
                select(func.max(SourceMessageRow.external_message_id)).where(
                    SourceMessageRow.source_channel_id == channel_id
                )
            )
            statement = insert(TelegramChannelProgressRow).values(
                applied_high_water_id=int(highest or 0),
                source_channel_id=channel_id,
                polled_through_id=max(external_id, 0),
                last_polled_at=datetime.now(UTC),
            )
            value = await session.scalar(
                statement.on_conflict_do_update(
                    index_elements=["source_channel_id"],
                    set_={
                        "polled_through_id": func.greatest(
                            TelegramChannelProgressRow.polled_through_id,
                            statement.excluded.polled_through_id,
                        ),
                        "last_polled_at": statement.excluded.last_polled_at,
                        "source_retry_at": None,
                    },
                ).returning(TelegramChannelProgressRow.polled_through_id)
            )
            return int(value or 0)

    async def _locked(
        self, session: AsyncSession, channel_external_id: str
    ) -> TelegramChannelProgressRow | None:
        channel_id = await self._channel(session, channel_external_id)
        if channel_id is None:
            await session.execute(
                insert(SourceChannelRow)
                .values(
                    id=uuid4(),
                    platform="telegram",
                    external_id=channel_external_id,
                    display_name=channel_external_id,
                )
                .on_conflict_do_nothing(constraint="uq_source_channels_identity")
            )
            channel_id = await self._channel(session, channel_external_id)
        await session.execute(
            insert(TelegramChannelProgressRow)
            .values(source_channel_id=channel_id)
            .on_conflict_do_nothing(index_elements=["source_channel_id"])
        )
        value: TelegramChannelProgressRow | None = await session.scalar(
            select(TelegramChannelProgressRow)
            .where(TelegramChannelProgressRow.source_channel_id == channel_id)
            .with_for_update()
        )
        return value

    async def sweep_batch(self, channel_external_id: str, limit: int) -> SweepBatch:
        """Use a fixed upper bound so arrivals cannot extend a sweep forever."""
        async with self._session_factory() as session, session.begin():
            row = await self._locked(session, channel_external_id)
            if row is None:
                return SweepBatch()
            if row.sweep_lease_until is not None and row.sweep_lease_until > datetime.now(UTC):
                return SweepBatch()
            if row.sweep_after_id >= row.sweep_upper_id:
                maximum = await session.scalar(
                    select(func.max(SourceMessageRow.external_message_id)).where(
                        SourceMessageRow.source_channel_id == row.source_channel_id
                    )
                )
                row.sweep_after_id = 0
                row.sweep_upper_id = int(maximum or 0)
                row.sweep_unknown_count = 0
            ids = await session.scalars(
                select(SourceMessageRow.external_message_id)
                .where(
                    SourceMessageRow.source_channel_id == row.source_channel_id,
                    SourceMessageRow.external_message_id > row.sweep_after_id,
                    SourceMessageRow.external_message_id <= row.sweep_upper_id,
                )
                .order_by(SourceMessageRow.external_message_id)
                .limit(min(limit, 100))
            )
            result = tuple(ids)
            row.sweep_token = uuid4()
            row.sweep_lease_until = datetime.now(UTC) + timedelta(seconds=300)
            return SweepBatch(result, row.sweep_token)

    async def finish_sweep_batch(
        self, channel_external_id: str, batch: SweepBatch, *, unknown: int
    ) -> None:
        """Persist continuation and unresolved access evidence after classified observations."""
        ids = batch.ids
        if not ids:
            return
        async with self._session_factory() as session, session.begin():
            row = await self._locked(session, channel_external_id)
            if row is None or row.sweep_token != batch.token or max(ids) <= row.sweep_after_id:
                return
            row.sweep_lease_until = None
            row.sweep_token = None
            row.sweep_after_id = max(row.sweep_after_id, *ids)
            row.sweep_unknown_count += unknown
            if unknown:
                row.history_limited = True
            if row.sweep_after_id >= row.sweep_upper_id:
                row.last_sweep_at = datetime.now(UTC)
                row.history_limited = row.sweep_unknown_count > 0

    async def defer_source(self, channel_external_id: str, *, seconds: float) -> None:
        """Keep retry-after durable without sleeping while canonical work is locked."""
        async with self._session_factory() as session, session.begin():
            row = await self._locked(session, channel_external_id)
            if row is not None:
                due = datetime.now(UTC) + timedelta(seconds=max(5, seconds))
                row.source_retry_at = max(row.source_retry_at, due) if row.source_retry_at else due
                row.history_limited = True
