"""SQLAlchemy read model for Telegram worker ops status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.telegram_progress_store import (
    SQLAlchemyTelegramProgressStore,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyTelegramWorkerStatusStore(SQLAlchemyTelegramProgressStore):
    """Read max message id and latest live ingest checkpoint."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the async session factory used for read-only queries."""
        self._session_factory = session_factory

    async def max_external_message_id(self, *, channel_external_id: str) -> int:
        """Return the highest persisted Telegram message id for the channel."""
        async with self._session_factory() as session:
            channel_id = await session.scalar(
                select(SourceChannelRow.id)
                .where(
                    SourceChannelRow.platform == "telegram",
                    SourceChannelRow.external_id == channel_external_id,
                )
                .limit(1),
            )
            if channel_id is None:
                return 0
            value = await session.scalar(
                select(func.max(SourceMessageRow.external_message_id)).where(
                    SourceMessageRow.source_channel_id == channel_id,
                ),
            )
            return int(value or 0)

    async def latest_live_checkpoint(
        self,
        *,
        channel_external_id: str,
    ) -> tuple[int | None, datetime | None]:
        """Return traversal progress; a late archive/run finish never rewinds it."""
        progress = await self.channel_progress(channel_external_id=channel_external_id)
        return progress.polled_through_id, progress.last_polled_at
