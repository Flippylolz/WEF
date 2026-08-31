"""SQLAlchemy adapter for place AI review persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from wef_backend.features.admin.application.ai_review import (
    AiApplyStatus,
    LocationAiSnapshot,
    PlaceReviewRun,
    ProposedField,
    ProviderOutcome,
    ReviewRunState,
    SourceRevisionEvidence,
    location_snapshot_version,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_models import (
    OfferAiEnrichmentBatchRow,
    OfferAiEnrichmentItemRow,
)
from wef_backend.features.admin.infrastructure.ai_models import PlaceAiReviewRunRow
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.domain.geocoding import (
    REVIEW_POLICY_VERSION,
    SelectionReason,
)
from wef_backend.features.ingestion.infrastructure.models import (
    LocationGeocodeSelectionRow,
    OfferSourceRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyPlaceAiReviewStore:
    """Load snapshots/sources and persist guarded place-review runs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def get_location_snapshot(self, location_id: UUID) -> LocationAiSnapshot | None:
        """Return one location snapshot, or None when unknown."""
        async with self._session_factory() as session:
            row = await session.get(LocationRow, location_id)
            if row is None:
                return None
            return _snapshot(row)

    async def list_current_source_revisions(
        self,
        location_id: UUID,
        *,
        limit: int,
    ) -> tuple[SourceRevisionEvidence, ...]:
        """Return newest distinct current revisions linked through offer sources."""
        async with self._session_factory() as session:
            stmt = (
                select(SourceMessageRevisionRow)
                .join(
                    OfferSourceRow,
                    OfferSourceRow.source_message_revision_id == SourceMessageRevisionRow.id,
                )
                .join(OfferRow, OfferRow.id == OfferSourceRow.offer_id)
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(
                    OfferRow.location_id == location_id,
                    SourceMessageRow.current_revision_id == SourceMessageRevisionRow.id,
                )
                .order_by(
                    SourceMessageRevisionRow.published_at.desc(),
                    SourceMessageRevisionRow.id.desc(),
                )
            )
            rows = (await session.execute(stmt)).scalars().all()
        unique: list[SourceRevisionEvidence] = []
        seen: set[UUID] = set()
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            unique.append(
                SourceRevisionEvidence(
                    revision_id=row.id,
                    checksum=row.raw_checksum,
                    published_at=row.published_at,
                    text_original=row.text_original,
                ),
            )
            if len(unique) >= limit:
                break
        return tuple(unique)

    async def count_current_source_revisions(self, location_id: UUID) -> int:
        """Count distinct current source revisions linked to the location."""
        async with self._session_factory() as session:
            stmt = (
                select(func.count(func.distinct(SourceMessageRevisionRow.id)))
                .select_from(SourceMessageRevisionRow)
                .join(
                    OfferSourceRow,
                    OfferSourceRow.source_message_revision_id == SourceMessageRevisionRow.id,
                )
                .join(OfferRow, OfferRow.id == OfferSourceRow.offer_id)
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(
                    OfferRow.location_id == location_id,
                    SourceMessageRow.current_revision_id == SourceMessageRevisionRow.id,
                )
            )
            count = await session.scalar(stmt)
        return int(count or 0)

    async def count_owner_runs_since(self, owner_id: UUID, *, since: datetime) -> int:
        """Count this owner's review runs and enrichment provider calls since ``since``."""
        async with self._session_factory() as session:
            place = await session.scalar(
                select(func.count()).where(
                    PlaceAiReviewRunRow.owner_user_id == owner_id,
                    PlaceAiReviewRunRow.created_at >= since,
                ),
            )
            enrichment = await session.scalar(
                select(func.count())
                .select_from(OfferAiEnrichmentItemRow)
                .join(
                    OfferAiEnrichmentBatchRow,
                    OfferAiEnrichmentBatchRow.id == OfferAiEnrichmentItemRow.batch_id,
                )
                .where(
                    OfferAiEnrichmentBatchRow.owner_user_id == owner_id,
                    OfferAiEnrichmentItemRow.provider_called_at >= since,
                ),
            )
        return int(place or 0) + int(enrichment or 0)

    async def insert_run(self, run: PlaceReviewRun) -> bool:
        """Persist a new run. False when a pending run already exists."""
        async with self._session_factory() as session:
            session.add(_to_row(run))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
        return True

    async def get_run(self, run_id: UUID) -> PlaceReviewRun | None:
        """Return one run by id."""
        async with self._session_factory() as session:
            row = await session.get(PlaceAiReviewRunRow, run_id)
            if row is None:
                return None
            return _from_row(row)

    async def get_pending_run(self, location_id: UUID) -> PlaceReviewRun | None:
        """Return the pending run for a location, if any."""
        async with self._session_factory() as session:
            stmt = select(PlaceAiReviewRunRow).where(
                PlaceAiReviewRunRow.location_id == location_id,
                PlaceAiReviewRunRow.state == ReviewRunState.PENDING.value,
            )
            row = await session.scalar(stmt)
            if row is None:
                return None
            return _from_row(row)

    async def apply_selected_fields(  # noqa: PLR0913
        self,
        *,
        run: PlaceReviewRun,
        snapshot: LocationAiSnapshot,
        display_name: str,
        display_address: str,
        district: str | None,
        normalized_address: str,
        normalized_address_hash: str,
        return_to_review: bool,
        applied_fields: tuple[str, ...],
        actor_id: str,
        decided_at: datetime,
    ) -> AiApplyStatus:
        """Apply selected fields, lineage, and mark the run applied."""
        try:
            async with self._session_factory.begin() as session:
                location = await session.get(LocationRow, snapshot.id, with_for_update=True)
                review = await session.get(PlaceAiReviewRunRow, run.id, with_for_update=True)
                if location is None or review is None:
                    return AiApplyStatus.UNKNOWN
                if review.state != ReviewRunState.PENDING.value:
                    return AiApplyStatus.STALE
                current = _snapshot(location)
                if location_snapshot_version(current) != run.location_snapshot_version:
                    return AiApplyStatus.STALE
                collision = await session.scalar(
                    select(LocationRow.id).where(
                        LocationRow.normalized_address_hash == normalized_address_hash,
                        LocationRow.id != location.id,
                    ),
                )
                if collision is not None:
                    return AiApplyStatus.COLLISION
                to_state = "needs_review" if return_to_review else location.review_status
                if return_to_review:
                    latest_version = await session.scalar(
                        select(func.max(LocationGeocodeSelectionRow.selection_version)).where(
                            LocationGeocodeSelectionRow.location_id == location.id,
                        ),
                    )
                    session.add(
                        LocationGeocodeSelectionRow(
                            id=uuid4(),
                            location_id=location.id,
                            geocode_result_id=location.selected_geocode_result_id,
                            from_state=location.review_status,
                            to_state="needs_review",
                            reason_code=SelectionReason.AI_ASSISTED_CORRECTION.value,
                            actor_type="operator",
                            actor_id=actor_id,
                            review_policy_version=REVIEW_POLICY_VERSION,
                            selection_version=(latest_version or 0) + 1,
                            decided_at=decided_at,
                        ),
                    )
                await session.execute(
                    update(LocationRow)
                    .where(LocationRow.id == location.id)
                    .values(
                        display_name=display_name,
                        display_address=display_address,
                        district=district,
                        normalized_address=normalized_address,
                        normalized_address_hash=normalized_address_hash,
                        review_status=to_state,
                        updated_at=decided_at,
                    ),
                )
                await session.execute(
                    update(PlaceAiReviewRunRow)
                    .where(PlaceAiReviewRunRow.id == run.id)
                    .values(
                        state=ReviewRunState.APPLIED.value,
                        applied_at=decided_at,
                        applied_fields=list(applied_fields),
                    ),
                )
        except IntegrityError:
            return AiApplyStatus.COLLISION
        return AiApplyStatus.APPLIED


