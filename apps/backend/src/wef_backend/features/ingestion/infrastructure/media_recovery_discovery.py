"""Bounded chronological discovery retaining association evidence across restarts."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.media_grouping import (
    GROUPING_VERSION,
    StatefulMediaGrouper,
)
from wef_backend.features.ingestion.application.media_recovery import MEDIA_RECOVERY_POLICY
from wef_backend.features.ingestion.domain import GroupingInput, SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.domain.media_storage import (
    TRANSFORM_VERSION,
    descriptor_identity,
)
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.models import (
    MediaRecoveryChannelRow,
    MediaRecoveryIntentionRow,
    MediaRecoveryWorkRow,
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.domain.model import RawMessage


async def discover_media(
    factory: async_sessionmaker[AsyncSession], external_id: str, limit: int
) -> int:
    """Bound initial discovery with a durable watermark and reuse later revision context."""
    async with factory() as session, session.begin():
        channel = await session.scalar(
            select(SourceChannelRow).where(SourceChannelRow.external_id == external_id)
        )
        if channel is None:
            return 0
        await session.execute(
            insert(MediaRecoveryChannelRow)
            .values(source_channel_id=channel.id)
            .on_conflict_do_nothing()
        )
        state = await session.scalar(
            select(MediaRecoveryChannelRow)
            .where(MediaRecoveryChannelRow.source_channel_id == channel.id)
            .with_for_update()
        )
        if state is None:
            message = "media discovery state missing"
            raise RuntimeError(message)
        if state.phase == "paused":
            return 0
        identity = SourceIdentity(
            SourcePlatform.TELEGRAM, external_id, channel.display_name, "public_channel"
        )
        if state.scan_upper_id is None:
            state.scan_upper_id = (
                await session.scalar(
                    select(func.max(SourceMessageRow.external_message_id)).where(
                        SourceMessageRow.source_channel_id == channel.id
                    )
                )
                or 0
            )
        rows = list(
            await session.scalars(
                select(SourceMessageRow)
                .where(
                    SourceMessageRow.source_channel_id == channel.id,
                    SourceMessageRow.external_message_id > state.scan_after_id,
                    SourceMessageRow.external_message_id <= state.scan_upper_id,
                )
                .order_by(SourceMessageRow.external_message_id)
                .limit(limit)
            )
        )
        grouper = StatefulMediaGrouper()
        grouper.restore_continuation(
            state.grouping_json if isinstance(state.grouping_json, dict) else {}
        )
        for source in rows:
            await _discover_revision(session, identity, source, grouper)
            state.scan_after_id = source.external_message_id
            state.grouping_json = grouper.continuation()
        if rows:
            return len(rows)
        # The frozen range is complete. Process older revised intentions using the
        # grouping boundary recorded for their earlier revision, never queue order.
        pending = list(
            await session.scalars(
                select(SourceMessageRow)
                .join(
                    MediaRecoveryIntentionRow,
                    MediaRecoveryIntentionRow.source_revision_id
                    == SourceMessageRow.current_revision_id,
                )
                .where(
                    SourceMessageRow.source_channel_id == channel.id,
                    SourceMessageRow.external_message_id <= state.scan_after_id,
                    MediaRecoveryIntentionRow.discovered.is_(False),
                )
                .order_by(MediaRecoveryIntentionRow.created_at)
                .limit(limit)
            )
        )
        for source in pending:
            context = await session.scalar(
                select(MediaRecoveryIntentionRow.context_json)
                .join(
                    SourceMessageRevisionRow,
                    SourceMessageRevisionRow.id == MediaRecoveryIntentionRow.source_revision_id,
                )
                .where(
                    SourceMessageRevisionRow.source_message_id == source.id,
                    MediaRecoveryIntentionRow.context_json.is_not(None),
                )
                .order_by(SourceMessageRevisionRow.revision_number)
                .limit(1)
            )
            previous = StatefulMediaGrouper()
            previous.restore_continuation(context if isinstance(context, dict) else {})
            await _discover_revision(session, identity, source, previous)
        # Extend the historical range only after handling this bounded page. New
        # canonical intentions remain durable while discovery catches up.
        state.scan_upper_id = (
            await session.scalar(
                select(func.max(SourceMessageRow.external_message_id)).where(
                    SourceMessageRow.source_channel_id == channel.id
                )
            )
            or state.scan_after_id
        )
        return len(pending)


async def _discover_revision(
    session: AsyncSession,
    identity: SourceIdentity,
    source: SourceMessageRow,
    grouper: StatefulMediaGrouper,
) -> None:
    await session.execute(
        insert(MediaRecoveryIntentionRow)
        .values(source_revision_id=source.current_revision_id)
        .on_conflict_do_nothing()
    )
    intention = await session.get(MediaRecoveryIntentionRow, source.current_revision_id)
    if intention is None:
        message = "media discovery intention missing"
        raise RuntimeError(message)
    intention.context_json = grouper.continuation()
    if not isinstance(source.raw_payload_json, dict):
        message = "media source payload is invalid"
        raise TypeError(message)
    raw = decode_archived_payload(source.raw_payload_json, identity)
    await _seed_explicit(session, source, raw, grouper)
    # Deleted messages are boundaries, not active association owners.
    extraction = extract_listing(raw)
    if source.deleted_at is not None:
        grouper.reset()
        intention.discovered = True
        return
    dispositions = grouper.ingest(GroupingInput(raw, extraction.decision))
    now = datetime.now(UTC)
    for disposition in dispositions:
        association = disposition.association
        owner = None
        if association is not None:
            owner = (
                await session.execute(
                    select(OfferSourceRow.offer_id, SourceMessageRow.current_revision_id)
                    .join(
                        SourceMessageRow,
                        SourceMessageRow.id == OfferSourceRow.source_message_id,
                    )
                    .where(
                        OfferSourceRow.relationship == "primary",
                        SourceMessageRow.source_channel_id == source.source_channel_id,
                        SourceMessageRow.external_message_id == association.listing_message_id,
                        SourceMessageRow.deleted_at.is_(None),
                    )
                )
            ).first()
        descriptor = disposition.reference.descriptor
        await session.execute(
            insert(MediaRecoveryWorkRow)
            .values(
                id=uuid4(),
                source_revision_id=source.current_revision_id,
                ordinal=disposition.reference.media_index,
                descriptor_identity=descriptor_identity(descriptor),
                grouping_version=GROUPING_VERSION,
                transform_version=TRANSFORM_VERSION,
                policy_version=MEDIA_RECOVERY_POLICY,
                descriptor_json=asdict(descriptor),
                offer_id=owner[0] if owner else None,
                association_revision_id=owner[1] if owner else None,
                association_rule=association.rule.value if association and owner else None,
                association_confidence=(1.0 if association.confidence.value == "high" else 0.6)
                if association and owner
                else None,
                state="pending" if owner else "unsupported",
                next_attempt_at=now,
                reason=None if owner else "unassociated_source_evidence",
            )
            .on_conflict_do_nothing()
        )
    intention.discovered = True
    await session.execute(
        update(MediaRecoveryIntentionRow)
        .where(
            MediaRecoveryIntentionRow.source_revision_id.in_(
                select(SourceMessageRevisionRow.id).where(
                    SourceMessageRevisionRow.source_message_id == source.id,
                    SourceMessageRevisionRow.id != source.current_revision_id,
                )
            ),
            MediaRecoveryIntentionRow.discovered.is_(False),
        )
        .values(discovered=True)
    )


async def _seed_explicit(
    session: AsyncSession, source: SourceMessageRow, raw: RawMessage, grouper: StatefulMediaGrouper
) -> None:
    query = (
        select(SourceMessageRow.external_message_id)
        .join(OfferSourceRow, OfferSourceRow.source_message_id == SourceMessageRow.id)
        .where(
            OfferSourceRow.relationship == "primary",
            SourceMessageRow.source_channel_id == source.source_channel_id,
            SourceMessageRow.deleted_at.is_(None),
            SourceMessageRow.external_message_id <= source.external_message_id,
        )
    )
    if raw.reply_to_message_id is not None:
        reply = await session.scalar(
            query.where(SourceMessageRow.external_message_id == raw.reply_to_message_id)
        )
        if reply is not None:
            grouper.seed_anchor(reply)
    if raw.media_group_id is not None:
        group = await session.scalar(
            query.where(
                func.coalesce(
                    SourceMessageRow.raw_payload_json["grouped_id"].astext,
                    SourceMessageRow.raw_payload_json["media_group_id"].astext,
                )
                == raw.media_group_id
            )
            .order_by(SourceMessageRow.external_message_id)
            .limit(1)
        )
        if group is not None:
            grouper.seed_anchor(group, group_id=raw.media_group_id)
