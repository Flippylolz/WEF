"""Deterministic fixture and policy-bounded hosted geocoder adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Protocol

import httpx

from wef_backend.features.ingestion.domain.geocoding import (
    WARSAW_BIAS_LAT,
    WARSAW_BIAS_LON,
    WARSAW_BOUNDS,
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    NormalizedGeocodeQuery,
    within_warsaw,
)

_MAX_RETRIES = 3
_MAX_NOMINATIM_SEED_QUOTA = 100
_COORDINATE_COUNT = 2

if TYPE_CHECKING:
    from collections.abc import Mapping


class JSONTransport(Protocol):
    """Narrow HTTP boundary that tests can replace without network access."""

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> object:
        """Return decoded JSON or raise a bounded transport exception."""
        ...


class ProviderTransportError(RuntimeError):
    """Redacted provider transport failure."""


class ProviderQuotaTransportError(ProviderTransportError):
    """A hosted provider explicitly rejected the request for quota/rate reasons."""


class HTTPXJSONTransport:
    """HTTPX implementation created only by operator composition."""

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> object:
        """Fetch JSON without reflecting URLs, keys, headers, or bodies in errors."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 429:  # noqa: PLR2004 - HTTP Too Many Requests
                    message = "hosted geocoder quota response"
                    raise ProviderQuotaTransportError(message)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as error:
            message = "hosted geocoder request failed"
            raise ProviderTransportError(message) from error