def _snapshot(row: LocationRow) -> LocationAiSnapshot:
    return LocationAiSnapshot(
        id=row.id,
        display_name=row.display_name,
        display_address=row.display_address,
        district=row.district,
        review_status=row.review_status,
        updated_at=row.updated_at,
        normalized_address_hash=row.normalized_address_hash,
    )


def _to_row(run: PlaceReviewRun) -> PlaceAiReviewRunRow:
    return PlaceAiReviewRunRow(
        id=run.id,
        owner_user_id=run.owner_user_id,
        location_id=run.location_id,
        state=run.state.value,
        model=run.model,
        prompt_version=run.prompt_version,
        schema_version=run.schema_version,
        input_fingerprint=run.input_fingerprint,
        source_revision_ids=[str(item) for item in run.source_revision_ids],
        source_checksums=list(run.source_checksums),
        location_snapshot_version=run.location_snapshot_version,
        proposed_fields=[
            {
                "field_name": item.field_name,
                "action": item.action,
                "current_value": item.current_value,
                "proposed_value": item.proposed_value,
                "confidence": item.confidence,
                "evidence_revision_ids": list(item.evidence_revision_ids),
                "rationale_code": item.rationale_code,
            }
            for item in run.proposed_fields
        ],
        verdict=run.verdict,
        warnings=list(run.warnings),
        token_input=run.token_input,
        token_output=run.token_output,
        provider_latency_ms=run.provider_latency_ms,
        provider_outcome=run.provider_outcome.value,
        provider_request_id=run.provider_request_id,
        selected_source_count=run.selected_source_count,
        omitted_source_count=run.omitted_source_count,
        created_at=run.created_at,
        expires_at=run.expires_at,
        applied_at=run.applied_at,
        applied_fields=list(run.applied_fields),
    )


