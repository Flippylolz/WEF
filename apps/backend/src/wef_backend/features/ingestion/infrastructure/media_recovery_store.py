"""PostgreSQL fenced media queue; network and transforms never hold these locks."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.archive_retry import retry_delay
from wef_backend.features.ingestion.application.media_recovery import (
    LEASE_SECONDS,
    MEDIA_RECOVERY_POLICY,
    MediaClaim,
)
from wef_backend.features.ingestion.application.media_storage import MediaWorkItem
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.domain.media_grouping import MediaAssociationRule
from wef_backend.features.ingestion.infrastructure.media_recovery_discovery import (
    decode_media_source,
    discover_media,
)
from wef_backend.features.ingestion.infrastructure.models import (
    MediaRecoveryChannelRow,
    MediaRecoveryWorkRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

CANARY_ASSETS = 100
MAX_DATA_FAILURES = 5

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.archive_retry import ArchiveFailure
    from wef_backend.features.ingestion.application.media_recovery import MediaRecoveryOutcome


@dataclass(frozen=True, slots=True)
class SQLAlchemyMediaRecoveryStore:
    """Bounded channel queue with fair eligibility, durable pause and canary state."""

    factory: async_sessionmaker[AsyncSession]
    channel_external_id: str

    async def discover(self, limit: int = 100) -> int:
        """Delegate bounded source discovery without coupling it to media acquisition."""
        return await discover_media(self.factory, self.channel_external_id, min(limit, 100))

    async def _channel(self, session: AsyncSession) -> MediaRecoveryChannelRow | None:
        channel_id = await session.scalar(
            select(SourceChannelRow.id).where(
                SourceChannelRow.external_id == self.channel_external_id
            )
        )
        if channel_id is None:
            return None
        await session.execute(
            insert(MediaRecoveryChannelRow)
            .values(source_channel_id=channel_id)
            .on_conflict_do_nothing()
        )
        result: MediaRecoveryChannelRow | None = await session.scalar(
            select(MediaRecoveryChannelRow)
            .where(MediaRecoveryChannelRow.source_channel_id == channel_id)
            .with_for_update()
        )

        return result

    async def claim(self) -> MediaClaim | None:
        """Serialize only channel claim accounting, then release all locks."""
        now = datetime.now(UTC)
        async with self.factory() as session, session.begin():
            channel = await self._channel(session)
            if channel is None or not await self._claim_allowed(session, channel, now):
                return None
            row = await session.scalar(
                select(MediaRecoveryWorkRow)
                .join(
                    SourceMessageRevisionRow,
                    SourceMessageRevisionRow.id == MediaRecoveryWorkRow.source_revision_id,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(
                    SourceMessageRow.source_channel_id == channel.source_channel_id,
                    or_(
                        (MediaRecoveryWorkRow.state.in_(("pending", "retry_wait")))
                        & (MediaRecoveryWorkRow.next_attempt_at <= now),
                        (MediaRecoveryWorkRow.state == "leased")
                        & (MediaRecoveryWorkRow.lease_until <= now),
                        (MediaRecoveryWorkRow.state == "quarantined")
                        & (MediaRecoveryWorkRow.policy_version != MEDIA_RECOVERY_POLICY),
                    ),
                )
                .order_by(MediaRecoveryWorkRow.next_attempt_at, MediaRecoveryWorkRow.id)
                .limit(1)
                .with_for_update(of=MediaRecoveryWorkRow, skip_locked=True)
            )
            if row is None:
                return None
            revision = await session.get(SourceMessageRevisionRow, row.source_revision_id)
            if revision is None:
                message = "media source relationship missing"
                raise RuntimeError(message)
            source = await session.get(SourceMessageRow, revision.source_message_id)
            if source is None:
                message = "media source relationship missing"
                raise RuntimeError(message)
            if source.current_revision_id != revision.id or source.deleted_at is not None:
                row.state = "superseded"
                row.reason = "source_revision_changed"
                return None
            if row.policy_version != MEDIA_RECOVERY_POLICY:
                row.data_failures = 0
                row.policy_version = MEDIA_RECOVERY_POLICY
            row.state = "leased"
            row.lease_token = uuid4()
            row.lease_until = now + timedelta(seconds=LEASE_SECONDS)
            row.updated_at = now
            channel_row = await session.get(SourceChannelRow, channel.source_channel_id)
            if channel_row is None:
                message = "media source relationship missing"
                raise RuntimeError(message)
            identity = SourceIdentity(
                SourcePlatform.TELEGRAM,
                channel_row.external_id,
                channel_row.display_name,
                "public_channel",
            )
            if not isinstance(revision.raw_payload_json, dict):
                message = "media source payload is invalid"
                raise TypeError(message)
            raw = decode_media_source(revision.raw_payload_json, identity)
            return MediaClaim(
                id=row.id,
                token=row.lease_token,
                channel_id=channel.source_channel_id,
                raw=raw,
                association_revision_id=row.association_revision_id,
                item=MediaWorkItem(
                    source_message_id=source.id,
                    source_message_revision_id=revision.id,
                    source_ordinal=row.ordinal,
                    descriptor=raw.media[row.ordinal],
                    association_version=row.grouping_version,
                    offer_id=row.offer_id,
                    association_rule=(
                        MediaAssociationRule(row.association_rule) if row.association_rule else None
                    ),
                    association_confidence=(
                        float(row.association_confidence)
                        if row.association_confidence is not None
                        else None
                    ),
                ),
            )

    @staticmethod
    async def _claim_allowed(
        session: AsyncSession,
        channel: MediaRecoveryChannelRow,
        now: datetime,
    ) -> bool:
        """Serialize canary accounting and a single active channel-wide media lease."""
        if channel.phase not in {"canary", "running"}:
            return False
        if channel.source_retry_at is not None and channel.source_retry_at > now:
            return False
        if channel.phase == "canary" and channel.canary_completed >= CANARY_ASSETS:
            channel.phase = "canary_ready"
            return False
        active = await session.scalar(
            select(func.count())
            .select_from(MediaRecoveryWorkRow)
            .join(
                SourceMessageRevisionRow,
                SourceMessageRevisionRow.id == MediaRecoveryWorkRow.source_revision_id,
            )
            .join(
                SourceMessageRow,
                SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
            )
            .where(
                SourceMessageRow.source_channel_id == channel.source_channel_id,
                MediaRecoveryWorkRow.state == "leased",
                MediaRecoveryWorkRow.lease_until > now,
            )
        )
        return not bool(active)

    @staticmethod
    async def _owned(session: AsyncSession, claim: MediaClaim) -> MediaRecoveryWorkRow | None:
        result: MediaRecoveryWorkRow | None = await session.scalar(
            select(MediaRecoveryWorkRow)
            .where(
                MediaRecoveryWorkRow.id == claim.id,
                MediaRecoveryWorkRow.state == "leased",
                MediaRecoveryWorkRow.lease_token == claim.token,
                MediaRecoveryWorkRow.lease_until > func.now(),
            )
            .with_for_update()
        )

        return result

    async def renew(self, claim: MediaClaim) -> bool:
        """Expired or replaced owners cannot renew or complete."""
        async with self.factory() as session, session.begin():
            row = await self._owned(session, claim)
            if row is None:
                return False
            row.lease_until = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)
            return True

    async def finish(self, claim: MediaClaim, outcome: MediaRecoveryOutcome) -> bool:
        """Complete only a current claim; canary counts successful intended assets."""
        if outcome.state not in {"completed", "unsupported", "superseded", "quarantined"}:
            msg = "invalid media recovery completion"
            raise ValueError(msg)
        async with self.factory() as session, session.begin():
            channel = await self._channel(session)
            row = await self._owned(session, claim)
            if row is None or channel is None:
                return False
            row.state = outcome.state
            row.reason = outcome.reason
            row.lease_token = None
            row.lease_until = None
            row.updated_at = datetime.now(UTC)
            if outcome.state == "completed" and channel.phase == "canary":
                channel.canary_completed += 1
            return True

    async def fail(self, claim: MediaClaim, failure: ArchiveFailure) -> bool:
        """Preserve source and past attempts while rescheduling only media work."""
        now = datetime.now(UTC)
        async with self.factory() as session, session.begin():
            channel = await self._channel(session)
            row = await self._owned(session, claim)
            if row is None or channel is None:
                return False
            if failure.kind == "data":
                row.data_failures += 1
            else:
                row.deferrals += 1
            row.state = "quarantined" if row.data_failures >= MAX_DATA_FAILURES else "retry_wait"
            row.reason = failure.category
            row.next_attempt_at = now + timedelta(
                seconds=retry_delay(
                    row.data_failures if failure.kind == "data" else row.deferrals,
                    random.random(),  # noqa: S311 — retry jitter only
                    failure.retry_after_seconds,
                )
            )
            row.lease_token = None
            row.lease_until = None
            row.updated_at = now
            if failure.retry_after_seconds:
                channel.source_retry_at = max(
                    channel.source_retry_at or now,
                    now + timedelta(seconds=failure.retry_after_seconds),
                )
            if failure.kind == "systemic":
                channel.phase = "paused"
                channel.reason = failure.category
            return True

    async def status(self) -> dict[str, object]:
        """Report aggregate media progress without source identifiers or file paths."""
        async with self.factory() as session:
            channel_id = await session.scalar(
                select(SourceChannelRow.id).where(
                    SourceChannelRow.external_id == self.channel_external_id
                )
            )
            if channel_id is None:
                return {"phase": "not_started", "counts": {}}
            control = await session.get(MediaRecoveryChannelRow, channel_id)
            filters = (SourceMessageRow.source_channel_id == channel_id,)
            query = (
                select(MediaRecoveryWorkRow.state, func.count())
                .join(
                    SourceMessageRevisionRow,
                    SourceMessageRevisionRow.id == MediaRecoveryWorkRow.source_revision_id,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
            )
            counts: dict[str, int] = {
                str(state): int(count)
                for state, count in (
                    await session.execute(
                        query.where(*filters).group_by(MediaRecoveryWorkRow.state)
                    )
                ).all()
            }
            oldest = await session.scalar(
                select(func.min(MediaRecoveryWorkRow.next_attempt_at))
                .join(
                    SourceMessageRevisionRow,
                    SourceMessageRevisionRow.id == MediaRecoveryWorkRow.source_revision_id,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(*filters, MediaRecoveryWorkRow.state.in_(("pending", "retry_wait")))
            )
            return {
                "phase": control.phase if control else "not_started",
                "counts": counts,
                "oldest_due_at": oldest.isoformat() if oldest else None,
                "scan_after_id": control.scan_after_id if control else 0,
                "scan_upper_id": control.scan_upper_id if control else None,
                "canary_completed": control.canary_completed if control else 0,
                "reason": control.reason if control else None,
            }

    async def control(self, action: str) -> None:
        """Pause only media work or activate bounded drain after the canary."""
        async with self.factory() as session, session.begin():
            channel = await self._channel(session)
            if channel is None:
                return
            if action == "pause":
                channel.phase = "paused"
                channel.reason = "operator_pause"
            elif action == "resume":
                channel.phase = "running" if channel.canary_completed >= CANARY_ASSETS else "canary"
                channel.reason = None
            else:
                message = "invalid media control action"
                raise ValueError(message)

    async def pause(self, reason: str) -> None:
        """Pause only media after a systemic discovery/execution failure."""
        async with self.factory() as session, session.begin():
            channel = await self._channel(session)
            if channel is not None:
                channel.phase = "paused"
                channel.reason = reason
