"""Backfill parse-issue ledger rows for historical non-offer messages."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import select

from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parse_issue_serialization import (
    build_parse_issue_insert,
)
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform, freeze_json
from wef_backend.features.ingestion.domain.model import RawMessage
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageParseIssueRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.parse_issue_store import insert_parse_issue

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class ParseIssueBackfillSummary:
    """Redacted result of one bounded parse-issue backfill run."""

    processed: int
    inserted: int
    skipped_clean: int
    batches: int


def _payload_for_message(*, payload: object, external_message_id: int) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return cast("Mapping[str, object]", payload)
    if payload:
        parsed = json.loads(payload) if isinstance(payload, str) else payload
        if isinstance(parsed, Mapping):
            return cast("Mapping[str, object]", parsed)
    return {"id": external_message_id}


def _row_to_raw(
    *,
    message: SourceMessageRow,
    channel_external_id: str,
    channel_name: str,
) -> RawMessage:
    payload = _payload_for_message(
        payload=message.raw_payload_json,
        external_message_id=message.external_message_id,
    )
    frozen = freeze_json(dict(payload))
    if not isinstance(frozen, Mapping):
        error = "source message payload must freeze as an object"
        raise TypeError(error)
    return RawMessage(
        source=SourceIdentity(
            platform=SourcePlatform.TELEGRAM,
            channel_id=channel_external_id,
            channel_name=channel_name,
            channel_type="public_channel",
        ),
        external_message_id=int(message.external_message_id),
        reply_to_message_id=None,
        published_at=message.published_at,
        edited_at=message.edited_at,
        message_type=message.message_type or "message",
        text=message.text_original or "",
        original_text=message.text_original or "",
        text_entities=(),
        media=(),
        raw_payload=frozen,
        checksum=message.raw_checksum,
    )


async def _eligible_messages(
    session: AsyncSession,
    *,
    limit: int,
) -> list[tuple[SourceMessageRow, str, str]]:
    rows = (
        await session.execute(
            select(
                SourceMessageRow,
                SourceChannelRow.external_id,
                SourceChannelRow.display_name,
            )
            .join(
                SourceChannelRow,
                SourceChannelRow.id == SourceMessageRow.source_channel_id,
            )
            .outerjoin(
                OfferSourceRow,
                OfferSourceRow.source_message_id == SourceMessageRow.id,
            )
            .outerjoin(
                SourceMessageParseIssueRow,
                SourceMessageParseIssueRow.source_message_id == SourceMessageRow.id,
            )
            .where(
                OfferSourceRow.source_message_id.is_(None),
                SourceMessageParseIssueRow.id.is_(None),
            )
            .order_by(SourceMessageRow.external_message_id.desc())
            .limit(limit),
        )
    ).all()
    return [(message, external_id, display_name) for message, external_id, display_name in rows]


async def _process_batch(
    session: AsyncSession,
    *,
    batch_size: int,
) -> tuple[int, int, int]:
    selected = await _eligible_messages(session, limit=batch_size)
    if not selected:
        return 0, 0, 0
    inserted = 0
    skipped = 0
    for message, channel_external_id, channel_name in selected:
        raw = _row_to_raw(
            message=message,
            channel_external_id=channel_external_id,
            channel_name=channel_name or "",
        )
        extraction = extract_listing(raw)
        issue = build_parse_issue_insert(
            extraction=extraction,
            raw=raw,
            message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE,
            channel_id=message.source_channel_id,
            source_message_id=message.id,
            source_message_revision_id=message.current_revision_id,
            ingest_run_id=None,
            offer_id=None,
        )
        if issue is None:
            skipped += 1
            continue
        await session.flush()
        await insert_parse_issue(session, issue)
        inserted += 1
    return inserted, skipped, len(selected)


async def backfill_parse_issues(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None = None,
    batch_size: int = 500,
) -> ParseIssueBackfillSummary:
    """Re-run extraction for historical non-offer messages missing ledger rows."""
    if batch_size <= 0:
        message = "batch_size must be positive"
        raise ValueError(message)
    remaining = limit
    total_processed = 0
    total_inserted = 0
    total_skipped = 0
    batches = 0
    while True:
        current_batch = batch_size if remaining is None else min(batch_size, remaining)
        if current_batch <= 0:
            break
        async with session_factory() as session, session.begin():
            inserted, skipped, processed = await _process_batch(
                session,
                batch_size=current_batch,
            )
        if processed == 0:
            break
        batches += 1
        total_processed += processed
        total_inserted += inserted
        total_skipped += skipped
        if remaining is not None:
            remaining -= processed
            if remaining <= 0:
                break
    return ParseIssueBackfillSummary(
        processed=total_processed,
        inserted=total_inserted,
        skipped_clean=total_skipped,
        batches=batches,
    )