def _from_row(row: PlaceAiReviewRunRow) -> PlaceReviewRun:
    fields_raw = row.proposed_fields if isinstance(row.proposed_fields, list) else []
    fields: list[ProposedField] = []
    for item in fields_raw:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence_revision_ids")
        fields.append(
            ProposedField(
                field_name=str(item.get("field_name")),
                action=str(item.get("action")),
                current_value=item.get("current_value")
                if isinstance(item.get("current_value"), str)
                else None,
                proposed_value=item.get("proposed_value")
                if isinstance(item.get("proposed_value"), str)
                else None,
                confidence=str(item.get("confidence")),
                evidence_revision_ids=tuple(
                    str(value) for value in evidence if isinstance(evidence, list)
                )
                if isinstance(evidence, list)
                else (),
                rationale_code=str(item.get("rationale_code")),
            ),
        )
    source_ids = row.source_revision_ids if isinstance(row.source_revision_ids, list) else []
    checksums = row.source_checksums if isinstance(row.source_checksums, list) else []
    warnings = row.warnings if isinstance(row.warnings, list) else []
    applied = row.applied_fields if isinstance(row.applied_fields, list) else []
    return PlaceReviewRun(
        id=row.id,
        owner_user_id=row.owner_user_id,
        location_id=row.location_id,
        state=ReviewRunState(row.state),
        model=row.model,
        prompt_version=row.prompt_version,
        schema_version=row.schema_version,
        input_fingerprint=row.input_fingerprint,
        source_revision_ids=tuple(UUID(str(item)) for item in source_ids),
        source_checksums=tuple(str(item) for item in checksums),
        location_snapshot_version=row.location_snapshot_version,
        proposed_fields=tuple(fields),
        verdict=row.verdict,
        warnings=tuple(str(item) for item in warnings),
        token_input=row.token_input,
        token_output=row.token_output,
        provider_latency_ms=row.provider_latency_ms,
        provider_outcome=ProviderOutcome(row.provider_outcome),
        provider_request_id=row.provider_request_id,
        selected_source_count=row.selected_source_count,
        omitted_source_count=row.omitted_source_count,
        created_at=row.created_at,
        expires_at=row.expires_at,
        applied_at=row.applied_at,
        applied_fields=tuple(str(item) for item in applied),
    )
