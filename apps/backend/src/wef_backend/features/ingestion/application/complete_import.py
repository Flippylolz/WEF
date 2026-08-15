"""Staged complete-import preparation, incremental planning, and provider budgeting."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.media_grouping import GROUPING_VERSION, group_media
from wef_backend.features.ingestion.application.persistence import PersistableMessage
from wef_backend.features.ingestion.domain import GroupingInput
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodeProvider,
    GeocodeResult,
)

if TYPE_CHECKING:
    from datetime import datetime, timedelta
    from uuid import UUID

    from wef_backend.features.ingestion.application.geocoding import GeocoderPort
    from wef_backend.features.ingestion.application.source import HistoricalSourcePort, ScanSummary
    from wef_backend.features.ingestion.domain import MediaDisposition, SourceIdentity
    from wef_backend.features.ingestion.domain.geocoding import NormalizedGeocodeQuery

PIPELINE_VERSION = "e3-complete-v1"
PrepareProgress = Callable[[int], None]


class CompleteImportStage(StrEnum):
    """Resumable stages of one exact-source import."""

    PREFLIGHT = "preflight"
    PERSISTENCE = "persistence"
    GEOCODE = "geocode"
    MEDIA = "media"
    VERIFY = "verify"


class CompleteImportStatus(StrEnum):
    """Durable terminal and resumable run states."""

    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


@dataclass(frozen=True, slots=True)
class PreparedImport:
    """Fully validated source snapshot prepared before the first database write."""

    summary: ScanSummary
    messages: tuple[PersistableMessage, ...]
    media_dispositions: tuple[MediaDisposition, ...]
    candidate_count: int

    @property
    def channel(self) -> SourceIdentity:
        """Return the validated stable source identity."""
        return self.summary.source.identity


@dataclass(frozen=True, slots=True)
class IncrementalPlan:
    """Read-only exact counts for a prospective persistence run."""

    records_total: int
    messages_total: int
    candidates_total: int
    malformed_total: int
    media_total: int
    new_messages: int
    changed_messages: int
    unchanged_messages: int

    @property
    def messages_to_process(self) -> int:
        """Return the rows that can create or revise source state."""
        return self.new_messages + self.changed_messages


@dataclass(frozen=True, slots=True)
class RunLease:
    """Fenced ownership of one exact source/pipeline run."""

    run_id: UUID
    owner_id: str
    fencing_token: int
    stage: CompleteImportStage
    status: CompleteImportStatus
    lease_expires_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderReservation:
    """One durable provider attempt slot reserved before network I/O."""

    attempt_id: UUID
    not_before: datetime


class ProviderBudgetPort(Protocol):
    """Durable cross-process hosted-provider attempt budget."""

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
        """Reserve daily budget and one globally spaced call slot atomically."""
        ...

    async def complete_provider_attempt(
        self,
        attempt_id: UUID,
        *,
        status: str,
        error_code: str | None,
        completed_at: datetime,
    ) -> None:
        """Record a sanitized terminal outcome for one reservation."""
        ...


class ProviderBatchLimitError(RuntimeError):
    """The operator-local hosted request allowance is exhausted."""


class ProviderDailyBudgetError(RuntimeError):
    """The durable UTC-day hosted-provider allowance is exhausted."""


class ProviderPauseError(RuntimeError):
    """A provider response requires a clean resumable pause."""


def prepare_import(
    source: HistoricalSourcePort,
    *,
    progress: PrepareProgress | None = None,
) -> PreparedImport:
    """Validate and exhaust a source snapshot before allowing canonical writes."""
    messages: list[PersistableMessage] = []
    grouping_inputs: list[GroupingInput] = []
    candidates = 0
    scan = source.open_scan()
    with scan:
        for index, record in enumerate(scan, start=1):
            if progress is not None:
                progress(index)
            if record.message is None:
                continue
            extraction = extract_listing(record.message)
            candidates += int(extraction.decision.is_candidate)
            messages.append(PersistableMessage(raw=record.message, extraction=extraction))
            grouping_inputs.append(
                GroupingInput(message=record.message, candidate=extraction.decision),
            )
        summary = scan.summary
    return PreparedImport(
        summary=summary,
        messages=tuple(messages),
        media_dispositions=tuple(
            group_media(grouping_inputs, grouping_version=GROUPING_VERSION),
        ),
        candidate_count=candidates,
    )


def build_incremental_plan(
    prepared: PreparedImport,
    existing_checksums: Mapping[int, str],
) -> IncrementalPlan:
    """Compare stable source identities/checksums without mutating persistence."""
    new_messages = 0
    changed_messages = 0
    unchanged_messages = 0
    for item in prepared.messages:
        existing = existing_checksums.get(item.raw.external_message_id)
        if existing is None:
            new_messages += 1
        elif existing == item.raw.checksum:
            unchanged_messages += 1
        else:
            changed_messages += 1
    return IncrementalPlan(
        records_total=prepared.summary.counts.total,
        messages_total=len(prepared.messages),
        candidates_total=prepared.candidate_count,
        malformed_total=prepared.summary.counts.malformed,
        media_total=len(prepared.media_dispositions),
        new_messages=new_messages,
        changed_messages=changed_messages,
        unchanged_messages=unchanged_messages,
    )


def messages_to_process(
    prepared: PreparedImport,
    existing_checksums: Mapping[int, str],
) -> tuple[PersistableMessage, ...]:
    """Return only unseen or revised messages in deterministic source order."""
    return tuple(
        item
        for item in prepared.messages
        if existing_checksums.get(item.raw.external_message_id) != item.raw.checksum
    )


@dataclass(slots=True)
class DurableBudgetedGeocoder:
    """Reserve every hosted attempt durably before delegating network I/O."""

    geocoder: GeocoderPort
    budget: ProviderBudgetPort
    run_id: UUID
    account_identity: str
    daily_limit: int
    minimum_interval: timedelta
    max_provider_requests: int
    clock: Callable[[], datetime]
    _used: int = 0

    @property
    def provider(self) -> GeocodeProvider:
        """Expose the wrapped provider for the complete geocode cache key."""
        return self.geocoder.provider

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Reserve, globally pace, call once, and record a sanitized outcome."""
        if self._used >= self.max_provider_requests:
            raise ProviderBatchLimitError
        key = GeocodeCacheKey(self.provider, query.normalized)
        now = self.clock()
        reservation = await self.budget.reserve_provider_attempt(
            run_id=self.run_id,
            provider=self.provider,
            account_identity=self.account_identity,
            query_hash=key.query_hash,
            daily_limit=self.daily_limit,
            minimum_interval=self.minimum_interval,
            now=now,
        )
        if reservation is None:
            raise ProviderDailyBudgetError
        self._used += 1
        delay = (reservation.not_before - self.clock()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            result = await self.geocoder.geocode(query)
        except Exception:
            await self.budget.complete_provider_attempt(
                reservation.attempt_id,
                status="failed",
                error_code="provider_exception",
                completed_at=self.clock(),
            )
            raise
        status = "succeeded"
        if result.error_code is GeocodeErrorCode.NO_RESULT:
            status = "no_result"
        elif result.error_code is GeocodeErrorCode.QUOTA:
            status = "quota"
        elif result.error_code is not None:
            status = "transient"
        await self.budget.complete_provider_attempt(
            reservation.attempt_id,
            status=status,
            error_code=result.error_code.value if result.error_code is not None else None,
            completed_at=self.clock(),
        )
        if result.error_code is GeocodeErrorCode.QUOTA:
            raise ProviderDailyBudgetError
        if result.error_code not in {None, GeocodeErrorCode.NO_RESULT}:
            raise ProviderPauseError
        return result


__all__ = [
    "GROUPING_VERSION",
    "PARSER_VERSION",
    "PIPELINE_VERSION",
    "CompleteImportStage",
    "CompleteImportStatus",
    "DurableBudgetedGeocoder",
    "IncrementalPlan",
    "PreparedImport",
    "ProviderBatchLimitError",
    "ProviderDailyBudgetError",
    "ProviderPauseError",
    "ProviderReservation",
    "RunLease",
    "build_incremental_plan",
    "messages_to_process",
    "prepare_import",
]
