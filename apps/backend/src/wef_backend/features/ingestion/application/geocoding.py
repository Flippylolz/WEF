"""Cache-owned geocoding orchestration and review contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from wef_backend.features.ingestion.domain.geocoding import (
    REQUEST_VERSION,
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodeProvider,
    GeocodeResult,
    NormalizedGeocodeQuery,
    ReviewDecision,
    SelectionReason,
    normalize_geocode_query,
    review_geocode_result,
)

if TYPE_CHECKING:
    from uuid import UUID

_DEFAULT_LEASE = timedelta(seconds=30)
_DEFAULT_WAIT_ATTEMPTS = 6


class ClaimDisposition(StrEnum):
    """Atomic cache-miss ownership result."""

    OWNER = "owner"
    WAIT = "wait"


@dataclass(frozen=True, slots=True)
class MissClaim:
    """Owner/fencing state returned by the durable cache."""

    disposition: ClaimDisposition
    owner_id: str
    fencing_token: int
    lease_expires_at: datetime


@dataclass(frozen=True, slots=True)
class CachedGeocode:
    """One durable result and its database identity."""

    result_id: UUID
    result: GeocodeResult
    expires_at: datetime | None

    def usable_at(self, now: datetime) -> bool:
        """Return whether success/no-result/error cache semantics remain live."""
        return self.expires_at is None or self.expires_at > now


@dataclass(frozen=True, slots=True)
class GeocodeResolution:
    """Resolved cache value and the policy decision applied to it."""

    cached: CachedGeocode
    decision: ReviewDecision
    cache_hit: bool


class CacheWaitExpiredError(RuntimeError):
    """A non-owner could not observe completion within the configured bound."""


class GeocoderPort(Protocol):
    """Provider adapter returning only sanitized neutral results."""

    @property
    def provider(self) -> GeocodeProvider:
        """Return the provider identity used in the complete cache key."""
        ...

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Resolve one query under provider-specific policy."""
        ...


