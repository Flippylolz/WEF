"""Hosted geocoder wire errors, schema failures and bounded retries without network."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from tests.test_geocoding import FakeTransport, _policy, _result
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    GeocodeProvider,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import (
    FixtureGeocoder,
    HostedGeocoder,
    HTTPXJSONTransport,
    ProviderPolicy,
    ProviderQuotaTransportError,
    ProviderTransportError,
    _provider_address,
)


@pytest.mark.parametrize("mode", ["success", "quota", "server", "json", "timeout"])
async def test_httpx_geocoder_transport_uses_bounded_requests_and_safe_errors(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real HTTPX client closes after JSON, HTTP, timeout or quota outcomes."""
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if mode == "timeout":
            message = "private provider url and key"
            raise httpx.ReadTimeout(message, request=request)
        if mode == "json":
            return httpx.Response(200, text="private malformed provider body")
        return httpx.Response(
            429 if mode == "quota" else 500 if mode == "server" else 200, json={"sanitized": True}
        )

    factory = httpx.AsyncClient
    clients: list[httpx.AsyncClient] = []

    def create(**kwargs: object) -> httpx.AsyncClient:
        assert kwargs == {"timeout": 2.5}
        client = factory(transport=httpx.MockTransport(handle), timeout=2.5)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", create)
    transport = HTTPXJSONTransport()
    if mode == "success":
        assert await transport.get_json(
            "https://geocoder.invalid/search",
            params={"key": "dummy"},
            headers={"User-Agent": "WEF test"},
            timeout_seconds=2.5,
        ) == {"sanitized": True}
    else:
        expected = ProviderQuotaTransportError if mode == "quota" else ProviderTransportError
        with pytest.raises(expected) as caught:
            await transport.get_json(
                "https://geocoder.invalid/search",
                params={"key": "dummy"},
                headers={"User-Agent": "WEF test"},
                timeout_seconds=2.5,
            )
        assert "private" not in str(caught.value)
        assert "dummy" not in str(caught.value)
    assert len(requests) == 1
    assert requests[0].url.params["key"] == "dummy"
    assert requests[0].headers["User-Agent"] == "WEF test"
    assert clients[0].is_closed


@pytest.mark.parametrize(
    ("rate", "quota", "retries"), [(0, 1, 0), (1, 0, 0), (1, 1, -1), (1, 1, 4)]
)
def test_provider_policy_rejects_unbounded_or_disabled_parameters(
    rate: int, quota: int, retries: int
) -> None:
    """Runtime policies cannot authorize negative retry counts or unbounded pacing."""
    with pytest.raises(ValueError, match="provider"):
        ProviderPolicy(Decimal(rate), quota, retries, 2.5, "WEF test")


async def test_fixture_adapter_refuses_a_result_for_another_provider() -> None:
    """Provider identities remain part of the fixture cache key and contract."""
    query = normalize_geocode_query("Warszawa")
    with pytest.raises(ValueError, match="provider identity"):
        await FixtureGeocoder(
            {query.normalized: replace(_result(), provider=GeocodeProvider.GEOAPIFY)}
        ).geocode(query)


@pytest.mark.parametrize("retries", [0, 1, 3])
async def test_hosted_retry_exhaustion_makes_exactly_the_allowed_attempts(retries: int) -> None:
    """Transport errors stop after the initial attempt plus the configured retries."""
    transport = FakeTransport([ProviderTransportError() for _ in range(retries + 1)])
    result = await HostedGeocoder(
        GeocodeProvider.GEOAPIFY, transport, _policy(retries=retries), api_key="dummy"
    ).geocode(normalize_geocode_query("Warszawa"))
    assert result.error_code is GeocodeErrorCode.TRANSIENT
    assert len(transport.calls) == retries + 1


async def test_hosted_quota_response_never_retries_or_changes_provider() -> None:
    """A provider quota response stops the entire operation immediately."""
    transport = FakeTransport([ProviderQuotaTransportError()])
    result = await HostedGeocoder(
        GeocodeProvider.GEOAPIFY, transport, _policy(retries=3), api_key="dummy"
    ).geocode(normalize_geocode_query("Warszawa"))
    assert result.error_code is GeocodeErrorCode.QUOTA
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "payload", [[], {"features": [3]}, {"features": [{"properties": {}, "geometry": None}]}]
)
async def test_geoapify_rejects_malformed_envelopes(payload: object) -> None:
    """Every malformed successful provider envelope becomes an invalid-response result."""
    result = await HostedGeocoder(
        GeocodeProvider.GEOAPIFY, FakeTransport([payload]), _policy(), api_key="dummy"
    ).geocode(normalize_geocode_query("Warszawa"))
    assert result.error_code is GeocodeErrorCode.INVALID_RESPONSE


async def test_nominatim_maps_malformed_row_without_an_api_key() -> None:
    """The permitted one-time seed path validates rows with the same safe mapper."""
    transport = FakeTransport([[3]])
    policy = ProviderPolicy(Decimal(1), 1, 0, 2.5, "WEF test contact@example.invalid")
    result = await HostedGeocoder(GeocodeProvider.NOMINATIM, transport, policy).geocode(
        normalize_geocode_query("Warszawa")
    )
    assert result.error_code is GeocodeErrorCode.INVALID_RESPONSE
    assert "key" not in transport.calls[0][1]
    assert _provider_address(GeocodeProvider.GEOAPIFY, 3) is None
