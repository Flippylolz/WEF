"""PostgreSQL coordination and read models for staged complete imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.application.complete_import import (
    CompleteImportStage,
    CompleteImportStatus,
    ProviderReservation,
    RunLease,
)
from wef_backend.features.ingestion.application.persistence import normalized_location_key
from wef_backend.features.ingestion.domain.geocoding import (
    NORMALIZER_VERSION,
    REQUEST_VERSION,
    SelectionReason,
)
from wef_backend.features.ingestion.infrastructure.models import (
    CompleteImportRunRow,
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
    MediaAssetRow,
    MediaDerivativeRow,
    MediaDispositionAttemptRow,
    OfferSourceRow,
    ProviderAttemptRow,
    ProviderDailyBudgetRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.domain import SourceIdentity
    from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider


class CompleteImportLeaseHeldError(RuntimeError):
    """Another non-expired owner controls the exact source run."""


class StaleCompleteImportLeaseError(RuntimeError):
    """A fenced owner attempted to checkpoint after takeover."""


RECURRING_GEOCODE_SOURCE_CHECKSUM = "recurring-live-geocode"
_RECURRING_GEOCODE_OWNER = "recurring-geocode"
_RECURRING_GEOCODE_LEASE = timedelta(days=3650)


@dataclass(frozen=True, slots=True)
class LocationWorkItem:
    """Minimum internal fields needed for one geocode resolution."""

    location_id: UUID
    address: str
    district: str | None


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """Current source/revision identity and optional canonical offer."""

    source_message_id: UUID
    revision_id: UUID
    offer_id: UUID | None


@dataclass(frozen=True, slots=True)
class ImportVerification:
    """Aggregate terminal database/storage reconciliation counts."""

    source_messages: int
    source_revisions: int
    offers: int
    locations: int
    accepted_locations: int
    media_assets: int
    media_derivatives: int
    media_dispositions: int
    provider_attempts: int


class SQLAlchemyCompleteImportRepository:
    """Bounded transactions for planning, leases, budgets, and reconciliation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the shared lazy session factory."""
        self._session_factory = session_factory

    async def existing_source_checksums(self, channel: SourceIdentity) -> Mapping[int, str]:
        """Return current exact checksums without creating source state."""
        async with self._session_factory() as session:
            channel_id = await self._channel_id(session, channel)
            if channel_id is None:
                return {}
            rows = await session.execute(
                select(SourceMessageRow.external_message_id, SourceMessageRow.raw_checksum).where(
                    SourceMessageRow.source_channel_id == channel_id,
                ),
            )
            return {int(message_id): checksum for message_id, checksum in rows}

    async def claim_run(  # noqa: PLR0913
        self,
        *,
        source_channel_id: UUID,
        source_checksum: str,
        source_size: int,
        pipeline_version: str,
        owner_id: str,
        stage: CompleteImportStage,
        now: datetime,
        lease_duration: timedelta,
    ) -> RunLease:
        """Create, resume, or take over only an expired exact-source run."""
        run_id = uuid4()
        async with self._session_factory() as session, session.begin():
            inserted = await session.scalar(
                insert(CompleteImportRunRow)
                .values(
                    id=run_id,
                    source_channel_id=source_channel_id,
                    source_checksum=source_checksum,
                    source_size=source_size,
                    pipeline_version=pipeline_version,
                    status=CompleteImportStatus.RUNNING.value,
                    stage=stage.value,
                    owner_id=owner_id,
                    fencing_token=1,
                    lease_expires_at=now + lease_duration,
                    checkpoint_json={},
                    counts_json={},
                    pause_reason=None,
                    next_eligible_at=None,
                    started_at=now,
                    updated_at=now,
                    finished_at=None,
                )
                .on_conflict_do_nothing(
                    constraint="uq_complete_import_runs_identity",
                )
                .returning(CompleteImportRunRow.id),
            )
            row = await session.scalar(
                select(CompleteImportRunRow)
                .where(
                    CompleteImportRunRow.source_channel_id == source_channel_id,
                    CompleteImportRunRow.source_checksum == source_checksum,
                    CompleteImportRunRow.pipeline_version == pipeline_version,
                )
                .with_for_update(),
            )
            if row is None:
                message = "complete import run disappeared during claim"
                raise RuntimeError(message)
            if inserted is None:
                if (
                    row.status == CompleteImportStatus.RUNNING.value
                    and row.lease_expires_at > now
                    and row.owner_id != owner_id
                ):
                    raise CompleteImportLeaseHeldError
                row.owner_id = owner_id
                row.fencing_token += 1
                row.status = CompleteImportStatus.RUNNING.value
                row.stage = stage.value
                row.lease_expires_at = now + lease_duration
                row.pause_reason = None
                row.next_eligible_at = None
                row.updated_at = now
                row.finished_at = None
            return self._lease(row)

    async def checkpoint_run(  # noqa: PLR0913
        self,
        lease: RunLease,
        *,
        stage: CompleteImportStage,
        status: CompleteImportStatus,
        checkpoint: Mapping[str, object],
        counts: Mapping[str, object],
        now: datetime,
        lease_duration: timedelta,
        pause_reason: str | None = None,
        next_eligible_at: datetime | None = None,
    ) -> RunLease:
        """Fence and atomically persist stage progress with lease renewal."""
        terminal = status in {CompleteImportStatus.FAILED, CompleteImportStatus.SUCCEEDED}
        expires = now if status is CompleteImportStatus.PAUSED else now + lease_duration
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                update(CompleteImportRunRow)
                .where(
                    CompleteImportRunRow.id == lease.run_id,
                    CompleteImportRunRow.owner_id == lease.owner_id,
                    CompleteImportRunRow.fencing_token == lease.fencing_token,
                )
                .values(
                    stage=stage.value,
                    status=status.value,
                    checkpoint_json=dict(checkpoint),
                    counts_json=dict(counts),
                    lease_expires_at=expires,
                    pause_reason=pause_reason,
                    next_eligible_at=next_eligible_at,
                    updated_at=now,
                    finished_at=now if terminal else None,
                )
                .returning(CompleteImportRunRow),
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise StaleCompleteImportLeaseError
            return self._lease(row)

    async def release_run(self, lease: RunLease, *, now: datetime) -> RunLease:
        """Release a successful explicit stage while retaining its checkpoint."""
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                update(CompleteImportRunRow)
                .where(
                    CompleteImportRunRow.id == lease.run_id,
                    CompleteImportRunRow.owner_id == lease.owner_id,
                    CompleteImportRunRow.fencing_token == lease.fencing_token,
                )
                .values(
                    status=CompleteImportStatus.PAUSED.value,
                    lease_expires_at=now,
                    pause_reason="operator_stage_complete",
                    next_eligible_at=now,
                    updated_at=now,
                )
                .returning(CompleteImportRunRow),
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise StaleCompleteImportLeaseError
            return self._lease(row)

    async def reserve_provider_attempt(  # noqa: PLR0913
        self,
        *,
        run_id: UUID,
        provider: GeocodeProvider,
        account_identity: str,
        query_hash: str,
        daily_limit: int,
        minimum_interval: timedelta,
        now: datetime,
    ) -> ProviderReservation | None:
        """Reserve quota and allocate one globally spaced not-before slot."""
        budget_date = now.astimezone(UTC).date()
        async with self._session_factory() as session, session.begin():
            await session.execute(
                insert(ProviderDailyBudgetRow)
                .values(
                    provider=provider.value,
                    budget_date=budget_date,
                    account_identity=account_identity,
                    used_attempts=0,
                    last_not_before=None,
                    updated_at=now,
                )
                .on_conflict_do_nothing(),
            )
            budget = await session.scalar(
                select(ProviderDailyBudgetRow)
                .where(
                    ProviderDailyBudgetRow.provider == provider.value,
                    ProviderDailyBudgetRow.budget_date == budget_date,
                    ProviderDailyBudgetRow.account_identity == account_identity,
                )
                .with_for_update(),
            )
            if budget is None:
                message = "provider budget disappeared during reservation"
                raise RuntimeError(message)
            if budget.used_attempts >= daily_limit:
                return None
            not_before = now
            if budget.last_not_before is not None:
                not_before = max(now, budget.last_not_before + minimum_interval)
            budget.used_attempts += 1
            budget.last_not_before = not_before
            budget.updated_at = now
            attempt_id = uuid4()
            session.add(
                ProviderAttemptRow(
                    id=attempt_id,
                    complete_import_run_id=run_id,
                    provider=provider.value,
                    budget_date=budget_date,
                    account_identity=account_identity,
                    query_hash=query_hash,
                    not_before=not_before,
                    status="reserved",
                    error_code=None,
                    reserved_at=now,
                    completed_at=None,
                ),
            )
            return ProviderReservation(attempt_id=attempt_id, not_before=not_before)

    async def complete_provider_attempt(
        self,
        attempt_id: UUID,
        *,
        status: str,
        error_code: str | None,
        completed_at: datetime,
    ) -> None:
        """Complete only a still-reserved non-sensitive attempt ledger row."""
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(ProviderAttemptRow)
                .where(
                    ProviderAttemptRow.id == attempt_id,
                    ProviderAttemptRow.status == "reserved",
                )
                .values(status=status, error_code=error_code, completed_at=completed_at),
            )

    async def resolve_source_channel_id(self, channel: SourceIdentity) -> UUID | None:
        """Return the durable channel id when the source has been persisted."""
        async with self._session_factory() as session:
            return await self._channel_id(session, channel)

    async def recurring_geocode_run_id(
        self,
        *,
        source_channel_id: UUID,
        pipeline_version: str,
        now: datetime,
    ) -> UUID:
        """Ensure one sentinel import run exists for recurring provider attempts."""
        async with self._session_factory() as session, session.begin():
            run_id = uuid4()
            inserted = await session.scalar(
                insert(CompleteImportRunRow)
                .values(
                    id=run_id,
                    source_channel_id=source_channel_id,
                    source_checksum=RECURRING_GEOCODE_SOURCE_CHECKSUM,
                    source_size=0,
                    pipeline_version=pipeline_version,
                    status=CompleteImportStatus.RUNNING.value,
                    stage=CompleteImportStage.GEOCODE.value,
                    owner_id=_RECURRING_GEOCODE_OWNER,
                    fencing_token=1,
                    lease_expires_at=now + _RECURRING_GEOCODE_LEASE,
                    checkpoint_json={},
                    counts_json={},
                    pause_reason=None,
                    next_eligible_at=None,
                    started_at=now,
                    updated_at=now,
                    finished_at=None,
                )
                .on_conflict_do_nothing(
                    constraint="uq_complete_import_runs_identity",
                )
                .returning(CompleteImportRunRow.id),
            )
            if inserted is not None:
                return inserted
            existing = await session.scalar(
                select(CompleteImportRunRow.id).where(
                    CompleteImportRunRow.source_channel_id == source_channel_id,
                    CompleteImportRunRow.source_checksum == RECURRING_GEOCODE_SOURCE_CHECKSUM,
                    CompleteImportRunRow.pipeline_version == pipeline_version,
                ),
            )
            if existing is None:
                message = "recurring geocode run disappeared during ensure"
                raise RuntimeError(message)
            return existing

    async def pending_locations(self) -> Sequence[LocationWorkItem]:
        """Return locations that still need provider resolution.

        Includes never-selected ungeocoded rows plus provider-error / out-of-scope
        selections whose negative or wrong-scope cache is expired or whose
        normalizer/request version no longer matches the live worker.
        """
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            selected = select(LocationGeocodeSelectionRow.id).where(
                LocationGeocodeSelectionRow.location_id == LocationRow.id,
            )
            latest = (
                select(
                    LocationGeocodeSelectionRow.location_id.label("location_id"),
                    LocationGeocodeSelectionRow.reason_code.label("reason_code"),
                    LocationGeocodeSelectionRow.geocode_result_id.label("geocode_result_id"),
                    func.row_number()
                    .over(
                        partition_by=LocationGeocodeSelectionRow.location_id,
                        order_by=LocationGeocodeSelectionRow.selection_version.desc(),
                    )
                    .label("rn"),
                )
            ).subquery()
            retryable = (
                select(latest.c.location_id)
                .outerjoin(GeocodeResultRow, GeocodeResultRow.id == latest.c.geocode_result_id)
                .where(
                    latest.c.rn == 1,
                    latest.c.reason_code.in_(
                        (
                            SelectionReason.PROVIDER_ERROR.value,
                            SelectionReason.OUT_OF_SCOPE.value,
                        ),
                    ),
                    (GeocodeResultRow.expires_at.is_(None))
                    | (GeocodeResultRow.expires_at <= now)
                    | (GeocodeResultRow.normalizer_version != NORMALIZER_VERSION)
                    | (GeocodeResultRow.request_version != REQUEST_VERSION),
                )
            )
            rows = await session.execute(
                select(LocationRow.id, LocationRow.display_address, LocationRow.district)
                .where(
                    LocationRow.review_status.in_(("ungeocoded", "needs_review")),
                    LocationRow.normalized_address_hash != normalized_location_key(None),
                    (~selected.exists()) | LocationRow.id.in_(retryable),
                )
                .order_by(LocationRow.normalized_address_hash),
            )
            return tuple(LocationWorkItem(*row) for row in rows)

    async def source_anchors(
        self,
        channel: SourceIdentity,
    ) -> Mapping[int, SourceAnchor]:
        """Resolve current source/revision and primary offer identities in one snapshot."""
        async with self._session_factory() as session:
            channel_id = await self._channel_id(session, channel)
            if channel_id is None:
                return {}
            rows = await session.execute(
                select(
                    SourceMessageRow.external_message_id,
                    SourceMessageRow.id,
                    SourceMessageRow.current_revision_id,
                    OfferSourceRow.offer_id,
                )
                .outerjoin(
                    OfferSourceRow,
                    (OfferSourceRow.source_message_id == SourceMessageRow.id)
                    & (OfferSourceRow.relationship == "primary"),
                )
                .where(SourceMessageRow.source_channel_id == channel_id),
            )
            return {
                int(external_id): SourceAnchor(message_id, revision_id, offer_id)
                for external_id, message_id, revision_id, offer_id in rows
            }

    async def existing_media_replays(
        self,
        channel: SourceIdentity,
    ) -> set[tuple[UUID, int, UUID, str, str]]:
        """Return exact replay keys so unchanged media bytes are never reopened."""
        async with self._session_factory() as session:
            channel_id = await self._channel_id(session, channel)
            if channel_id is None:
                return set()
            rows = await session.execute(
                select(
                    MediaDispositionAttemptRow.source_message_id,
                    MediaDispositionAttemptRow.source_ordinal,
                    MediaDispositionAttemptRow.source_message_revision_id,
                    MediaDispositionAttemptRow.source_descriptor_identity,
                    MediaDispositionAttemptRow.association_version,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == MediaDispositionAttemptRow.source_message_id,
                )
                .where(SourceMessageRow.source_channel_id == channel_id),
            )
            return {tuple(row) for row in rows}

    async def verify(self, channel: SourceIdentity, run_id: UUID) -> ImportVerification:
        """Return aggregate restricted-safe reconciliation for the selected source channel."""
        async with self._session_factory() as session:
            channel_id = await self._channel_id(session, channel)
            if channel_id is None:
                return ImportVerification(0, 0, 0, 0, 0, 0, 0, 0, 0)
            source_filter = SourceMessageRow.source_channel_id == channel_id
            source_messages = int(
                await session.scalar(
                    select(func.count()).select_from(SourceMessageRow).where(source_filter),
                )
                or 0
            )
            source_revisions = int(
                await session.scalar(
                    select(func.count())
                    .select_from(SourceMessageRevisionRow)
                    .join(
                        SourceMessageRow,
                        SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                    )
                    .where(source_filter),
                )
                or 0
            )
            offers = int(
                await session.scalar(
                    select(func.count(func.distinct(OfferSourceRow.offer_id)))
                    .select_from(OfferSourceRow)
                    .join(SourceMessageRow, SourceMessageRow.id == OfferSourceRow.source_message_id)
                    .where(source_filter),
                )
                or 0
            )
            locations = int(
                await session.scalar(select(func.count()).select_from(LocationRow)) or 0,
            )
            accepted = int(
                await session.scalar(
                    select(func.count())
                    .select_from(LocationRow)
                    .where(LocationRow.review_status == "accepted"),
                )
                or 0
            )
            media_assets = int(
                await session.scalar(select(func.count()).select_from(MediaAssetRow)) or 0,
            )
            derivatives = int(
                await session.scalar(select(func.count()).select_from(MediaDerivativeRow)) or 0
            )
            dispositions = int(
                await session.scalar(
                    select(func.count()).select_from(MediaDispositionAttemptRow),
                )
                or 0
            )
            attempts = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ProviderAttemptRow)
                    .where(
                        ProviderAttemptRow.complete_import_run_id == run_id,
                    ),
                )
                or 0
            )
            return ImportVerification(
                source_messages,
                source_revisions,
                offers,
                locations,
                accepted,
                media_assets,
                derivatives,
                dispositions,
                attempts,
            )

    @staticmethod
    async def _channel_id(session: AsyncSession, channel: SourceIdentity) -> UUID | None:
        return cast(
            "UUID | None",
            await session.scalar(
                select(SourceChannelRow.id).where(
                    SourceChannelRow.platform == channel.platform.value,
                    SourceChannelRow.external_id == channel.channel_id,
                ),
            ),
        )

    @staticmethod
    def _lease(row: CompleteImportRunRow) -> RunLease:
        return RunLease(
            run_id=row.id,
            owner_id=row.owner_id,
            fencing_token=row.fencing_token,
            stage=CompleteImportStage(row.stage),
            status=CompleteImportStatus(row.status),
            lease_expires_at=row.lease_expires_at,
        )


__all__ = [
    "RECURRING_GEOCODE_SOURCE_CHECKSUM",
    "CompleteImportLeaseHeldError",
    "ImportVerification",
    "LocationWorkItem",
    "SQLAlchemyCompleteImportRepository",
    "SourceAnchor",
    "StaleCompleteImportLeaseError",
]
