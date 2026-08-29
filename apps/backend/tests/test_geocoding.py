"""Provider-neutral geocoding, cache orchestration, and adapter tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from wef_backend.features.ingestion.application.geocoding import (
    CachedGeocode,
    CacheWaitExpiredError,
    ClaimDisposition,
    MissClaim,
    ResolveGeocode,
)
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    GeocodeReviewStatus,
    SelectionReason,
    canonical_warsaw_district,
    district_match_values,
    looks_like_warsaw_address,
    normalize_geocode_query,
    review_geocode_result,
    warsaw_district_in,
    within_warsaw,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import (
    FixtureGeocoder,
    HostedGeocoder,
    ProviderPolicy,
    ProviderTransportError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from wef_backend.features.ingestion.domain.geocoding import (
        NormalizedGeocodeQuery,
        ReviewDecision,
    )

NOW = datetime(2026, 8, 15, 6, 30, tzinfo=UTC)


def _result(
    *,
    provider: GeocodeProvider = GeocodeProvider.FIXTURE,
    lon: str | None = "21.0122",
    lat: str | None = "52.2297",
    precision: GeocodePrecision = GeocodePrecision.BUILDING,
    confidence: str = "0.95",
    error: GeocodeErrorCode | None = None,
) -> GeocodeResult:
    """Build one sanitized neutral result."""
    return GeocodeResult(
        provider=provider,
        provider_result_id="place-1" if error is None else None,
        longitude=Decimal(lon) if lon is not None else None,
        latitude=Decimal(lat) if lat is not None else None,
        display_name="ul. Marszałkowska 1, Warszawa" if error is None else None,
        precision=precision,
        confidence=Decimal(confidence),
        within_scope=True if lon is not None else None,
        attribution_text="Synthetic fixture",
        error_code=error,
        diagnostic=(("result_type", precision.value),) if error is None else (),
    )


def test_normalization_is_versioned_deterministic_and_preserves_source() -> None:
    """Polish/Cyrillic forms normalize without inventing a replacement display value."""
    first = normalize_geocode_query("  улица  Marszałkowska  1, Варшава ", "Śródmieście")
    second = normalize_geocode_query("улица Marszałkowska 1, Варшава", "Śródmieście")
    assert first.original.startswith("  ")
    assert first.normalized == second.normalized
    assert first.normalized == "ul. marszałkowska 1, warszawa, śródmieście, pl"
    assert canonical_warsaw_district("Mokotow") == "Mokotów"
    assert canonical_warsaw_district("not-a-district") is None
    with pytest.raises(ValueError, match="non-empty"):
        normalize_geocode_query("  ")


def test_template_address_screen_accepts_only_warsaw_evidence() -> None:
    """Pin-line screening accepts street/city/district lines and rejects prose."""
    assert looks_like_warsaw_address("Варшава, Wola, ul. Stańczyka")
    assert looks_like_warsaw_address("ul. Chmielna, Śródmieście, Warszawa")
    assert looks_like_warsaw_address("Wola | ul. Prosta 69")
    assert looks_like_warsaw_address("Урсус | ул. Herbu Oksza")  # noqa: RUF001
    assert looks_like_warsaw_address("Район Targówek | ul. Miedza")
    assert looks_like_warsaw_address("Nowodwory, Białołęka, Warszawa")
    assert looks_like_warsaw_address("Mokotów, Варшава")
    assert not looks_like_warsaw_address("Dosin, гмина Serock, Мазовецкое воеводство")
    assert not looks_like_warsaw_address("Локация:")
    assert not looks_like_warsaw_address("Идеальная локация — тихо и уютно")
    assert not looks_like_warsaw_address(
        "Локация — 10-15 минут до метро Wilanowska, 10 минут до Westifield Mokotów.",
    )
    assert warsaw_district_in("Варшава, Białołęka, ul. Geodezyjna") == "Białołęka"
    assert warsaw_district_in("Warszawa, Mokotów (Służewiec) | ul. Domaniewska 47A") == "Mokotów"
    assert warsaw_district_in("Район Targówek | ul. Miedza") == "Targówek"
    assert warsaw_district_in("ul. Chmielna, Warszawa") is None

    assert canonical_warsaw_district("Bia\u0142O\u0142\u0119Cka") == "Bia\u0142o\u0142\u0119ka"
    assert canonical_warsaw_district("Praga Po\u0142Udnie") == "Praga-Po\u0142udnie"
    assert canonical_warsaw_district("PRAGA P\u00d3LNOC") == "Praga-P\u00f3\u0142noc"
    assert canonical_warsaw_district("Mordor") is None
    assert district_match_values("wola") == ("Wola", "wola")
    assert district_match_values("Bia\u0142O\u0142\u0119Ka") == (
        "Bia\u0142o\u0142\u0119ka",
        "bialolecka",
        "bialoleka",
        "bia\u0142o\u0142\u0119cka",
        "bia\u0142o\u0142\u0119ka",
    )
    assert district_match_values("Mordor") == ("Mordor",)


def test_cache_identity_covers_provider_and_every_version() -> None:
    """Any behavior-changing cache input yields a distinct identity."""
    base = GeocodeCacheKey(GeocodeProvider.FIXTURE, "query")
    hashes = {
        base.query_hash,
        GeocodeCacheKey(GeocodeProvider.GEOAPIFY, "query").query_hash,
        GeocodeCacheKey(GeocodeProvider.FIXTURE, "query", normalizer_version="v2").query_hash,
        GeocodeCacheKey(GeocodeProvider.FIXTURE, "query", scope_version="v2").query_hash,
        GeocodeCacheKey(GeocodeProvider.FIXTURE, "query", request_version="v2").query_hash,
        GeocodeCacheKey(GeocodeProvider.FIXTURE, "other").query_hash,
    }
    assert len(hashes) == 6


@pytest.mark.parametrize(
    ("result", "status", "reason", "selected", "out_of_scope"),
    [
        (
            _result(),
            GeocodeReviewStatus.ACCEPTED,
            SelectionReason.AUTO_PRECISE_IN_SCOPE,
            True,
            False,
        ),
        (
            _result(confidence="0.50"),
            GeocodeReviewStatus.NEEDS_REVIEW,
            SelectionReason.LOW_CONFIDENCE,
            False,
            False,
        ),
        (
            _result(precision=GeocodePrecision.DISTRICT),
            GeocodeReviewStatus.NEEDS_REVIEW,
            SelectionReason.LOW_PRECISION,
            False,
            False,
        ),
        (
            _result(lon="19.0", lat="52.0"),
            GeocodeReviewStatus.NEEDS_REVIEW,
            SelectionReason.OUT_OF_SCOPE,
            False,
            True,
        ),
        (
            _result(lon=None, lat=None, confidence="0", error=GeocodeErrorCode.NO_RESULT),
            GeocodeReviewStatus.UNGEOCODED,
            SelectionReason.PROVIDER_ERROR,
            False,
            False,
        ),
    ],
)
def test_review_policy_fails_closed(
    result: GeocodeResult,
    status: GeocodeReviewStatus,
    reason: SelectionReason,
    selected: bool,  # noqa: FBT001
    out_of_scope: bool,  # noqa: FBT001
) -> None:
    """Only precise, confident, in-scope points auto-select."""
    decision = review_geocode_result(result)
    assert (decision.status, decision.reason) == (status, reason)
    assert decision.select_result is selected
    assert decision.out_of_scope is out_of_scope
    assert within_warsaw(Decimal(21), Decimal("52.2"))
    assert not within_warsaw(Decimal(21), Decimal(60))


def test_result_invariants_and_diagnostic_redaction() -> None:
    """Invalid coordinate/confidence/error and secret diagnostic shapes are rejected."""
    with pytest.raises(ValueError, match="between"):
        _result(confidence="1.1")
    with pytest.raises(ValueError, match="both"):
        _result(lat=None)
    with pytest.raises(ValueError, match="cannot carry"):
        _result(error=GeocodeErrorCode.TIMEOUT)
    with pytest.raises(ValueError, match="secret"):
        GeocodeResult(
            provider=GeocodeProvider.FIXTURE,
            provider_result_id=None,
            longitude=None,
            latitude=None,
            display_name=None,
            precision=GeocodePrecision.UNKNOWN,
            confidence=Decimal(0),
            within_scope=None,
            attribution_text="fixture",
            error_code=GeocodeErrorCode.NO_RESULT,
            diagnostic=(("authorization", "secret"),),
        )


@dataclass
class FakeStore:
    """In-memory cache with scriptable ownership for application tests."""

    cached: CachedGeocode | None = None
    claims: list[ClaimDisposition] = field(default_factory=lambda: [ClaimDisposition.OWNER])
    claim_calls: int = 0
    completions: int = 0
    abandonments: int = 0
    selections: list[tuple[UUID, ReviewDecision]] = field(default_factory=list)

    async def get_cached(self, _: GeocodeCacheKey) -> CachedGeocode | None:
        """Return the scripted cache value."""
        return self.cached

    async def claim_miss(
        self,
        _: GeocodeCacheKey,
        *,
        owner_id: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> MissClaim:
        """Return the next scripted ownership state."""
        del now
        disposition = self.claims[min(self.claim_calls, len(self.claims) - 1)]
        self.claim_calls += 1
        return MissClaim(
            disposition,
            owner_id if disposition is ClaimDisposition.OWNER else "other",
            1,
            lease_expires_at,
        )

    async def complete_miss(
        self,
        _: GeocodeCacheKey,
        *,
        claim: MissClaim,
        query: NormalizedGeocodeQuery,
        result: GeocodeResult,
        attempted_at: datetime,
        expires_at: datetime | None,
    ) -> CachedGeocode:
        """Persist one in-memory completed result."""
        del claim, query, attempted_at
        self.completions += 1
        self.cached = CachedGeocode(uuid4(), result, expires_at)
        return self.cached

    async def abandon_miss(
        self,
        _: GeocodeCacheKey,
        *,
        claim: MissClaim,
        now: datetime,
    ) -> None:
        """Record release of an incomplete owned miss."""
        del claim, now
        self.abandonments += 1

    async def select_for_location(
        self,
        *,
        location_id: UUID,
        cached: CachedGeocode,
        decision: ReviewDecision,
        actor_type: str,
        actor_id: str | None,
    ) -> None:
        """Record one in-memory selection."""
        del cached, actor_type, actor_id
        self.selections.append((location_id, decision))


async def test_resolution_uses_cache_without_provider_call_and_selects() -> None:
    """A live cache entry skips provider I/O and applies the same review policy."""
    cached = CachedGeocode(uuid4(), _result(), None)
    store = FakeStore(cached=cached)
    geocoder = FixtureGeocoder({})
    location_id = uuid4()
    resolution = await ResolveGeocode(store, geocoder, clock=lambda: NOW)(
        source_query="Marszałkowska 1",
        location_id=location_id,
    )
    assert resolution.cache_hit
    assert store.claim_calls == store.completions == 0
    assert store.selections[0][0] == location_id


async def test_resolution_owns_miss_persists_once_and_negative_cache_expires() -> None:
    """Owned calls happen outside the store and persist bounded negative semantics."""
    query = normalize_geocode_query("Unknown place")
    store = FakeStore()
    resolution = await ResolveGeocode(store, FixtureGeocoder({}), clock=lambda: NOW)(
        source_query=query.original,
    )
    assert not resolution.cache_hit
    assert resolution.cached.result.error_code is GeocodeErrorCode.NO_RESULT
    assert resolution.cached.expires_at == NOW + timedelta(hours=24)
    assert store.completions == 1


async def test_resolution_waits_for_owner_or_fails_within_bound() -> None:
    """Non-owners recheck durably and stop after a configured bound."""
    completed = CachedGeocode(uuid4(), _result(), None)
    store = FakeStore(claims=[ClaimDisposition.WAIT])

    async def finish() -> None:
        store.cached = completed

    resolution = await ResolveGeocode(store, FixtureGeocoder({}), clock=lambda: NOW, wait=finish)(
        source_query="Marszałkowska 1",
    )
    assert resolution.cache_hit
    blocked = FakeStore(claims=[ClaimDisposition.WAIT])
    with pytest.raises(CacheWaitExpiredError):
        await ResolveGeocode(
            blocked,
            FixtureGeocoder({}),
            clock=lambda: NOW,
            wait_attempts=2,
        )(source_query="Marszałkowska 1")


async def test_resolution_abandons_owned_miss_when_provider_pauses() -> None:
    """A provider exception releases cache ownership for immediate resume."""

    class PausingGeocoder:
        @property
        def provider(self) -> GeocodeProvider:
            return GeocodeProvider.FIXTURE

        async def geocode(self, _: NormalizedGeocodeQuery) -> GeocodeResult:
            message = "pause"
            raise RuntimeError(message)

    store = FakeStore()
    with pytest.raises(RuntimeError, match="pause"):
        await ResolveGeocode(store, PausingGeocoder(), clock=lambda: NOW)(
            source_query="Marszałkowska 1"
        )
    assert store.abandonments == 1
    assert store.completions == 0


@dataclass
class FakeTransport:
    """Scripted decoded provider transport."""

    payloads: list[object]
    calls: list[tuple[str, Mapping[str, str], Mapping[str, str], float]] = field(
        default_factory=list
    )

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> object:
        """Return or raise the next scripted transport payload."""
        self.calls.append((url, params, headers, timeout_seconds))
        payload = self.payloads.pop(0)
        if isinstance(payload, BaseException):
            raise payload
        return payload


def _policy(*, quota: int = 10, retries: int = 0) -> ProviderPolicy:
    return ProviderPolicy(
        requests_per_second=Decimal(100000),
        quota=quota,
        retries=retries,
        timeout_seconds=2.5,
        identifying_user_agent="WEF acceptance contact@example.invalid",
    )


async def test_hosted_adapters_map_sanitized_provider_shapes_without_fanout() -> None:
    """Geoapify and LocationIQ map through one neutral result shape."""
    geoapify_transport = FakeTransport(
        [
            {
                "features": [
                    {
                        "geometry": {"coordinates": [21.01, 52.23]},
                        "properties": {
                            "place_id": "g1",
                            "formatted": "Warsaw",
                            "result_type": "building",
                            "rank": {"confidence": 0.9},
                        },
                    }
                ]
            }
        ],
    )
    geoapify = HostedGeocoder(
        GeocodeProvider.GEOAPIFY,
        geoapify_transport,
        _policy(),
        api_key="not-logged",
    )
    mapped = await geoapify.geocode(normalize_geocode_query("Marszałkowska 1"))
    assert mapped.precision is GeocodePrecision.BUILDING
    assert mapped.within_scope is True
    assert geoapify_transport.calls[0][1]["apiKey"] == "not-logged"
    assert dict(mapped.diagnostic) == {"result_type": "building"}

    locationiq_transport = FakeTransport(
        [
            [
                {
                    "place_id": 7,
                    "lon": "21.02",
                    "lat": "52.20",
                    "display_name": "Warsaw",
                    "type": "road",
                    "importance": 0.85,
                }
            ]
        ],
    )
    locationiq = HostedGeocoder(
        GeocodeProvider.LOCATIONIQ,
        locationiq_transport,
        _policy(),
        api_key="not-logged",
    )
    mapped = await locationiq.geocode(normalize_geocode_query("Puławska"))
    assert mapped.precision is GeocodePrecision.STREET
    assert mapped.confidence == Decimal("0.85")
    assert len(locationiq_transport.calls) == 1


async def test_hosted_adapter_bounds_retry_quota_and_invalid_responses() -> None:
    """Transient, quota, no-result, and malformed outcomes stay bounded/redacted."""
    transport = FakeTransport([ProviderTransportError("secret URL"), []])
    adapter = HostedGeocoder(
        GeocodeProvider.LOCATIONIQ,
        transport,
        _policy(quota=2, retries=1),
        api_key="secret-key",
    )
    result = await adapter.geocode(normalize_geocode_query("unknown"))
    assert result.error_code is GeocodeErrorCode.NO_RESULT
    assert len(transport.calls) == 2
    quota = await adapter.geocode(normalize_geocode_query("another"))
    assert quota.error_code is GeocodeErrorCode.QUOTA

    malformed = HostedGeocoder(
        GeocodeProvider.GEOAPIFY,
        FakeTransport([{"features": [{"geometry": {}, "properties": {}}]}]),
        _policy(),
        api_key="secret-key",
    )
    assert (
        await malformed.geocode(normalize_geocode_query("x"))
    ).error_code is GeocodeErrorCode.INVALID_RESPONSE


def test_provider_configuration_enforces_identification_keys_and_nominatim_policy() -> None:
    """Misconfigured providers fail before any network call."""
    with pytest.raises(ValueError, match="API key"):
        HostedGeocoder(GeocodeProvider.GEOAPIFY, FakeTransport([]), _policy())
    with pytest.raises(ValueError, match="one-time"):
        HostedGeocoder(
            GeocodeProvider.NOMINATIM,
            FakeTransport([]),
            ProviderPolicy(Decimal(2), 101, 0, 2, "WEF contact@example.invalid"),
        )
    with pytest.raises(ValueError, match="hosted provider"):
        HostedGeocoder(GeocodeProvider.FIXTURE, FakeTransport([]), _policy())
    with pytest.raises(ValueError, match="identification"):
        ProviderPolicy(Decimal(1), 1, 0, 2, "")
