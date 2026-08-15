"""Bounded operator-only Geoapify credential and egress check."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeProvider,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import (
    HostedGeocoder,
    HTTPXJSONTransport,
    ProviderPolicy,
)
from wef_backend.settings import Settings, load_settings

if TYPE_CHECKING:
    from wef_backend.features.ingestion.infrastructure.geocoder_adapters import JSONTransport

_PUBLIC_CHECK_QUERY = "Plac Defilad 1, Warszawa"


class GeoapifyCheckError(RuntimeError):
    """Raised without reflecting credentials, URLs, or provider payloads."""


async def check_geoapify(
    settings: Settings,
    *,
    transport: JSONTransport | None = None,
) -> dict[str, object]:
    """Use one credit to prove the configured key, egress, and response mapping."""
    if settings.geoapify_api_key is None:
        message = "Geoapify API key is not configured"
        raise GeoapifyCheckError(message)
    adapter = HostedGeocoder(
        provider=GeocodeProvider.GEOAPIFY,
        transport=transport or HTTPXJSONTransport(),
        policy=ProviderPolicy(
            requests_per_second=settings.geoapify_requests_per_second,
            quota=1,
            retries=1,
            timeout_seconds=15,
            identifying_user_agent="WEF production geocoder readiness/1.0",
        ),
        api_key=settings.geoapify_api_key.get_secret_value(),
    )
    result = await adapter.geocode(normalize_geocode_query(_PUBLIC_CHECK_QUERY))
    if result.error_code is not None or result.longitude is None or result.within_scope is not True:
        message = "Geoapify credential or connectivity check failed"
        raise GeoapifyCheckError(message)
    return {
        "attribution": result.attribution_text,
        "precision": result.precision.value,
        "provider": result.provider.value,
        "status": "ok",
        "within_scope": result.within_scope,
    }


def main() -> None:
    """Run the bounded check without exposing a traceback or secret material."""
    try:
        result = asyncio.run(check_geoapify(load_settings()))
    except Exception as error:  # noqa: BLE001
        message = str(error) if isinstance(error, GeoapifyCheckError) else "Geoapify check failed"
        sys.stderr.write(f"{message}\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
