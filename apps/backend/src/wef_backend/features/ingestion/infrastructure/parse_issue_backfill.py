"""Backfill parse-issue ledger rows for historical non-offer messages."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import exists, select, true

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.parse_issue_serialization import (
    build_parse_issue_insert,
)
from wef_backend.features.ingestion.application.parse_quality import POLICY_VERSION
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform, freeze_json
from wef_backend.features.ingestion.domain.model import RawMessage
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    ParseEvaluationRow,
    SourceChannelRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.parse_evaluation_store import (
    record_parse_evaluation,
)
from wef_backend.features.ingestion.infrastructure.parse_issue_store import insert_parse_issue

if TYPE_CHECKING:
    from uuid import UUID

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
    after_id: UUID | None = None,
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
            .where(
                SourceMessageRow.deleted_at.is_(None),
                SourceMessageRow.id > after_id if after_id else true(),
                ~exists().where(
                    ParseEvaluationRow.source_message_revision_id
                    == SourceMessageRow.current_revision_id,
                    ParseEvaluationRow.parser_version == PARSER_VERSION,
                    ParseEvaluationRow.policy_version == POLICY_VERSION,
                ),
            )
            .order_by(SourceMessageRow.id)
            .limit(limit),
        )
    ).all()
    return [(message, external_id, display_name) for message, external_id, display_name in rows]


async def _process_batch(
    session: AsyncSession,
    *,
    batch_size: int,
    after_id: UUID | None = None,
) -> tuple[int, int, int, UUID | None]:
    selected = await _eligible_messages(session, limit=batch_size, after_id=after_id)
    if not selected:
        return 0, 0, 0, after_id
    inserted = 0
    skipped = 0
    for message, channel_external_id, channel_name in selected:
        raw = _row_to_raw(
            message=message,
            channel_external_id=channel_external_id,
            channel_name=channel_name or "",
        )
        extraction = extract_listing(raw)
        observed = await record_parse_evaluation(
            session,
            message_id=message.id,
            revision_id=message.current_revision_id,
            text=raw.text,
            extraction=extraction,
        )
        if not observed:
            skipped += 1
            continue
        offer_id = await session.scalar(
            select(OfferSourceRow.offer_id)
            .where(
                OfferSourceRow.source_message_id == message.id,
                OfferSourceRow.relationship == "primary",
            )
            .limit(1)
        )
        issue = build_parse_issue_insert(
            extraction=extraction,
            raw=raw,
            message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE,
            channel_id=message.source_channel_id,
            source_message_id=message.id,
            source_message_revision_id=message.current_revision_id,
            ingest_run_id=None,
            offer_id=offer_id,
        )
        if issue is None:
            skipped += 1
            continue
        await session.flush()
        await insert_parse_issue(session, issue)
        inserted += 1
    return inserted, skipped, len(selected), selected[-1][0].id


async def backfill_parse_issues(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None = 100,
    batch_size: int = 10,
) -> ParseIssueBackfillSummary:
    """Evaluate current source revisions in bounded restartable observation batches."""
    if batch_size <= 0:
        message = "batch_size must be positive"
        raise ValueError(message)
    batch_size = min(batch_size, 10)
    remaining = limit
    total_processed = 0
    total_inserted = 0
    total_skipped = 0
    batches = 0
    after_id = None
    while True:
        current_batch = batch_size if remaining is None else min(batch_size, remaining)
        if current_batch <= 0:
            break
        async with session_factory() as session, session.begin():
            inserted, skipped, processed, after_id = await _process_batch(
                session,
                batch_size=current_batch,
                after_id=after_id,
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
