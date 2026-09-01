"""SQLAlchemy persistence for source message parse issues."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy import select

from wef_backend.features.ingestion.domain.parse_issue import (
    ParseIssueOutcome,
    SourceMessageParseIssue,
)
from wef_backend.features.ingestion.infrastructure.models import SourceMessageParseIssueRow

if TYPE_CHECKING:

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.parse_issue_serialization import (
        ParseIssueInsert,
    )


async def insert_parse_issue(session: AsyncSession, record: ParseIssueInsert) -> None:
    """Append one parse issue row in the current ingestion transaction."""
    session.add(
        SourceMessageParseIssueRow(
            id=record.id,
            source_channel_id=record.source_channel_id,
            source_message_id=record.source_message_id,
            source_message_revision_id=record.source_message_revision_id,
            external_message_id=record.external_message_id,
            ingest_run_id=record.ingest_run_id,
            parser_version=record.parser_version,
            score=record.score,
            threshold=record.threshold,
            is_candidate=record.is_candidate,
            signals_json=list(record.signals_json),
            warnings_json=list(record.warnings_json),
            issue_outcome=record.issue_outcome.value,
            message_outcome=record.message_outcome.value,
            boundary_band=record.boundary_band,
            signal_combination=record.signal_combination,
            text_excerpt_redacted=record.text_excerpt_redacted,
            offer_id=record.offer_id,
        ),
    )


class SQLAlchemyParseIssueStore:
    """Read recent parse issues for owner admin reporting."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        """Store the async session factory."""
        self._session_factory = session_factory

    async def list_recent(self, *, limit: int = 500) -> tuple[SourceMessageParseIssue, ...]:
        """Return newest parse issues for admin export."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(SourceMessageParseIssueRow)
                    .order_by(SourceMessageParseIssueRow.created_at.desc())
                    .limit(limit),
                )
            ).all()
            return tuple(_to_domain(row) for row in rows)


def _to_domain(row: SourceMessageParseIssueRow) -> SourceMessageParseIssue:
    return SourceMessageParseIssue(
        id=row.id,
        source_channel_id=row.source_channel_id,
        source_message_id=row.source_message_id,
        source_message_revision_id=row.source_message_revision_id,
        external_message_id=row.external_message_id,
        ingest_run_id=row.ingest_run_id,
        parser_version=row.parser_version,
        score=row.score,
        threshold=row.threshold,
        is_candidate=row.is_candidate,
        signals_json=tuple(row.signals_json if isinstance(row.signals_json, list) else ()),
        warnings_json=tuple(row.warnings_json if isinstance(row.warnings_json, list) else ()),
        issue_outcome=ParseIssueOutcome(row.issue_outcome),
        message_outcome=row.message_outcome,
        boundary_band=row.boundary_band,
        signal_combination=row.signal_combination,
        text_excerpt_redacted=row.text_excerpt_redacted,
        offer_id=row.offer_id,
        created_at=row.created_at.astimezone(UTC),
    )
