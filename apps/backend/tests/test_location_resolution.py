"""Ordered fallbacks never let AI substitute an invented location."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from tests.test_geocoding import _result
from wef_backend.features.admin.application.ai_review import (
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)
from wef_backend.features.admin.application.provider_context import provider_actor
from wef_backend.features.admin.infrastructure.address_recovery import (
    AddressRecoveryGeocoder,
    CachedAddressRecovery,
)
from wef_backend.features.ingestion.application.complete_import import ProviderDailyBudgetError
from wef_backend.features.ingestion.application.geocoding import CachedGeocode, GeocodeResolution
from wef_backend.features.ingestion.application.location_resolution import (
    MunicipalUnavailableError,
    ResolveLocation,
    recovered_address,
)
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    GeocodeReviewStatus,
    ReviewDecision,
    SelectionReason,
    normalize_geocode_query,
)
from wef_backend.location_resolution import build_location_resolver
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from wef_backend.features.ingestion.application.geocoding import ResolveGeocode

SOURCE = "ul. Syntetyczna obok metra, Warszawa"


def resolution(*, accepted: bool = False, ambiguous: bool = False) -> GeocodeResolution:
    """Make a bounded synthetic response for orchestration tests."""
    decision = ReviewDecision(
        status=GeocodeReviewStatus.ACCEPTED if accepted else GeocodeReviewStatus.NEEDS_REVIEW,
        reason=SelectionReason.AMBIGUOUS_CANDIDATES if ambiguous else SelectionReason.NO_MATCH,
        select_result=accepted,
        out_of_scope=False,
    )
    return GeocodeResolution(CachedGeocode(uuid4(), _result(), None), decision, cache_hit=False)


@pytest.mark.parametrize(
    ("municipal", "hosted", "expected_calls"),
    [(True, False, 0), (False, True, 1), (False, False, 1)],
)
async def test_lookup_order_and_single_selection(
    *, municipal: bool, hosted: bool, expected_calls: int
) -> None:
    primary = AsyncMock(return_value=resolution(accepted=municipal))
    secondary = AsyncMock(return_value=resolution(accepted=hosted))
    store = MagicMock()
    store.select_for_location = AsyncMock()
    resolver = ResolveLocation(primary, secondary, store)
    await resolver(source_query=SOURCE, location_id=uuid4())
    assert secondary.await_count == expected_calls
    assert store.select_for_location.await_count == 1
    assert store.select_for_location.await_args.kwargs["actor_type"] == "automatic_policy"


async def test_authoritative_ambiguity_stops_fallback() -> None:
    primary = AsyncMock(return_value=resolution(ambiguous=True))
    secondary = AsyncMock()
    recovery = MagicMock()
    recovery.recover = AsyncMock()
    await ResolveLocation(primary, secondary, MagicMock(), recovery)(source_query=SOURCE)
    secondary.assert_not_awaited()
    recovery.recover.assert_not_awaited()


@pytest.mark.parametrize("hosted_accepts", [False, True])
async def test_municipal_outage_uses_hosted_but_does_not_become_no_result(
    *, hosted_accepts: bool
) -> None:
    primary = AsyncMock(side_effect=MunicipalUnavailableError())
    secondary = AsyncMock(return_value=resolution(accepted=hosted_accepts))
    resolver = ResolveLocation(primary, secondary, MagicMock())
    if hosted_accepts:
        assert (await resolver(source_query=SOURCE)).decision.select_result
    else:
        with pytest.raises(MunicipalUnavailableError):
            await resolver(source_query=SOURCE)


async def test_ai_recovery_gets_one_verified_lookup_pass() -> None:
    primary = AsyncMock(side_effect=[resolution(), resolution(accepted=True)])
    secondary = AsyncMock(return_value=resolution())
    recovery = MagicMock()
    recovery.recover = AsyncMock(return_value="ul. Syntetyczna, Warszawa")
    result = await ResolveLocation(primary, secondary, MagicMock(), recovery)(source_query=SOURCE)
    assert result.decision.select_result
    assert recovery.recover.await_count == 1
    assert primary.await_count == 2
    assert secondary.await_count == 1


@pytest.mark.parametrize("quote", [None, 14, "Other", "Sy", "Syntetyczna 12", "Warszawa"])
def test_recovery_rejects_invention_and_partial_names(quote: object) -> None:
    assert recovered_address(SOURCE, "Praga-Południe", quote) is None


def test_recovery_preserves_number_and_district() -> None:
    recovered = recovered_address("ul. Syntetyczna 12, Warszawa", "Wola", "Syntetyczna")
    assert recovered
    query = normalize_geocode_query(recovered, "Wola")
    assert query.address
    assert query.address.house_number == "12"
    assert query.address.district == "Wola"
    assert recovered_address(SOURCE, None, "Syntetyczna")


@pytest.mark.parametrize(
    "payload",
    [{"street": "Syntetyczna"}, {"street": "Invented"}, {"street": "Syntetyczna", "latitude": 52}],
)
async def test_ai_output_is_only_source_text(payload: object) -> None:
    sessions = MagicMock()
    session = AsyncMock()
    sessions.return_value.__aenter__.return_value = session
    session.scalar.return_value = uuid4()
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=StructuredCompletion(payload, 5, 5, 10, None))
    adapter = AddressRecoveryGeocoder(provider, sessions, uuid4())
    result = await adapter.geocode(normalize_geocode_query(SOURCE))
    assert result.longitude is None
    assert result.latitude is None
    assert (dict(result.diagnostic).get("street_quote") == "Syntetyczna") == (
        payload == {"street": "Syntetyczna"}
    )
    assert provider_actor.get() is None
    cached = replace(result, diagnostic=(("street_quote", "Invented"),))
    fake = AsyncMock(
        return_value=replace(resolution(), cached=CachedGeocode(uuid4(), cached, None))
    )
    assert await CachedAddressRecovery(cast("ResolveGeocode", fake)).recover(SOURCE, None) is None


@pytest.mark.parametrize(
    "source", ["ul. Syntetyczna +48123456789", "ul. Syntetyczna test@example.invalid", "x" * 241]
)
async def test_private_or_oversized_input_is_not_sent(source: str) -> None:
    provider = MagicMock()
    provider.complete = AsyncMock()
    result = await AddressRecoveryGeocoder(provider, MagicMock(), uuid4()).geocode(
        normalize_geocode_query(source)
    )
    assert result.error_code is GeocodeErrorCode.NO_RESULT
    provider.complete.assert_not_awaited()


@pytest.mark.parametrize(
    "outcome", [ProviderOutcome.QUOTA, ProviderOutcome.RATE_LIMITED, ProviderOutcome.REFUSAL]
)
async def test_ai_budget_defers_without_caching_false_failure(outcome: ProviderOutcome) -> None:
    sessions = MagicMock()
    session = AsyncMock()
    sessions.return_value.__aenter__.return_value = session
    session.scalar.return_value = uuid4()
    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=ProviderRequestError(outcome))
    adapter = AddressRecoveryGeocoder(provider, sessions, uuid4())
    if outcome is ProviderOutcome.REFUSAL:
        result = await adapter.geocode(normalize_geocode_query(SOURCE))
        assert result.longitude is None
    else:
        with pytest.raises(ProviderDailyBudgetError):
            await adapter.geocode(normalize_geocode_query(SOURCE))
    assert provider_actor.get() is None


def test_ai_composition_retains_all_existing_activation_gates() -> None:
    resolver = build_location_resolver(MagicMock(), MagicMock(), Settings())
    assert resolver.recovery is None
    assert resolver.municipal.request_version.startswith("municipal-v2-")
    enabled = Settings(
        ai_curation_enabled=True,
        ai_recovery_enabled=True,
        ai_recovery_activation_verified=True,
        groq_zdr_verified=True,
        groq_api_key=SecretStr("synthetic"),
        ai_recovery_owner_id=uuid4(),
    )
    assert build_location_resolver(MagicMock(), MagicMock(), enabled).recovery is not None
