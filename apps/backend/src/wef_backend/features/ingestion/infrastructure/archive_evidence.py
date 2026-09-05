"""Transaction-scoped archive proof and conservative source ordering."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.archive_processing import (
    ARCHIVE_POLICY_VERSION,
    ArchiveDisposition,
    ArchiveResolution,
)
from wef_backend.features.ingestion.domain.model import canonical_json_checksum
from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
    TelegramSourceTombstoneRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from wef_backend.features.ingestion.application.telegram_events import RawEventRecord
    from wef_backend.features.ingestion.domain.model import RawMessage


class ArchiveEvidenceError(ValueError):
    """Source identity or version cannot safely be resolved from retained evidence."""


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [_plain(v) for v in value]
    return value


def flatten_legacy_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Reproduce only the historical seed transform for provenance comparison."""
    plain = cast("dict[str, object]", _plain(payload))
    original = plain.get("text", "")
    if isinstance(original, list):
        parts: list[str] = []
        for part in original:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, Mapping) and isinstance(part.get("text"), str):
                parts.append(cast("str", part["text"]))
            else:
                msg = "invalid legacy text"
                raise ArchiveEvidenceError(msg)
        plain["text"] = "".join(parts)
    return plain


def legacy_projection_checksums(payload: Mapping[str, object]) -> frozenset[str]:
    """Exact checksums of the known old live reconstruction, not semantic guesses."""
    projections = []
    for candidate in (cast("dict[str, object]", _plain(payload)), flatten_legacy_payload(payload)):
        projection = {
            "id": candidate["id"],
            "type": "message",
            "date_unixtime": str(candidate["date_unixtime"]),
            "text": str(candidate.get("text", "")),
            "from_live": True,
        }
        for key in ("edited_unixtime", "media_group_id"):
            if key in candidate:
                projection[key] = str(candidate[key])
        projections.append(canonical_json_checksum(projection))
    return frozenset(projections)


async def proven_payload(session: AsyncSession, record: RawEventRecord) -> Mapping[str, object]:
    """Resolve corrupt legacy seed shape only through an exact retained revision."""
    stored = await session.get(TelegramRawEventRow, record.id)
    if (
        stored is None
        or stored.channel_external_id != record.channel_external_id
        or stored.external_message_id != record.external_message_id
        or stored.event_kind != record.event_kind
        or stored.checksum != record.checksum
        or stored.payload_json != record.payload
    ):
        msg = "archive record differs from retained identity"
        raise ArchiveEvidenceError(msg)
    if canonical_json_checksum(record.payload) == record.checksum:
        return record.payload
    rows = await session.scalars(
        select(SourceMessageRevisionRow.raw_payload_json)
        .join(SourceMessageRow, SourceMessageRow.id == SourceMessageRevisionRow.source_message_id)
        .join(SourceChannelRow, SourceChannelRow.id == SourceMessageRow.source_channel_id)
        .where(
            SourceChannelRow.external_id == record.channel_external_id,
            SourceMessageRow.external_message_id == record.external_message_id,
            SourceMessageRevisionRow.raw_checksum == record.checksum,
        ),
    )
    for payload in rows:
        original = cast("Mapping[str, object]", payload)
        if (
            canonical_json_checksum(original) == record.checksum
            and flatten_legacy_payload(original) == record.payload
        ):
            return original
    msg = "archive checksum has no exact source proof"
    raise ArchiveEvidenceError(msg)


async def ensure_tombstone(
    session: AsyncSession,
    channel_id: UUID,
    external_id: int,
    deleted_at: datetime,
) -> UUID:
    """Retain deletion even when its source message has never existed locally."""
    await session.execute(
        insert(TelegramSourceTombstoneRow)
        .values(
            id=uuid4(),
            source_channel_id=channel_id,
            external_message_id=external_id,
            deleted_at=deleted_at,
        )
        .on_conflict_do_nothing(index_elements=["source_channel_id", "external_message_id"])
    )
    value = await session.scalar(
        select(TelegramSourceTombstoneRow.id).where(
            TelegramSourceTombstoneRow.source_channel_id == channel_id,
            TelegramSourceTombstoneRow.external_message_id == external_id,
        )
    )
    if value is None:
        msg = "missing committed deletion evidence"
        raise ArchiveEvidenceError(msg)
    return value


