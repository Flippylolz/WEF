"""Durable bounded canary and redacted archive reconciliation preflight."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from wef_backend.features.ingestion.application.archive_processing import ARCHIVE_POLICY_VERSION
from wef_backend.features.ingestion.infrastructure.models import (
    TelegramArchiveRecoveryRow,
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.telegram_events import RawEventRecord


_MAX_DATA_ATTEMPTS = 5


class SQLAlchemyArchiveRecovery:
    """Bound automatic recovery with durable, operator-readable progress state."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Keep all recovery state in PostgreSQL, independent of process restarts."""
        self._factory = session_factory
        self._archive = SQLAlchemyRawEventArchive(session_factory)

    async def preflight(self, channel_external_id: str) -> dict[str, object]:
        """Report proposed work without mutating archive, canonical, or recovery state."""
        raw = TelegramRawEventRow
        sibling = aliased(raw)
        pending = raw.processed_at.is_(None)
        sibling_exists = (
            select(sibling.id)
            .where(
                sibling.channel_external_id == raw.channel_external_id,
                sibling.external_message_id == raw.external_message_id,
                sibling.event_kind == raw.event_kind,
                sibling.checksum != raw.checksum,
                sibling.processed_at.is_not(None),
            )
            .exists()
        )
        receipt_exists = (
            select(TelegramArchiveResolutionRow.event_id)
            .where(
                TelegramArchiveResolutionRow.event_id == raw.id,
            )
            .exists()
        )
        async with self._factory() as session:
            row = (
                await session.execute(
                    select(
                        func.count().filter(
                            pending & ((raw.attempts < _MAX_DATA_ATTEMPTS) | receipt_exists)
                        ),
                        func.count().filter(
                            pending & (raw.attempts >= _MAX_DATA_ATTEMPTS) & ~receipt_exists
                        ),
                        func.min(case((pending, raw.received_at))),
                        func.count().filter(pending & sibling_exists),
                        func.count().filter(pending & receipt_exists),
                    ).where(raw.channel_external_id == channel_external_id)
                )
            ).one()
            state = await session.get(TelegramArchiveRecoveryRow, channel_external_id)
            oldest = row[2]
            return {
                "eligible": row[0],
                "exhausted": row[1],
                "oldest_pending_age_seconds": (
                    max(0, int((datetime.now(UTC) - oldest).total_seconds())) if oldest else None
                ),
                "pending_with_terminal_sibling": row[3],
                "proposed_receipt_projections": row[4],
                "proposed_canonical_evaluations": row[0] - row[4],
                "phase": state.phase if state else "not_started",
                "pause_reason": state.pause_reason if state else None,
            }

    async def _state(self, session: AsyncSession, channel: str) -> TelegramArchiveRecoveryRow:
        existing = await session.scalar(
            select(TelegramArchiveRecoveryRow)
            .where(TelegramArchiveRecoveryRow.channel_external_id == channel)
            .with_for_update()
        )
        if existing is not None:
            return existing
        records = await self._archive.unprocessed_batch(100, channel_external_id=channel)
        await session.execute(
            insert(TelegramArchiveRecoveryRow)
            .values(
                channel_external_id=channel,
                phase="canary" if records else "running",
                policy_version=ARCHIVE_POLICY_VERSION,
                canary_ids=[str(record.id) for record in records],
                baseline_count=len(records),
                next_batch_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["channel_external_id"])
        )
        state = await session.scalar(
            select(TelegramArchiveRecoveryRow)
            .where(
                TelegramArchiveRecoveryRow.channel_external_id == channel,
            )
            .with_for_update()
        )
        if state is None:
            msg = "archive recovery state is missing"
            raise RuntimeError(msg)
        return state

    async def claim_batch(self, channel_external_id: str, limit: int) -> Sequence[RawEventRecord]:
        """Reserve one rate-bounded batch while preserving a restart-safe canary."""
        async with self._factory() as session, session.begin():
            state = await self._state(session, channel_external_id)
            now = datetime.now(UTC)
            if state.phase == "paused" or state.next_batch_at > now:
                return ()
            state.next_batch_at = now + timedelta(seconds=5)
            return await self._archive.unprocessed_batch(
                min(25, limit),
                channel_external_id=channel_external_id,
                event_ids=(
                    tuple(UUID(value) for value in state.canary_ids)
                    if state.phase == "canary"
                    else None
                ),
            )

    async def finish_batch(self, channel_external_id: str, *, failed: bool) -> None:
        """Require canonical proof for every original canary before expanding."""
        async with self._factory() as session, session.begin():
            state = await self._state(session, channel_external_id)
            if state.phase != "canary":
                return
            if failed:
                state.phase = "paused"
                state.pause_reason = "canary_requires_review"
                return
            ids = [UUID(value) for value in state.canary_ids]
            verified = await session.scalar(
                select(func.count())
                .select_from(TelegramRawEventRow)
                .join(
                    TelegramArchiveResolutionRow,
                    TelegramArchiveResolutionRow.event_id == TelegramRawEventRow.id,
                )
                .where(
                    TelegramRawEventRow.id.in_(ids),
                    TelegramRawEventRow.processed_at.is_not(None),
                    TelegramRawEventRow.checksum == TelegramArchiveResolutionRow.source_checksum,
                )
            )
            if verified == len(ids):
                state.phase = "running"

    async def set_paused(self, channel_external_id: str, *, paused: bool) -> None:
        """Persist operator pause/resume without altering any source or receipt."""
        async with self._factory() as session, session.begin():
            state = await self._state(session, channel_external_id)
            state.phase = "paused" if paused else "canary"
            state.pause_reason = "operator_pause" if paused else None
            state.next_batch_at = datetime.now(UTC)
        if not paused:
            await self.finish_batch(channel_external_id, failed=False)
