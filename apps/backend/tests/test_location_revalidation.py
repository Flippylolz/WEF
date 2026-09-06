"""Recovery orchestration defers failures without inventing accepted results."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from tests.test_geocoding import _result
from wef_backend.features.ingestion.application.complete_import import (
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.application.geocoding import CachedGeocode, GeocodeResolution
from wef_backend.features.ingestion.application.location_revalidation import (
    LimitedGeocoder,
    RevalidateLocations,
    ValidationClaim,
)
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    GeocodeProvider,
    normalize_geocode_query,
    review_geocode_result,
)

if TYPE_CHECKING:
    from datetime import datetime

    from wef_backend.features.ingestion.domain.geocoding import (
        GeocodeResult,
        NormalizedGeocodeQuery,
    )


def _resolution() -> GeocodeResolution:
    result = _result()
    return GeocodeResolution(
        CachedGeocode(uuid4(), result, None),
        review_geocode_result(result, query=normalize_geocode_query("ul. Marszałkowska 1")),
        cache_hit=True,
    )


@dataclass
class _Store:
    claims: list[ValidationClaim] = field(
        default_factory=lambda: [
            ValidationClaim(
                uuid4(), uuid4(), "fingerprint", "ul. Marszałkowska 1", None, 1, 1, "observe", 0
            )
        ]
    )
    deferrals: list[dict[str, object]] = field(default_factory=list)
    finishes: int = 0
    renewals: int = 0
    owned: bool = True

    async def discover(self, *, target: str, now: datetime) -> int:
        del target, now
        return 1

    async def claim(self, *, target: str, now: datetime) -> ValidationClaim | None:
        del target, now
        return self.claims.pop(0) if self.claims else None

    async def finish(
        self, claim: ValidationClaim, result: GeocodeResolution, *, now: datetime
    ) -> str:
        del claim, result, now
        self.finishes += 1
        return "validated"

    async def renew(self, claim: ValidationClaim, *, now: datetime) -> bool:
        del claim, now
        self.renewals += 1
        return self.owned

    async def defer(
        self,
        claim: ValidationClaim,
        *,
        reason: str,
        next_attempt: datetime,
        failure: bool,
        now: datetime,
    ) -> None:
        del claim
        self.deferrals.append(
            {"reason": reason, "delay": (next_attempt - now).total_seconds(), "failure": failure}
        )


@dataclass
class _Resolver:
    error: Exception | None = None
    delay: float = 0

    async def __call__(
        self, *, source_query: str, district: str | None = None
    ) -> GeocodeResolution:
        del source_query, district
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return _resolution()


@pytest.mark.parametrize(
    ("error", "reason", "failure"),
    [
        (ProviderDailyBudgetError(), "quota", False),
        (ProviderBatchLimitError(), "cycle_budget", False),
        (ProviderPauseError(), "transient", True),
        (TimeoutError(), "transient", True),
        (RuntimeError("private provider payload"), "transient", True),
    ],
)
async def test_failure_classes_defer_without_applying(
    error: Exception, reason: str, *, failure: bool
) -> None:
    store = _Store()
    counts = await RevalidateLocations(store, _Resolver(error)).run()
    assert counts["deferred"] == 1
    assert store.finishes == 0
    assert store.deferrals[0]["reason"] == reason
    assert store.deferrals[0]["failure"] is failure
    assert "private" not in str(store.deferrals)


async def test_zero_limit_discovers_without_claiming_or_resolving() -> None:
    store = _Store()
    assert (await RevalidateLocations(store, _Resolver()).run(limit=0))["processed"] == 0
    assert len(store.claims) == 1


async def test_long_resolution_renews_lease_and_lost_lease_cancels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.location_revalidation.RESOLUTION_POLL_SECONDS",
        0.001,
    )
    store = _Store()
    result = await RevalidateLocations(store, _Resolver(delay=0.02)).run()
    assert result["processed"] == 1
    assert store.renewals > 0
    lost = _Store(owned=False)
    result = await RevalidateLocations(lost, _Resolver(delay=5)).run()
    assert result["deferred"] == 1
    assert lost.finishes == 0


async def test_queue_shares_count_each_actual_request_before_delegation() -> None:
    class Provider:
        provider = GeocodeProvider.FIXTURE
        calls = 0

        async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
            del query
            self.calls += 1
            return _result()

    provider = Provider()
    queue = LimitedGeocoder(provider, 1)
    assert queue.provider is GeocodeProvider.FIXTURE
    await queue.geocode(normalize_geocode_query("ul. Testowa"))
    with pytest.raises(ProviderBatchLimitError):
        await queue.geocode(normalize_geocode_query("ul. Testowa"))
    assert provider.calls == 1


async def test_error_result_from_unwrapped_provider_cannot_erase_a_location() -> None:
    class ErrorResolver:
        async def __call__(
            self, *, source_query: str, district: str | None = None
        ) -> GeocodeResolution:
            del source_query, district
            result = _result(lon=None, lat=None, error=GeocodeErrorCode.TRANSIENT)
            return GeocodeResolution(
                CachedGeocode(uuid4(), result, None), review_geocode_result(result), cache_hit=False
            )

    store = _Store()
    assert (await RevalidateLocations(store, ErrorResolver()).run())["deferred"] == 1
    assert store.finishes == 0