class GeocodeStorePort(Protocol):
    """Durable cache, miss ownership, and review-selection operations."""

    async def get_cached(self, key: GeocodeCacheKey) -> CachedGeocode | None:
        """Return the unique durable cache row when present."""
        ...

    async def claim_miss(
        self,
        key: GeocodeCacheKey,
        *,
        owner_id: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> MissClaim:
        """Acquire, wait for, or fence-take over one identical miss."""
        ...

    async def complete_miss(  # noqa: PLR0913
        self,
        key: GeocodeCacheKey,
        *,
        claim: MissClaim,
        query: NormalizedGeocodeQuery,
        result: GeocodeResult,
        attempted_at: datetime,
        expires_at: datetime | None,
    ) -> CachedGeocode:
        """Reconcile one possibly ambiguous provider result durably."""
        ...

    async def abandon_miss(
        self,
        key: GeocodeCacheKey,
        *,
        claim: MissClaim,
        now: datetime,
    ) -> None:
        """Release a still-owned incomplete miss after provider failure or pause."""
        ...

    async def select_for_location(
        self,
        *,
        location_id: UUID,
        cached: CachedGeocode,
        decision: ReviewDecision,
        actor_type: str,
        actor_id: str | None,
    ) -> None:
        """Append lineage and atomically update the location projection."""
        ...


Clock = Callable[[], datetime]
Wait = Callable[[], Awaitable[None]]


async def _no_wait() -> None:
    """Default cooperative wait used outside a polling UI."""


@dataclass(frozen=True, slots=True)
class ResolveGeocode:
    """Use a durable cache and fenced miss ownership around provider I/O."""

    store: GeocodeStorePort
    geocoder: GeocoderPort
    clock: Clock = lambda: datetime.now(UTC)
    wait: Wait = _no_wait
    lease_duration: timedelta = _DEFAULT_LEASE
    wait_attempts: int = _DEFAULT_WAIT_ATTEMPTS
    request_version: str = REQUEST_VERSION
    fallback_forms: bool = True

    async def __call__(
        self,
        *,
        source_query: str,
        district: str | None = None,
        location_id: UUID | None = None,
    ) -> GeocodeResolution:
        """Resolve from cache or one owned provider call, then apply review."""
        query = normalize_geocode_query(source_query, district)
        resolution = await self._resolve(query)
        fallback = _fallback_query(query)
        if (
            self.fallback_forms
            and not resolution.decision.select_result
            and resolution.cached.result.error_code in {None, GeocodeErrorCode.NO_RESULT}
            and resolution.decision.reason is not SelectionReason.AMBIGUOUS_CANDIDATES
            and fallback is not None
        ):
            resolution = await self._resolve(fallback)
        if location_id is not None:
            await self.store.select_for_location(
                location_id=location_id,
                cached=resolution.cached,
                decision=resolution.decision,
                actor_type="automatic_policy",
                actor_id=None,
            )
        return resolution

    async def _resolve(self, query: NormalizedGeocodeQuery) -> GeocodeResolution:
        """Resolve one form through the durable cache and account-budgeted port."""
        key = GeocodeCacheKey(
            provider=self.geocoder.provider,
            normalized_query=query.normalized,
            request_version=f"{self.request_version}-city"
            if query.locality_only
            else f"{self.request_version}-street"
            if query.street_only
            else self.request_version,
        )
        now = self.clock()
        cached = await self.store.get_cached(key)
        if cached is not None and cached.usable_at(now):
            return await self._review(cached, query=query, cache_hit=True)

        owner_id = str(uuid4())
        claim = await self.store.claim_miss(
            key,
            owner_id=owner_id,
            now=now,
            lease_expires_at=now + self.lease_duration,
        )
        for _ in range(self.wait_attempts):
            if claim.disposition is ClaimDisposition.OWNER:
                break
            await self.wait()
            now = self.clock()
            cached = await self.store.get_cached(key)
            if cached is not None and cached.usable_at(now):
                return await self._review(cached, query=query, cache_hit=True)
            claim = await self.store.claim_miss(
                key,
                owner_id=owner_id,
                now=now,
                lease_expires_at=now + self.lease_duration,
            )
        if claim.disposition is not ClaimDisposition.OWNER:
            message = "geocode cache miss remained owned beyond the wait bound"
            raise CacheWaitExpiredError(message)

        attempted_at = self.clock()
        try:
            result = await self.geocoder.geocode(query)
        except Exception:
            await self.store.abandon_miss(key, claim=claim, now=self.clock())
            raise
        expires_at = _result_expiry(result, attempted_at)
        cached = await self.store.complete_miss(
            key,
            claim=claim,
            query=query,
            result=result,
            attempted_at=attempted_at,
            expires_at=expires_at,
        )
        return await self._review(cached, query=query, cache_hit=False)

    async def _review(
        self,
        cached: CachedGeocode,
        *,
        cache_hit: bool,
        query: NormalizedGeocodeQuery,
    ) -> GeocodeResolution:
        """Apply fail-closed policy and optional atomic location selection."""
        decision = review_geocode_result(cached.result, query=query)
        return GeocodeResolution(cached=cached, decision=decision, cache_hit=cache_hit)


def _result_expiry(result: GeocodeResult, attempted_at: datetime) -> datetime | None:
    """Persist successes indefinitely and bound negative/error caching."""
    if result.error_code in {None, GeocodeErrorCode.NO_RESULT}:
        return None
    return attempted_at + timedelta(hours=24)


def _fallback_query(query: NormalizedGeocodeQuery) -> NormalizedGeocodeQuery | None:
    """Build at most one source-supported form without weakening constraints."""
    source = query.address
    if source is None or not source.street:
        return None
    street = source.street
    if source.house_number:
        street = f"{street} {source.house_number}"
    parts = [street, source.neighborhood, source.district, source.city, source.country_code]
    normalized = ", ".join(part for part in parts if part).casefold()
    street_only = not source.house_number
    if normalized == query.normalized and not street_only:
        return None
    return replace(query, normalized=normalized, street_only=street_only)
