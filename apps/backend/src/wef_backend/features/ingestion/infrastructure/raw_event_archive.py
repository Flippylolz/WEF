"""SQLAlchemy adapter for the verbatim Telegram raw-event archive."""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.application.archive_retry import (
    MAX_DATA_FAILURES,
    RETRY_POLICY_VERSION,
    ArchiveFailure,
)
from wef_backend.features.ingestion.application.raw_replay import ReplayWorkItem
from wef_backend.features.ingestion.application.telegram_events import (
    RawArchiveKind,
    RawArchiveOutcome,
    RawEventRecord,
)
from wef_backend.features.ingestion.infrastructure.archive_retry_store import (
    prepare_retry_versions,
    record_retry,
)
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRow,
    TelegramArchiveExceptionRow,
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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
                    retry_policy_version=RETRY_POLICY_VERSION,
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

    async def unprocessed_batch(
        self,
        limit: int,
        *,
        channel_external_id: str | None = None,
        event_ids: Sequence[UUID] | None = None,
    ) -> Sequence[RawEventRecord]:
        """Return the oldest events that still need a terminal processing outcome."""
        async with self._session_factory() as session, session.begin():
            await prepare_retry_versions(session, datetime.now(UTC), 25, channel_external_id)
            rows = (
                await session.execute(
                    select(TelegramRawEventRow)
                    .where(
                        TelegramRawEventRow.processed_at.is_(None),
                        (
                            (TelegramRawEventRow.data_failure_count < MAX_DATA_FAILURES)
                            & (TelegramRawEventRow.retry_policy_version == RETRY_POLICY_VERSION)
                            & (
                                (TelegramRawEventRow.next_attempt_at.is_(None))
                                | (TelegramRawEventRow.next_attempt_at <= datetime.now(UTC))
                            )
                        )
                        | select(TelegramArchiveResolutionRow.event_id)
                        .where(TelegramArchiveResolutionRow.event_id == TelegramRawEventRow.id)
                        .exists(),
                        *(
                            [TelegramRawEventRow.channel_external_id == channel_external_id]
                            if channel_external_id is not None
                            else []
                        ),
                        *([TelegramRawEventRow.id.in_(event_ids)] if event_ids is not None else []),
                    )
                    .order_by(
                        func.coalesce(
                            TelegramRawEventRow.next_attempt_at, TelegramRawEventRow.received_at
                        ),
                        TelegramRawEventRow.received_at,
                        TelegramRawEventRow.id,
                    )
                    .limit(limit),
                )
            ).scalars()
            return tuple(
                RawEventRecord(
                    id=row.id,
                    event_kind=cast("RawArchiveKind", row.event_kind),
                    channel_external_id=row.channel_external_id,
                    external_message_id=row.external_message_id,
                    payload=cast("Mapping[str, object]", row.payload_json),
                    received_at=row.received_at,
                    attempts=row.attempts,
                    checksum=row.checksum,
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
    ) -> bool:
        """Record one processing attempt; failed events retry until the cap."""
        now = completed_at or datetime.now(UTC)
        if outcome == "failed":
            async with self._session_factory() as session, session.begin():
                return await record_retry(
                    session,
                    event_id,
                    ArchiveFailure(
                        "deferred"
                        if error_category in {"RunLockHeldError", "OSError", "TimeoutError"}
                        else "data",
                        error_category or "UnknownError",
                    ),
                    now,
                    random.SystemRandom().random(),
                )
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                update(TelegramRawEventRow)
                .where(
                    TelegramRawEventRow.id == event_id, TelegramRawEventRow.processed_at.is_(None)
                )
                .values(
                    attempts=TelegramRawEventRow.attempts + 1,
                    outcome=outcome,
                    last_error=error_category,
                    processed_at=now,
                ),
            )
            changed = bool(getattr(result, "rowcount", 0))
            if changed:
                await session.execute(
                    update(TelegramArchiveExceptionRow)
                    .where(TelegramArchiveExceptionRow.event_id == event_id)
                    .values(state="resolved")
                )
            return changed

    async def can_attempt(self, event_id: UUID) -> bool:
        """Repeated source observations cannot bypass durable quarantine/backoff."""
        async with self._session_factory() as session:
            row = await session.get(TelegramRawEventRow, event_id)
            if row is None or row.processed_at is not None:
                return False
            if await session.get(TelegramArchiveResolutionRow, event_id) is not None:
                return True
            return (
                row.retry_policy_version == RETRY_POLICY_VERSION
                and row.data_failure_count < MAX_DATA_FAILURES
                and (row.next_attempt_at is None or row.next_attempt_at <= datetime.now(UTC))
            )

    async def record_failure(self, event_id: UUID, failure: ArchiveFailure) -> bool:
        """Persist a typed safe failure without collapsing transport into corrupt data."""
        async with self._session_factory() as session, session.begin():
            return await record_retry(
                session, event_id, failure, datetime.now(UTC), random.SystemRandom().random()
            )

    async def failed_exhausted_count(self) -> int:
        """Return how many events permanently failed after the bounded retries."""
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(TelegramRawEventRow)
                .where(
                    TelegramRawEventRow.outcome == "failed",
                    TelegramRawEventRow.data_failure_count >= MAX_DATA_FAILURES,
                ),
            )
            return int(value or 0)

    async def stale_message_events(
        self,
        *,
        parser_version: str,
        sentinel_hash: str,  # noqa: ARG002 - protocol parity; staleness is parser drift
        limit: int,
        exclude: frozenset[str] = frozenset(),
    ) -> Sequence[ReplayWorkItem]:
        """Select latest archived message events with stale canonical state."""
        ranked = (
            select(
                TelegramRawEventRow.channel_external_id,
                TelegramRawEventRow.external_message_id,
                TelegramRawEventRow.payload_json,
                func.row_number()
                .over(
                    partition_by=(
                        TelegramRawEventRow.channel_external_id,
                        TelegramRawEventRow.external_message_id,
                    ),
                    order_by=TelegramRawEventRow.received_at.desc(),
                )
                .label("recency"),
            ).where(
                TelegramRawEventRow.event_kind.in_(("new", "edit")),
            )
        ).subquery()
        statement = (
            select(
                ranked.c.channel_external_id,
                ranked.c.external_message_id,
                ranked.c.payload_json,
            )
            .join(
                SourceChannelRow,
                SourceChannelRow.external_id == ranked.c.channel_external_id,
            )
            .join(
                SourceMessageRow,
                (SourceMessageRow.source_channel_id == SourceChannelRow.id)
                & (SourceMessageRow.external_message_id == ranked.c.external_message_id),
            )
            .join(
                OfferSourceRow,
                (OfferSourceRow.source_message_id == SourceMessageRow.id)
                & (OfferSourceRow.relationship == "primary"),
            )
            .join(OfferRow, OfferRow.id == OfferSourceRow.offer_id)
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(
                ranked.c.recency == 1,
                OfferRow.parser_version != parser_version,
            )
            .order_by(ranked.c.channel_external_id, ranked.c.external_message_id)
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            ReplayWorkItem(
                channel_external_id=row.channel_external_id,
                external_message_id=row.external_message_id,
                payload=cast("Mapping[str, object]", row.payload_json),
            )
            for row in rows
            if f"{row.channel_external_id}:{row.external_message_id}" not in exclude
        )

    async def seed_from_history(
        self,
        *,
        chunk_size: int = 500,
    ) -> tuple[int, int]:
        """Backfill the archive from retained history for pre-archive messages.

        Every current source revision already stores its verbatim payload and
        checksum, so replay can cover messages ingested before the archive
        existed. Original mixed text and entity evidence is retained verbatim;
        malformed rows are skipped and counted.
        Returns (seeded, skipped).
        """
        async with self._session_factory() as session:
            selected = await session.execute(
                select(
                    SourceChannelRow.external_id,
                    SourceMessageRow.external_message_id,
                    SourceMessageRow.raw_payload_json,
                    SourceMessageRow.raw_checksum,
                    SourceMessageRow.ingested_at,
                )
                .join(
                    SourceChannelRow,
                    SourceChannelRow.id == SourceMessageRow.source_channel_id,
                )
                .outerjoin(
                    TelegramRawEventRow,
                    (TelegramRawEventRow.channel_external_id == SourceChannelRow.external_id)
                    & (
                        TelegramRawEventRow.external_message_id
                        == SourceMessageRow.external_message_id
                    ),
                )
                .where(
                    TelegramRawEventRow.id.is_(None),
                )
                .order_by(SourceMessageRow.external_message_id),
            )
            rows = selected.all()

        seeded = 0
        skipped = 0
        chunk: list[dict[str, object]] = []
        for row in rows:
            payload = cast("Mapping[str, object]", row.raw_payload_json)
            if _flatten_text(payload) is None:
                skipped += 1
                continue
            chunk.append(
                {
                    "id": uuid4(),
                    "event_kind": "new",
                    "channel_external_id": row.external_id,
                    "external_message_id": row.external_message_id,
                    "payload_json": json.loads(json.dumps(dict(payload))),
                    "checksum": row.raw_checksum,
                    "received_at": row.ingested_at,
                },
            )
            seeded += 1
            if len(chunk) >= chunk_size:
                await _insert_seed_chunk(self._session_factory, chunk)
                chunk = []
        if chunk:
            await _insert_seed_chunk(self._session_factory, chunk)
        return seeded, skipped


def _flatten_text(payload: Mapping[str, object]) -> dict[str, object] | None:
    """Return the payload with Telegram's mixed text flattened for replay."""
    original = payload.get("text", "")
    if isinstance(original, str):
        flattened: object = original
    elif isinstance(original, list):
        parts: list[str] = []
        for segment in original:
            if isinstance(segment, str):
                parts.append(segment)
            elif isinstance(segment, Mapping) and isinstance(segment.get("text"), str):
                parts.append(cast("str", segment["text"]))
            else:
                return None
        flattened = "".join(parts)
    else:
        return None
    seeded_payload = dict(payload)
    seeded_payload["text"] = flattened
    return seeded_payload


async def _insert_seed_chunk(
    session_factory: async_sessionmaker[AsyncSession],
    chunk: list[dict[str, object]],
) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            insert(TelegramRawEventRow)
            .values(chunk)
            .on_conflict_do_nothing(
                constraint="uq_telegram_raw_events_dedupe",
            ),
        )
