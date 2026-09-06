"""Bounded automatic revalidation with durable observation and guarded application."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.application.complete_import import (
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.application.geocoding import CacheWaitExpiredError
from wef_backend.features.ingestion.domain.geocoding import (
    NORMALIZER_VERSION,
    REQUEST_VERSION,
    REVIEW_POLICY_VERSION,
    GeocodeErrorCode,
    GeocodeProvider,
)

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.features.ingestion.application.geocoding import (
        GeocodeResolution,
        GeocoderPort,
    )
    from wef_backend.features.ingestion.domain.geocoding import (
        GeocodeResult,
        NormalizedGeocodeQuery,
    )

VALIDATION_TARGET = f"{NORMALIZER_VERSION}/{REQUEST_VERSION}/{REVIEW_POLICY_VERSION}"
LEASE_SECONDS = 120
RESOLUTION_POLL_SECONDS = 40.0
RETRY_MINUTES = (1, 5, 15, 60, 240)


@dataclass(frozen=True, slots=True)
class ValidationClaim:
    """Snapshot and fencing identity, detached before provider I/O."""

    work_id: UUID
    location_id: UUID
    fingerprint: str
    address: str
    district: str | None
    selection_version: int
    fence: int
    mode: str
    failures: int


class GeocodeResolver(Protocol):
    """Resolve source evidence without selecting a canonical location."""

    async def __call__(
        self, *, source_query: str, district: str | None = None
    ) -> GeocodeResolution:
        """Use current policy and cache under the shared account budget."""
        ...


class ValidationStore(Protocol):
    """Queue persistence owns short transaction and atomic receipt boundaries."""

    async def discover(self, *, target: str, now: datetime) -> int:
        """Advance a durable scan by at most 100 locations."""
        ...

    async def claim(self, *, target: str, now: datetime) -> ValidationClaim | None:
        """Lease one current item or return no eligible work."""
        ...

    async def finish(
        self, claim: ValidationClaim, result: GeocodeResolution, *, now: datetime
    ) -> str:
        """Guard source/owner versions and atomically receipt the outcome."""
        ...

    async def renew(self, claim: ValidationClaim, *, now: datetime) -> bool:
        """Renew a live fenced lease during long provider pacing or I/O."""
        ...

    async def defer(
        self,
        claim: ValidationClaim,
        *,
        reason: str,
        next_attempt: datetime,
        failure: bool,
        now: datetime,
    ) -> None:
        """Retain retries and pacing without turning quota into quality failure."""
        ...


@dataclass(frozen=True, slots=True)
class RevalidateLocations:
    """Process bounded work; unchanged completed versions require no human campaign."""

    store: ValidationStore
    resolver: GeocodeResolver
    target: str = VALIDATION_TARGET

    async def run(self, *, limit: int = 25) -> dict[str, int]:
        """Discover and resolve no more than one bounded cycle under shared quotas."""
        now = datetime.now(UTC)
        discovered = await self.store.discover(target=self.target, now=now)
        counts = {"discovered": discovered, "processed": 0, "deferred": 0}
        for _ in range(min(max(limit, 0), 25)):
            claim = await self.store.claim(target=self.target, now=datetime.now(UTC))
            if claim is None:
                break
            try:
                result = await self._resolve(claim)
            except ProviderDailyBudgetError:
                now = datetime.now(UTC)
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                await self.store.defer(
                    claim, reason="quota", next_attempt=tomorrow, failure=False, now=now
                )
                counts["deferred"] += 1
                break
            except ProviderBatchLimitError:
                now = datetime.now(UTC)
                await self.store.defer(
                    claim,
                    reason="cycle_budget",
                    next_attempt=now + timedelta(minutes=1),
                    failure=False,
                    now=now,
                )
                counts["deferred"] += 1
                break
            except Exception:  # noqa: BLE001 - redacted durable systemic retry
                now = datetime.now(UTC)
                delay = RETRY_MINUTES[min(claim.failures, len(RETRY_MINUTES) - 1)]
                await self.store.defer(
                    claim,
                    reason="transient",
                    next_attempt=now + timedelta(minutes=delay),
                    failure=True,
                    now=now,
                )
                counts["deferred"] += 1
                continue
            outcome = await self.store.finish(claim, result, now=datetime.now(UTC))
            counts["processed"] += 1
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    async def _resolve(self, claim: ValidationClaim) -> GeocodeResolution:
        """Renew ownership during bounded network work and cancel on lost fencing."""
        task = asyncio.create_task(
            self.resolver(source_query=claim.address, district=claim.district)
        )
        try:
            while True:
                try:
                    result = await asyncio.wait_for(
                        asyncio.shield(task), timeout=RESOLUTION_POLL_SECONDS
                    )
                except TimeoutError:
                    if task.done():
                        raise
                    if not await self.store.renew(claim, now=datetime.now(UTC)):
                        raise CacheWaitExpiredError from None
                else:
                    if result.cached.result.error_code not in {None, GeocodeErrorCode.NO_RESULT}:
                        raise ProviderPauseError
                    return result
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task


@dataclass(slots=True)
class LimitedGeocoder:
    """Share one durable account budget while bounding one cycle's queue share."""

    geocoder: GeocoderPort
    limit: int
    used: int = 0

    @property
    def provider(self) -> GeocodeProvider:
        """Retain the wrapped provider's cache identity."""
        return self.geocoder.provider

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Charge each fallback form to the queue share and underlying account cap."""
        if self.used >= self.limit:
            raise ProviderBatchLimitError
        self.used += 1
        return await self.geocoder.geocode(query)
