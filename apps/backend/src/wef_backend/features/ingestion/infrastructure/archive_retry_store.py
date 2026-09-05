"""Transaction-local retry accounting and one exception per original archived event."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from wef_backend.features.ingestion.application.archive_retry import (
    MAX_DATA_FAILURES,
    RETRY_POLICY_VERSION,
    ArchiveFailure,
    retry_delay,
)
from wef_backend.features.ingestion.infrastructure.models import (
    TelegramArchiveExceptionRow,
    TelegramArchiveRecoveryRow,
    TelegramRawEventRow,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


async def exception_for(session: AsyncSession, row: TelegramRawEventRow, now: datetime) -> None:
    """Upsert one safe actionable record rather than a repeated notification per attempt."""
    issue = await session.get(TelegramArchiveExceptionRow, row.id)
    if issue is None:
        session.add(
            TelegramArchiveExceptionRow(
                event_id=row.id,
                reason=row.last_error or "UnknownError",
                policy_version=RETRY_POLICY_VERSION,
                state="quarantined",
                first_seen_at=now,
                last_seen_at=now,
            )
        )
    else:
        issue.reason = row.last_error or "UnknownError"
        issue.state = "quarantined"
        issue.policy_version = RETRY_POLICY_VERSION
        issue.last_seen_at = now


async def prepare_retry_versions(
    session: AsyncSession, now: datetime, limit: int, channel_external_id: str | None = None
) -> None:
    """Bound legacy classification and relevant-policy re-evaluation without deleting history."""
    rows = await session.scalars(
        select(TelegramRawEventRow)
        .where(
            TelegramRawEventRow.processed_at.is_(None),
            TelegramRawEventRow.retry_policy_version != RETRY_POLICY_VERSION,
            *(
                [TelegramRawEventRow.channel_external_id == channel_external_id]
                if channel_external_id is not None
                else []
            ),
        )
        .order_by(TelegramRawEventRow.received_at, TelegramRawEventRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    for row in rows:
        if not row.retry_policy_version:
            row.data_failure_count = (
                row.attempts
                if row.outcome == "failed" and row.last_error != "RunLockHeldError"
                else 0
            )
            row.deferral_count = row.attempts if row.last_error == "RunLockHeldError" else 0
        else:
            row.data_failure_count = 0
        row.retry_policy_version = RETRY_POLICY_VERSION
        row.next_attempt_at = now
        if row.data_failure_count >= MAX_DATA_FAILURES:
            await exception_for(session, row, now)
        else:
            issue = await session.get(TelegramArchiveExceptionRow, row.id)
            if issue is not None:
                issue.state = "retrying"
                issue.policy_version = RETRY_POLICY_VERSION
                issue.last_seen_at = now


async def record_retry(
    session: AsyncSession, event_id: UUID, failure: ArchiveFailure, now: datetime, jitter: float
) -> bool:
    """Defer contention/transport separately from the five-failure source-data budget."""
    row = await session.scalar(
        select(TelegramRawEventRow)
        .where(
            TelegramRawEventRow.id == event_id,
        )
        .with_for_update()
    )
    if row is None or row.processed_at is not None:
        return False
    row.attempts += 1
    row.outcome = "failed"
    row.last_error = failure.category
    row.retry_policy_version = RETRY_POLICY_VERSION
    if failure.kind == "data":
        row.data_failure_count += 1
        streak = row.data_failure_count
    else:
        row.deferral_count += 1
        streak = row.deferral_count
    row.next_attempt_at = now + timedelta(
        seconds=retry_delay(streak, jitter, failure.retry_after_seconds)
    )
    if row.data_failure_count >= MAX_DATA_FAILURES:
        await exception_for(session, row, now)
    if failure.kind == "systemic":
        recovery = await session.get(TelegramArchiveRecoveryRow, row.channel_external_id)
        if recovery is not None:
            recovery.phase = "paused"
            recovery.pause_reason = failure.category
    return True