@dataclass(slots=True)
class ProviderPolicy:
    """Per-process provider rate/quota/retry policy."""

    requests_per_second: Decimal
    quota: int
    retries: int
    timeout_seconds: float
    identifying_user_agent: str
    _used: int = field(default=0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _last_call: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Reject unsafe or unbounded provider configuration."""
        if self.requests_per_second <= 0 or self.quota <= 0:
            message = "provider rate and quota must be positive"
            raise ValueError(message)
        if self.retries < 0 or self.retries > _MAX_RETRIES:
            message = "provider retries must be between zero and three"
            raise ValueError(message)
        if self.timeout_seconds <= 0 or not self.identifying_user_agent.strip():
            message = "provider timeout and identification are required"
            raise ValueError(message)

    async def enter(self) -> bool:
        """Reserve quota and enforce a monotonic per-process minimum interval."""
        async with self._lock:
            if self._used >= self.quota:
                return False
            loop = asyncio.get_running_loop()
            interval = float(Decimal(1) / self.requests_per_second)
            now = loop.time()
            if self._last_call is not None and now - self._last_call < interval:
                await asyncio.sleep(interval - (now - self._last_call))
            self._last_call = loop.time()
            self._used += 1
            return True


@dataclass(frozen=True, slots=True)
class FixtureGeocoder:
    """No-network geocoder keyed by the complete normalized query."""

    fixtures: Mapping[str, GeocodeResult]
    provider: GeocodeProvider = GeocodeProvider.FIXTURE

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Return one fixture or a stable negative cache result."""
        result = self.fixtures.get(query.normalized)
        if result is not None:
            if result.provider is not self.provider:
                message = "fixture provider identity does not match adapter"
                raise ValueError(message)
            return result
        return _error_result(
            provider=self.provider,
            error=GeocodeErrorCode.NO_RESULT,
            attribution="Synthetic no-network fixture",
        )


@dataclass(frozen=True, slots=True)
class HostedGeocoder:
    """Geoapify, LocationIQ, or policy-locked one-time Nominatim adapter."""

    provider: GeocodeProvider
    transport: JSONTransport
    policy: ProviderPolicy
    api_key: str | None = None

    def __post_init__(self) -> None:
        """Require keys for commercial hosted providers and lock Nominatim policy."""
        if self.provider not in {
            GeocodeProvider.GEOAPIFY,
            GeocodeProvider.LOCATIONIQ,
            GeocodeProvider.NOMINATIM,
        }:
            message = "hosted adapter requires a hosted provider"
            raise ValueError(message)
        if self.provider is not GeocodeProvider.NOMINATIM and not (self.api_key or "").strip():
            message = "hosted provider API key is required"
            raise ValueError(message)
        if self.provider is GeocodeProvider.NOMINATIM and (
            self.policy.requests_per_second > 1 or self.policy.quota > _MAX_NOMINATIM_SEED_QUOTA
        ):
            message = "public Nominatim is limited to a small one-time seed"
            raise ValueError(message)

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Call only the configured provider; never fan out or expose secrets."""
        for attempt in range(self.policy.retries + 1):
            if not await self.policy.enter():
                return _error_result(
                    provider=self.provider,
                    error=GeocodeErrorCode.QUOTA,
                    attribution=_attribution(self.provider),
                )
            try:
                payload = await self.transport.get_json(
                    _endpoint(self.provider),
                    params=_params(self.provider, query, self.api_key),
                    headers={"User-Agent": self.policy.identifying_user_agent},
                    timeout_seconds=self.policy.timeout_seconds,
                )
                return _map_payload(self.provider, payload)
            except ProviderQuotaTransportError:
                return _error_result(
                    provider=self.provider,
                    error=GeocodeErrorCode.QUOTA,
                    attribution=_attribution(self.provider),
                )
            except ProviderTransportError:
                if attempt == self.policy.retries:
                    return _error_result(
                        provider=self.provider,
                        error=GeocodeErrorCode.TRANSIENT,
                        attribution=_attribution(self.provider),
                    )
        return _error_result(
            provider=self.provider,
            error=GeocodeErrorCode.TRANSIENT,
            attribution=_attribution(self.provider),
        )


def _endpoint(provider: GeocodeProvider) -> str:
    return {
        GeocodeProvider.GEOAPIFY: "https://api.geoapify.com/v1/geocode/search",
        GeocodeProvider.LOCATIONIQ: "https://eu1.locationiq.com/v1/search",
        GeocodeProvider.NOMINATIM: "https://nominatim.openstreetmap.org/search",
    }[provider]


def _params(
    provider: GeocodeProvider,
    query: NormalizedGeocodeQuery,
    api_key: str | None,
) -> dict[str, str]:
    common = {"format": "json", "limit": "1"}
    if provider is GeocodeProvider.GEOAPIFY:
        west, south, east, north = WARSAW_BOUNDS
        return {
            "text": query.normalized,
            "filter": f"rect:{west},{south},{east},{north}|countrycode:pl",
            "bias": f"proximity:{WARSAW_BIAS_LON},{WARSAW_BIAS_LAT}",
            "apiKey": api_key or "",
        }
    result = {**common, "q": query.normalized, "countrycodes": "pl"}
    if provider is GeocodeProvider.LOCATIONIQ:
        result["key"] = api_key or ""
    return result


def _map_payload(provider: GeocodeProvider, payload: object) -> GeocodeResult:
    """Map only a sanitized diagnostic subset of provider-specific JSON."""
    try:
        if provider is GeocodeProvider.GEOAPIFY:
            if not isinstance(payload, dict):
                raise ValueError  # noqa: TRY301
            features = payload.get("features")
            if not isinstance(features, list) or not features:
                return _error_result(provider, GeocodeErrorCode.NO_RESULT, _attribution(provider))
            feature = features[0]
            if not isinstance(feature, dict):
                raise ValueError  # noqa: TRY301
            properties = feature.get("properties")
            geometry = feature.get("geometry")
            if not isinstance(properties, dict) or not isinstance(geometry, dict):
                raise ValueError  # noqa: TRY301
            coordinates = geometry.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) < _COORDINATE_COUNT:
                raise ValueError  # noqa: TRY301
            lon, lat = Decimal(str(coordinates[0])), Decimal(str(coordinates[1]))
            result_type = str(properties.get("result_type", "unknown"))
            return _success_result(
                provider=provider,
                provider_id=_optional_string(properties.get("place_id")),
                lon=lon,
                lat=lat,
                display=_optional_string(properties.get("formatted")),
                precision=_precision(result_type),
                confidence=Decimal(str(properties.get("rank", {}).get("confidence", 0)))
                if isinstance(properties.get("rank"), dict)
                else Decimal(0),
                result_type=result_type,
            )
        if not isinstance(payload, list) or not payload:
            return _error_result(provider, GeocodeErrorCode.NO_RESULT, _attribution(provider))
        item = payload[0]
        if not isinstance(item, dict):
            raise TypeError  # noqa: TRY301
        lon, lat = Decimal(str(item["lon"])), Decimal(str(item["lat"]))
        result_type = str(item.get("type", "unknown"))
        importance = Decimal(str(item.get("importance", "0")))
        return _success_result(
            provider=provider,
            provider_id=_optional_string(item.get("place_id")),
            lon=lon,
            lat=lat,
            display=_optional_string(item.get("display_name")),
            precision=_precision(result_type),
            confidence=max(Decimal(0), min(Decimal(1), importance)),
            result_type=result_type,
        )
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return _error_result(
            provider,
            GeocodeErrorCode.INVALID_RESPONSE,
            _attribution(provider),
        )


def _success_result(  # noqa: PLR0913
    *,
    provider: GeocodeProvider,
    provider_id: str | None,
    lon: Decimal,
    lat: Decimal,
    display: str | None,
    precision: GeocodePrecision,
    confidence: Decimal,
    result_type: str,
) -> GeocodeResult:
    return GeocodeResult(
        provider=provider,
        provider_result_id=provider_id,
        longitude=lon,
        latitude=lat,
        display_name=display,
        precision=precision,
        confidence=max(Decimal(0), min(Decimal(1), confidence)),
        within_scope=within_warsaw(lon, lat),
        attribution_text=_attribution(provider),
        diagnostic=(("result_type", result_type[:40]),),
    )


def _error_result(
    provider: GeocodeProvider,
    error: GeocodeErrorCode,
    attribution: str,
) -> GeocodeResult:
    return GeocodeResult(
        provider=provider,
        provider_result_id=None,
        longitude=None,
        latitude=None,
        display_name=None,
        precision=GeocodePrecision.UNKNOWN,
        confidence=Decimal(0),
        within_scope=None,
        attribution_text=attribution,
        error_code=error,
    )


def _optional_string(value: object) -> str | None:
    return str(value)[:240] if value is not None else None


def _precision(value: str) -> GeocodePrecision:
    normalized = value.casefold()
    if normalized in {"building", "amenity", "house"}:
        return GeocodePrecision.BUILDING
    if normalized in {"street", "road"}:
        return GeocodePrecision.STREET
    if normalized in {"district", "suburb", "borough"}:
        return GeocodePrecision.DISTRICT
    if normalized in {"city", "municipality"}:
        return GeocodePrecision.CITY
    return GeocodePrecision.UNKNOWN


def _attribution(provider: GeocodeProvider) -> str:
    return {
        GeocodeProvider.GEOAPIFY: "© OpenStreetMap contributors; Geoapify",
        GeocodeProvider.LOCATIONIQ: "© OpenStreetMap contributors; LocationIQ",
        GeocodeProvider.NOMINATIM: "© OpenStreetMap contributors",
        GeocodeProvider.FIXTURE: "Synthetic no-network fixture",
    }[provider]
