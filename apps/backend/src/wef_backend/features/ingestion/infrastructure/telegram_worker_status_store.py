"""SQLAlchemy read model for Telegram worker ops status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from wef_backend.features.ingestion.application.persistence import RunMode, RunStatus
from wef_backend.features.ingestion.infrastructure.models import (
    IngestRunRow,
    SourceChannelRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyTelegramWorkerStatusStore:
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
        """Return (checkpoint last_source_index, finished_at) for the latest live run."""
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
                return None, None
            row = await session.execute(
                select(IngestRunRow.checkpoint_json, IngestRunRow.finished_at)
                .where(
                    IngestRunRow.source_channel_id == channel_id,
                    IngestRunRow.mode == RunMode.LIVE.value,
                    IngestRunRow.status.in_(
                        (
                            RunStatus.SUCCEEDED.value,
                            RunStatus.FAILED.value,
                        ),
                    ),
                    IngestRunRow.finished_at.is_not(None),
                )
                .order_by(IngestRunRow.finished_at.desc())
                .limit(1),
            )
            first = row.first()
            if first is None:
                return None, None
            checkpoint_json, finished_at = first
            checkpoint_id: int | None = None
            if isinstance(checkpoint_json, dict):
                raw = checkpoint_json.get("last_source_index")
                if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
                    checkpoint_id = raw
            return checkpoint_id, finished_at