async def retained_delete(session: AsyncSession, channel_id: UUID, external_id: int) -> bool:
    """Retain verified archived deletion evidence before any stale source upsert."""
    archived_deletes = await session.scalars(
        select(TelegramRawEventRow)
        .join(
            SourceChannelRow,
            SourceChannelRow.external_id == TelegramRawEventRow.channel_external_id,
        )
        .where(
            SourceChannelRow.id == channel_id,
            TelegramRawEventRow.external_message_id == external_id,
            TelegramRawEventRow.event_kind == "delete",
        )
    )
    for event in archived_deletes:
        payload = cast("Mapping[str, object]", event.payload_json)
        if (
            payload.get("id") == external_id
            and not isinstance(payload.get("id"), bool)
            and canonical_json_checksum(payload) == event.checksum
        ):
            await ensure_tombstone(session, channel_id, external_id, event.received_at)
            return True
    return False


async def source_disposition(  # noqa: PLR0911 - explicit ordered source outcomes
    session: AsyncSession,
    *,
    channel_id: UUID,
    existing: SourceMessageRow | None,
    raw: RawMessage,
    enforce_order: bool,
) -> ArchiveDisposition | None:
    """Guard offer/source mutation before parser hooks or canonical refresh."""
    tombstone = await session.scalar(
        select(TelegramSourceTombstoneRow.id).where(
            TelegramSourceTombstoneRow.source_channel_id == channel_id,
            TelegramSourceTombstoneRow.external_message_id == raw.external_message_id,
        )
    )
    if tombstone is not None:
        return "deleted"
    if existing is not None and existing.deleted_at is not None:
        await ensure_tombstone(session, channel_id, raw.external_message_id, existing.deleted_at)
        return "deleted"
    if await retained_delete(session, channel_id, raw.external_message_id):
        return "deleted"
    if not enforce_order or existing is None or existing.raw_checksum == raw.checksum:
        return None
    version = raw.edited_at or raw.published_at
    current_version = existing.edited_at or existing.published_at
    if version < current_version:
        return "superseded"
    if version > current_version:
        return None
    existing_payload = cast("Mapping[str, object]", existing.raw_payload_json)
    if raw.checksum in legacy_projection_checksums(existing_payload):
        return "already_canonical"
    retained = await session.scalar(
        select(SourceMessageRevisionRow.id)
        .where(
            SourceMessageRevisionRow.source_message_id == existing.id,
            SourceMessageRevisionRow.raw_checksum == raw.checksum,
        )
        .limit(1)
    )
    if retained is not None and existing.raw_checksum in legacy_projection_checksums(
        cast("Mapping[str, object]", raw.raw_payload),
    ):
        newer = await session.scalar(
            select(SourceMessageRevisionRow.id)
            .where(
                SourceMessageRevisionRow.source_message_id == existing.id,
                func.coalesce(
                    SourceMessageRevisionRow.edited_at, SourceMessageRevisionRow.published_at
                )
                > version,
            )
            .limit(1)
        )
        if newer is None:
            return None
    msg = "conflicting source revisions at equal source time"
    raise ArchiveEvidenceError(msg)


def resolution_value(row: TelegramArchiveResolutionRow) -> ArchiveResolution:
    """Project a receipt without raw source values."""
    return ArchiveResolution(
        row.event_id, cast("ArchiveDisposition", row.disposition), row.committed_at
    )


async def write_resolution(
    session: AsyncSession,
    *,
    event_id: UUID,
    channel_id: UUID,
    external_id: int,
    disposition: ArchiveDisposition,
) -> ArchiveResolution:
    """Insert a unique receipt alongside the canonical mutation/no-op."""
    prior = await session.get(TelegramArchiveResolutionRow, event_id)
    if prior is not None:
        return resolution_value(prior)
    event = await session.get(TelegramRawEventRow, event_id)
    channel = await session.get(SourceChannelRow, channel_id)
    if (
        event is None
        or channel is None
        or event.channel_external_id != channel.external_id
        or event.external_message_id != external_id
    ):
        msg = "canonical receipt identity mismatch"
        raise ArchiveEvidenceError(msg)
    revision_id = await session.scalar(
        select(SourceMessageRow.current_revision_id).where(
            SourceMessageRow.source_channel_id == channel_id,
            SourceMessageRow.external_message_id == external_id,
        )
    )
    tombstone_id = await session.scalar(
        select(TelegramSourceTombstoneRow.id).where(
            TelegramSourceTombstoneRow.source_channel_id == channel_id,
            TelegramSourceTombstoneRow.external_message_id == external_id,
        )
    )
    now = datetime.now(UTC)
    row = TelegramArchiveResolutionRow(
        event_id=event_id,
        disposition=disposition,
        source_checksum=event.checksum,
        source_revision_id=revision_id,
        tombstone_id=tombstone_id,
        policy_version=ARCHIVE_POLICY_VERSION,
        committed_at=now,
        previous_outcome=event.outcome,
        previous_attempts=event.attempts,
    )
    session.add(row)
    await session.flush()
    return resolution_value(row)
