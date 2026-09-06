"""Sanitized E26 address-agreement regressions; no claimed production coordinates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from tests.test_geocoding import NOW, FakeStore, FakeTransport, _policy
from wef_backend.features.ingestion.application.geocoding import CachedGeocode, ResolveGeocode
from wef_backend.features.ingestion.domain.address_evidence import AddressEvidence, fold_address
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    SelectionReason,
    normalize_geocode_query,
    normalize_location_display_name,
    review_geocode_result,
    within_warsaw,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import HostedGeocoder

if TYPE_CHECKING:
    from datetime import datetime

    from wef_backend.features.ingestion.application.geocoding import MissClaim
    from wef_backend.features.ingestion.domain.geocoding import NormalizedGeocodeQuery


def _feature(
    street: str = "Jugosłowiańska",
    *,
    result_type: str = "street",
    number: str | None = None,
    city: str | None = "Warszawa",
    district: str | None = "Praga-Południe",
    country: str | None = "pl",
    confidence: float = 1.0,
    longitude: float = 21.01,
) -> dict[str, object]:
    """Synthetic point and address components, never a proposed real-world correction."""
    return {
        "geometry": {"coordinates": [longitude, 52.23]},
        "properties": {
            "street": street,
            "housenumber": number,
            "city": city,
            "district": district,
            "country_code": country,
            "result_type": result_type,
            "rank": {"confidence": confidence},
            "formatted": "Sanitized provider fixture",
            "api_key": "must-not-be-persisted",
            "contact": "must-not-be-persisted",
        },
    }


async def _mapped(*features: object, source: str = "ul. Jugosłowiańska") -> GeocodeResult:
    adapter = HostedGeocoder(
        GeocodeProvider.GEOAPIFY,
        FakeTransport([{"features": list(features)}]),
        _policy(),
        api_key="private-key",
    )
    return await adapter.geocode(normalize_geocode_query(source))


@pytest.mark.parametrize(
    ("feature", "source", "reason"),
    [
        (
            _feature("Grochowska", result_type="amenity"),
            "ul. Jugosłowiańska",
            SelectionReason.ADDRESS_MISMATCH,
        ),
        (
            _feature(result_type="building", number="1"),
            "ul. Jugosłowiańska",
            SelectionReason.UNSUPPORTED_PRECISION,
        ),
        (
            _feature(result_type="amenity", number="1"),
            "ul. Jugosłowiańska 1",
            SelectionReason.LOW_PRECISION,
        ),
        (
            _feature(result_type="building", number="2"),
            "ul. Jugosłowiańska 1",
            SelectionReason.ADDRESS_MISMATCH,
        ),
        (
            _feature(result_type="building"),
            "ul. Jugosłowiańska 1",
            SelectionReason.UNSUPPORTED_PRECISION,
        ),
        (_feature(city="Kraków"), "ul. Jugosłowiańska", SelectionReason.ADDRESS_MISMATCH),
        (_feature(country="de"), "ul. Jugosłowiańska", SelectionReason.ADDRESS_MISMATCH),
        (_feature(city=None), "ul. Jugosłowiańska", SelectionReason.MISSING_ADDRESS_EVIDENCE),
        (_feature(country=None), "ul. Jugosłowiańska", SelectionReason.MISSING_ADDRESS_EVIDENCE),
        (
            _feature(district="Mokotów"),
            "ul. Jugosłowiańska | Gocław",
            SelectionReason.ADDRESS_MISMATCH,
        ),
        (
            _feature(district=None),
            "ul. Jugosłowiańska | Gocław",
            SelectionReason.MISSING_ADDRESS_EVIDENCE,
        ),
        (
            _feature(street="", result_type="district"),
            "ul. Jugosłowiańska",
            SelectionReason.MISSING_ADDRESS_EVIDENCE,
        ),
        (_feature(confidence=0.5), "ul. Jugosłowiańska", SelectionReason.LOW_CONFIDENCE),
        (_feature(longitude=19), "ul. Jugosłowiańska", SelectionReason.OUT_OF_SCOPE),
        (_feature(), "Gocław", SelectionReason.UNSUPPORTED_PRECISION),
    ],
)
async def test_rejects_unsupported_claims(
    feature: object,
    source: str,
    reason: SelectionReason,
) -> None:
    result = await _mapped(feature, source=source)
    decision = review_geocode_result(result, query=normalize_geocode_query(source))
    assert not decision.select_result
    assert decision.reason is reason


@pytest.mark.parametrize("source", ["ul. Jugosłowiańska | Gocław", "Goclaw | ул. Jugosłowiańska"])
async def test_goclaw_preserves_street_and_warsaw_context(source: str) -> None:
    query = normalize_geocode_query(source)
    assert query.original == source
    assert query.address is not None
    assert query.address.neighborhood == "Gocław"
    assert query.address.city == "Warszawa"
    assert query.address.district == "Praga-Południe"
    display = normalize_location_display_name(source)
    assert "Jugosłowiańska" in display
    assert display.endswith("Warszawa")
    result = await _mapped(_feature(), source=source)
    assert review_geocode_result(result, query=query).select_result


async def test_candidate_order_cannot_prefer_high_confidence_wrong_street() -> None:
    wrong = _feature("Grochowska", result_type="amenity")
    right = _feature(confidence=0.9)
    for features in [(wrong, right), (right, wrong)]:
        result = await _mapped(*features)
        assert result.address is not None
        assert result.address.street == "Jugosłowiańska"
        assert review_geocode_result(
            result, query=normalize_geocode_query("ul. Jugosłowiańska")
        ).select_result
        diagnostic = json.dumps(dict(result.diagnostic))
        assert "must-not-be-persisted" not in diagnostic
        assert "private-key" not in diagnostic
        assert len(json.loads(dict(result.diagnostic)["candidate_evidence"])) == 2


async def test_confidence_does_not_resolve_same_street_position_ambiguity() -> None:
    result = await _mapped(_feature(), _feature(longitude=21.05, confidence=0.6))
    decision = review_geocode_result(result, query=normalize_geocode_query("ul. Jugosłowiańska"))
    assert decision.reason is SelectionReason.AMBIGUOUS_CANDIDATES
    assert not decision.select_result


async def test_only_five_candidates_are_considered_and_duplicates_are_safe() -> None:
    result = await _mapped(*([_feature()] * 5), _feature(longitude=21.05))
    assert review_geocode_result(
        result, query=normalize_geocode_query("ul. Jugosłowiańska")
    ).select_result
    assert len(json.loads(dict(result.diagnostic)["candidate_evidence"])) == 5


async def test_numbered_source_accepts_only_matching_building_evidence() -> None:
    result = await _mapped(
        _feature(result_type="building", number="1"), source="ul. Jugosłowiańska 1"
    )
    assert result.precision is GeocodePrecision.BUILDING
    assert review_geocode_result(
        result, query=normalize_geocode_query("ul. Jugosłowiańska 1")
    ).select_result
    legacy = replace(result, address=None)
    assert (
        review_geocode_result(legacy, query=normalize_geocode_query("ul. Jugosłowiańska 1")).reason
        is SelectionReason.MISSING_ADDRESS_EVIDENCE
    )
    assert not review_geocode_result(result).select_result


@dataclass
class _KeyedStore(FakeStore):
    values: dict[str, CachedGeocode] = field(default_factory=dict)

    async def get_cached(self, key: GeocodeCacheKey) -> CachedGeocode | None:
        return self.values.get(key.query_hash)

    async def complete_miss(
        self,
        key: GeocodeCacheKey,
        *,
        claim: MissClaim,
        query: NormalizedGeocodeQuery,
        result: GeocodeResult,
        attempted_at: datetime,
        expires_at: datetime | None,
    ) -> CachedGeocode:
        cached = await super().complete_miss(
            key,
            claim=claim,
            query=query,
            result=result,
            attempted_at=attempted_at,
            expires_at=expires_at,
        )
        self.values[key.query_hash] = cached
        return cached


async def test_two_quality_forms_are_cached_across_resolver_restarts() -> None:
    transport = FakeTransport([{"features": [_feature("Grochowska")]}, {"features": []}])
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="private")
    store = _KeyedStore()
    source = "Warszawa | Praga-Południe | ul. Jugosłowiańska"
    first = await ResolveGeocode(store, geocoder, clock=lambda: NOW)(source_query=source)
    second = await ResolveGeocode(store, geocoder, clock=lambda: NOW)(source_query=source)
    assert first.decision.reason is SelectionReason.NO_MATCH
    assert second.decision.reason is SelectionReason.NO_MATCH
    assert second.cache_hit
    assert len(transport.calls) == 2
    assert all("jugosłowiańska" in call[1]["text"] for call in transport.calls)
    assert all(call[1]["limit"] == "5" for call in transport.calls)


async def test_retry_can_select_street_candidate_without_inventing_a_number() -> None:
    transport = FakeTransport(
        [
            {"features": [_feature(result_type="building", number="1")]},
            {"features": [_feature()]},
        ]
    )
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="private")
    result = await ResolveGeocode(_KeyedStore(), geocoder, clock=lambda: NOW)(
        source_query="Warszawa | ul. Jugosłowiańska",
    )
    assert result.decision.select_result
    assert result.cached.result.precision is GeocodePrecision.STREET
    assert len(transport.calls) == 2
    assert all("1" not in call[1]["text"] for call in transport.calls)


async def test_quota_does_not_trigger_quality_fallback() -> None:
    transport = FakeTransport([])
    policy = _policy(quota=1)
    assert await policy.enter()
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, policy, api_key="private")
    result = await ResolveGeocode(_KeyedStore(), geocoder, clock=lambda: NOW)(
        source_query="Warszawa | ul. Jugosłowiańska",
    )
    assert result.cached.result.error_code is GeocodeErrorCode.QUOTA
    assert not transport.calls


def test_bounded_evidence_and_numeric_scope_fail_closed() -> None:
    assert AddressEvidence.from_json(None) is None
    assert AddressEvidence.from_json({"version": "old"}) is None
    assert AddressEvidence.from_json({"version": "address-evidence-v1", "street": []}) is None
    evidence = AddressEvidence(street="x" * 500)
    restored = AddressEvidence.from_json(evidence.as_json())
    assert restored is not None
    assert len(restored.street or "") == 240
    assert fold_address("ul. JUGOSŁOWIAŃSKA") == fold_address("Jugoslowianska")
    assert not within_warsaw(Decimal("NaN"), Decimal("52.2"))
    assert not within_warsaw(Decimal(21), Decimal("Infinity"))


async def test_clean_street_query_uses_distinct_cached_street_request() -> None:
    transport = FakeTransport(
        [
            {"features": [_feature(result_type="building", number="1")]},
            {"features": [_feature()]},
        ]
    )
    store = _KeyedStore()
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="private")
    for _ in range(2):
        result = await ResolveGeocode(store, geocoder)(source_query="ul. Jugosłowiańska")
        assert result.decision.select_result
    assert len(transport.calls) == 2
    assert transport.calls[0][1]["text"] == transport.calls[1][1]["text"]
    assert "type" not in transport.calls[0][1]
    assert transport.calls[1][1]["type"] == "street"
    assert len(store.values) == 2


@pytest.mark.parametrize("source", ["ul. Testowa 1, ul. Testowa 2", "ul. Testowa 1, ul. Inna 1"])
async def test_conflicting_source_addresses_do_not_use_the_last_segment(source: str) -> None:
    result = await _mapped(_feature("Testowa", result_type="building", number="1"), source=source)
    assert not review_geocode_result(result, query=normalize_geocode_query(source)).select_result


@pytest.mark.parametrize(
    ("suburb", "source", "district"),
    [
        ("South Praga", "ul. Jugosłowiańska | Gocław", "Praga-Południe"),
        (" south PRAGA ", "ul. Ostrzycka | Gocław", "Praga-Południe"),
        ("North Praga", "ul. Testowa | Praga-Północ", "Praga-Północ"),
    ],
)
async def test_provider_translated_district_is_not_an_unrelated_neighborhood(
    suburb: str, source: str, district: str
) -> None:
    query = normalize_geocode_query(source)
    assert query.address is not None
    feature = _feature(query.address.street or "", district=None, city="Warsaw")
    properties = feature["properties"]
    assert isinstance(properties, dict)
    properties["suburb"] = suburb
    result = await _mapped(feature, source=source)
    assert result.address is not None
    assert result.address.district == district
    assert result.address.neighborhood is None
    assert review_geocode_result(result, query=query).select_result
    assert result.precision is GeocodePrecision.STREET


@pytest.mark.parametrize(
    ("suburb", "district", "reason"),
    [
        ("North Praga", None, SelectionReason.ADDRESS_MISMATCH),
        ("South Praga vicinity", None, SelectionReason.MISSING_ADDRESS_EVIDENCE),
        ("South Praga", "Mokotów", SelectionReason.ADDRESS_MISMATCH),
    ],
)
async def test_provider_alias_does_not_relax_unknown_or_conflicting_districts(
    suburb: str, district: str | None, reason: SelectionReason
) -> None:
    source = "ul. Jugosłowiańska | Gocław"
    feature = _feature(district=district)
    properties = feature["properties"]
    assert isinstance(properties, dict)
    properties["suburb"] = suburb
    result = await _mapped(feature, source=source)
    decision = review_geocode_result(result, query=normalize_geocode_query(source))
    assert not decision.select_result
    assert decision.reason is reason


async def test_provider_alias_upgrade_does_not_reuse_v3_address_cache() -> None:
    source = "ul. Jugosłowiańska | Gocław"
    query = normalize_geocode_query(source)
    feature = _feature(district=None, city="Warsaw")
    properties = feature["properties"]
    assert isinstance(properties, dict)
    properties["suburb"] = "South Praga"
    current = await _mapped(feature, source=source)
    assert current.address is not None
    old = replace(
        current, address=replace(current.address, district=None, neighborhood="South Praga")
    )
    store = _KeyedStore()
    old_key = GeocodeCacheKey(
        GeocodeProvider.GEOAPIFY, query.normalized, request_version="forward-geocode-v3"
    )
    store.values[old_key.query_hash] = CachedGeocode(uuid4(), old, None)
    transport = FakeTransport([{"features": [feature]}])
    geocoder = HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="private")
    resolver = ResolveGeocode(store, geocoder, clock=lambda: NOW)
    first = await resolver(source_query=source)
    assert first.decision.select_result
    assert not first.cache_hit
    assert (await resolver(source_query=source)).cache_hit
    assert len(transport.calls) == 1
    assert len(store.values) == 2
