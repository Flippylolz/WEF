"""SQLAlchemy adapter for ingestion AI parse persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from wef_backend.features.admin.application.ai_review import ProviderOutcome, ReviewRunState
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyStatus,
    IngestionAiParseRun,
    RevisionParseContext,
)
from wef_backend.features.admin.infrastructure.ai_models import IngestionAiParseRunRow
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _run_from_row(row: IngestionAiParseRunRow) -> IngestionAiParseRun:
    proposed = row.proposed_fields
    warnings = row.warnings
    return IngestionAiParseRun(
        id=row.id,
        owner_user_id=row.owner_user_id,
        source_message_id=row.source_message_id,
        source_message_revision_id=row.source_message_revision_id,
        external_message_id=row.external_message_id,
        state=ReviewRunState(row.state),
        model=row.model,
        prompt_version=row.prompt_version,
        schema_version=row.schema_version,
        input_fingerprint=row.input_fingerprint,
        source_checksum=row.source_checksum,
        proposed_fields=tuple(proposed) if isinstance(proposed, list) else (),
        verdict=row.verdict,
        warnings=tuple(warnings) if isinstance(warnings, list) else (),
        token_input=row.token_input,
        token_output=row.token_output,
        provider_latency_ms=row.provider_latency_ms,
        provider_outcome=ProviderOutcome(row.provider_outcome),
        provider_request_id=row.provider_request_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        applied_at=row.applied_at,
        offer_id=row.offer_id,
    )


class SQLAlchemyIngestionAiParseStore:
    """Load revision context and persist guarded ingestion AI parse runs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def get_revision_context(
        self,
        revision_id: UUID,
    ) -> RevisionParseContext | None:
        """Return one revision context, or None when unknown."""
        async with self._session_factory() as session:
            row = await session.get(SourceMessageRevisionRow, revision_id)
            if row is None:
                return None
            return RevisionParseContext(
                revision_id=row.id,
                message_id=row.source_message_id,
                external_message_id=await self._external_message_id(session, row.source_message_id),
                checksum=row.raw_checksum,
                text_original=row.text_original,
            )

    async def has_primary_offer(self, message_id: UUID) -> bool:
        """Return whether one message already has a primary offer link."""
        async with self._session_factory() as session:
            existing = await session.scalar(
                select(OfferSourceRow.id)
                .where(
                    OfferSourceRow.source_message_id == message_id,
                    OfferSourceRow.relationship == "primary",
                )
                .limit(1),
            )
            return existing is not None

    async def get_pending_run(self, revision_id: UUID) -> IngestionAiParseRun | None:
        """Return the pending run for one revision, if any."""
        async with self._session_factory() as session:
            row = await session.scalar(
                select(IngestionAiParseRunRow)
                .where(
                    IngestionAiParseRunRow.source_message_revision_id == revision_id,
                    IngestionAiParseRunRow.state == ReviewRunState.PENDING.value,
                )
                .limit(1),
            )
            return None if row is None else _run_from_row(row)

    async def count_owner_runs_since(
        self,
        owner_id: UUID,
        *,
        since: datetime,
    ) -> int:
        """Count owner AI parse runs created since one UTC instant."""
        async with self._session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(IngestionAiParseRunRow)
                .where(
                    IngestionAiParseRunRow.owner_user_id == owner_id,
                    IngestionAiParseRunRow.created_at >= since,
                ),
            )
            return int(count or 0)

    async def insert_run(self, run: IngestionAiParseRun) -> bool:
        """Insert one run; return False when a pending run already exists."""
        async with self._session_factory() as session:
            session.add(
                IngestionAiParseRunRow(
                    id=run.id,
                    owner_user_id=run.owner_user_id,
                    source_message_id=run.source_message_id,
                    source_message_revision_id=run.source_message_revision_id,
                    external_message_id=run.external_message_id,
                    state=run.state.value,
                    model=run.model,
                    prompt_version=run.prompt_version,
                    schema_version=run.schema_version,
                    input_fingerprint=run.input_fingerprint,
                    source_checksum=run.source_checksum,
                    proposed_fields=list(run.proposed_fields),
                    verdict=run.verdict,
                    warnings=list(run.warnings),
                    token_input=run.token_input,
                    token_output=run.token_output,
                    provider_latency_ms=run.provider_latency_ms,
                    provider_outcome=run.provider_outcome.value,
                    provider_request_id=run.provider_request_id,
                    created_at=run.created_at,
                    expires_at=run.expires_at,
                    applied_at=run.applied_at,
                    offer_id=run.offer_id,
                ),
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
            return True

    async def get_run(self, run_id: UUID) -> IngestionAiParseRun | None:
        """Return one run by id."""
        async with self._session_factory() as session:
            row = await session.get(IngestionAiParseRunRow, run_id)
            return None if row is None else _run_from_row(row)

    async def mark_applied(
        self,
        run_id: UUID,
        *,
        offer_id: UUID,
        applied_at: datetime,
    ) -> IngestionAiApplyStatus:
        """Apply one pending run and return a bounded status."""
        async with self._session_factory() as session:
            row = await session.get(IngestionAiParseRunRow, run_id)
            if row is None:
                return IngestionAiApplyStatus.UNKNOWN
            if row.state == ReviewRunState.APPLIED.value:
                return IngestionAiApplyStatus.APPLIED
            if row.state != ReviewRunState.PENDING.value:
                return IngestionAiApplyStatus.STALE
            updated = await session.execute(
                update(IngestionAiParseRunRow)
                .where(
                    IngestionAiParseRunRow.id == run_id,
                    IngestionAiParseRunRow.state == ReviewRunState.PENDING.value,
                )
                .values(
                    state=ReviewRunState.APPLIED.value,
                    applied_at=applied_at,
                    offer_id=offer_id,
                ),
            )
            if int(getattr(updated, "rowcount", 0) or 0) != 1:
                await session.rollback()
                return IngestionAiApplyStatus.COLLISION
            await session.commit()
            return IngestionAiApplyStatus.APPLIED

    async def mark_failed(self, run_id: UUID) -> bool:
        """Dismiss one pending run so the revision can be regenerated."""
        async with self._session_factory() as session:
            updated = await session.execute(
                update(IngestionAiParseRunRow)
                .where(
                    IngestionAiParseRunRow.id == run_id,
                    IngestionAiParseRunRow.state == ReviewRunState.PENDING.value,
                )
                .values(state=ReviewRunState.FAILED.value),
            )
            if int(getattr(updated, "rowcount", 0) or 0) != 1:
                await session.rollback()
                return False
            await session.commit()
            return True

    async def _external_message_id(self, session: AsyncSession, message_id: UUID) -> int:
        external = await session.scalar(
            select(SourceMessageRow.external_message_id).where(SourceMessageRow.id == message_id),
        )
        if external is None:
            message = "source message not found"
            raise RuntimeError(message)
        return int(external)
