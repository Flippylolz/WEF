"""Bounded recovery orchestration with durable work and existing mutation services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import ReviewRunState
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiParseStatus,
)
from wef_backend.features.admin.application.offer_enrichment import BatchState, missing_fields
from wef_backend.features.admin.application.recovery_validation import listing_creation_supported
from wef_backend.features.ingestion.application.extraction import extract_source_property_type

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.admin.application.ingestion_ai_parse import (
        ApplyIngestionAiParse,
        GenerateIngestionAiParse,
        IngestionAiParseStore,
    )
    from wef_backend.features.admin.application.offer_enrichment import (
        OfferAiEnrichmentStore,
        ProcessOfferEnrichmentItem,
        StartOfferEnrichmentBatch,
    )


@dataclass(frozen=True)
class RecoveryWork:
    """Minimized leased work; source text remains in its original revision."""

    id: UUID
    revision_id: UUID
    owner_id: UUID
    claim_id: UUID
    offer_id: UUID | None
    proposal_id: UUID | None
    attempts: int
    missing_fields: tuple[str, ...] = ()


class RecoveryQueue(Protocol):
    """Database checkpoint boundary for the worker."""

    async def enqueue(self, owner: UUID, now: datetime) -> int:
        """Select no more than 100 current eligible revisions in short chunks."""
        ...

    async def claim(self, owner: UUID, now: datetime) -> RecoveryWork | None:
        """Claim one due identity; reclaim expired leases without regenerating results."""
        ...

    async def finish(
        self,
        work: RecoveryWork,
        state: str,
        reason: str | None,
        now: datetime,
        proposal_id: UUID | None = None,
    ) -> None:
        """Compare the claim and current revision, then persist the outcome."""
        ...

    async def retry_local(self, work: RecoveryWork, now: datetime) -> None:
        """Persist bounded local backoff and one terminal systemic exception."""
        ...

    async def cohort_outcome(self, work: RecoveryWork) -> tuple[str, str | None]:
        """Report applied, fully validated observation, or minimized terminal failure."""
        ...

    async def canary_passed(self) -> bool:
        """At least ten distinct revisions completed valid observation."""
        ...

    async def defer_provider(self, work: RecoveryWork, now: datetime) -> bool:
        """Persist the allocation's next eligible time or uncertain attempt state."""
        ...


class AutomaticRecovery:
    """Generate only eligible work; save proposals before guarded application."""

    def __init__(  # noqa: PLR0913, PLR0917 - existing mutation services stay authoritative
        self,
        queue: RecoveryQueue,
        generate: GenerateIngestionAiParse,
        apply: ApplyIngestionAiParse,
        parses: IngestionAiParseStore,
        start: StartOfferEnrichmentBatch,
        process: ProcessOfferEnrichmentItem,
        enrichments: OfferAiEnrichmentStore,
    ) -> None:
        """Reuse authoritative application services for proposal and mutation behavior."""
        self._queue, self._generate, self._apply, self._parses = queue, generate, apply, parses
        self._start, self._process, self._enrichments = start, process, enrichments

    async def tick(self, owner: UUID, now: datetime, *, submit: bool, apply: bool) -> None:
        """One bounded item per cadence; paused submission retains all checkpoints."""
        if not submit:
            return
        await self._queue.enqueue(owner, now)
        work = await self._queue.claim(owner, now)
        if work is None:
            return
        try:
            await self._execute(work, now, apply=apply)
        except AdminDeniedError:
            await self._queue.finish(work, "terminal", "validation_or_snapshot", now)
        except Exception:  # noqa: BLE001 - persist local retries without exposing source/error bodies
            await self._queue.retry_local(work, now)

    async def _execute(  # noqa: C901, PLR0911, PLR0912 - explicit persisted terminal outcomes
        self, work: RecoveryWork, now: datetime, *, apply: bool
    ) -> None:
        owner = work.owner_id
        if work.offer_id is not None:
            batch = await self._enrichments.get_batch(work.id)
            if batch is None:
                snapshot = await self._enrichments.get_offer_snapshot(work.offer_id)
                targets = repairable_offer_fields(work.missing_fields)
                if snapshot is None or not targets.intersection(missing_fields(snapshot)):
                    await self._queue.finish(
                        work, "observed", "already_resolved_or_unsupported", now
                    )
                    return
                protected = await self._enrichments.protected_field_names(work.offer_id)
                if not (targets - protected).intersection(missing_fields(snapshot)):
                    await self._queue.finish(work, "terminal", "protected_conflict", now)
                    return
                batch = await self._start(
                    owner_id=owner,
                    request_id=work.id,
                    offer_ids=(work.offer_id,),
                    limit=1,
                    batch_id=work.id,
                )
            if batch.state in {BatchState.COMPLETED, BatchState.FAILED}:
                state, reason = await self._queue.cohort_outcome(work)
                await self._queue.finish(work, state, reason, now)
                return
            await self._process(
                owner_id=owner,
                batch_id=batch.id,
                request_id=work.id,
                auto_apply=apply and await self._queue.canary_passed(),
            )
            if await self._queue.defer_provider(work, now):
                return
            state, reason = await self._queue.cohort_outcome(work)
            await self._queue.finish(work, state, reason, now)
            return
        run = (
            await self._parses.get_run(work.proposal_id)
            if work.proposal_id
            else await self._parses.get_pending_run(work.revision_id)
        )
        if run is None:
            result = await self._generate(
                owner_id=owner, source_message_revision_id=work.revision_id, request_id=work.id
            )
            if result.status is not IngestionAiParseStatus.GENERATED:
                if result.reason != "schema" and await self._queue.defer_provider(work, now):
                    return
                await self._queue.finish(work, "terminal", "proposal_rejected", now)
                return
            run = result.run
        if run is None or run.owner_user_id != owner:
            await self._queue.finish(work, "terminal", "proposal_unavailable", now)
            return
        if run.state is ReviewRunState.APPLIED:
            await self._queue.finish(work, "applied", None, now, run.id)
            return
        context = await self._parses.get_revision_context(work.revision_id)
        supported = (
            context is not None
            and extract_source_property_type(context.text_original) is not None
            and listing_creation_supported(context.text_original, run.proposed_fields)
        )
        if not supported:
            await self._queue.finish(work, "observed", "creation_calibration_required", now, run.id)
            return
        if apply and await self._queue.canary_passed():
            await self._apply(owner_id=owner, run_id=run.id, request_id=work.id, automatic=True)
            await self._queue.finish(work, "applied", None, now, run.id)
        else:
            await self._queue.finish(work, "observed", "validated_observation", now, run.id)


def repairable_offer_fields(fields: tuple[str, ...]) -> frozenset[str]:
    """Map evidenced parser gaps onto the canonical missing-only field allowlist."""
    mapping = {
        "apartment_price": {"apartment_price_min", "apartment_price_max", "currency"},
        "parking_price": {"parking_price_min", "parking_price_max", "parking_included_in_price"},
        "storage_price": {"storage_price_min", "storage_price_max", "storage_included_in_price"},
        "area_sqm": {"area_min_sqm", "area_max_sqm"},
        "rooms": {"rooms_min", "rooms_max"},
        "market_type": {"market_type"},
    }
    return frozenset(name for field in fields for name in mapping.get(field, set()))
