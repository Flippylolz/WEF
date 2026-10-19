"""Invented municipality evidence and honest locality precision regressions."""

from dataclasses import replace
from decimal import Decimal

import pytest

from tests.test_geocode_address_accuracy import _feature, _mapped
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodePrecision,
    SelectionReason,
    normalize_geocode_query,
    normalize_location_display_name,
    review_geocode_result,
)
from wef_backend.features.ingestion.domain.nearby_locality import nearby_locality

SOURCE = "Miejscowość Testowa, гмина Przykładowa, Мазовецкое воеводство"


def _locality_feature(**overrides: object) -> dict[str, object]:
    feature = _feature(result_type="city", city="Miejscowość Testowa", district=None)
    properties = feature["properties"]
    assert isinstance(properties, dict)
    properties.pop("street")
    properties.update({"municipality": "gmina Przykładowa", **overrides})
    feature["geometry"] = {"coordinates": [21.01, 52.48]}
    return feature


def test_explicit_nearby_identity_survives_display_and_query() -> None:
    query = normalize_geocode_query(SOURCE)
    assert query.normalized == "miejscowość testowa, gmina przykładowa, pl"
    assert query.city == "Miejscowość Testowa"
    assert query.locality_only
    assert query.address is not None
    assert query.address.municipality == "Przykładowa"
    assert normalize_location_display_name(SOURCE) == "Miejscowość Testowa, gmina Przykładowa"
    assert "warszawa" not in normalize_geocode_query("ul. Testowa 8, Pruszków").normalized


@pytest.mark.parametrize(
    "value",
    [
        "Blisko Warszawy",
        "Локация: Doskonała lokalizacja",
        "Miejscowość Testowa",
        "Miejscowość Testowa, gmina Przykładowa, ul. Inna 8",
        "Warszawa za 20 minut",
    ],
)
def test_prose_or_partial_evidence_is_not_a_locality(value: str) -> None:
    assert nearby_locality(value) is None


@pytest.mark.asyncio
async def test_unique_matched_municipality_accepts_truthful_locality_precision() -> None:
    result = await _mapped(_locality_feature(), source=SOURCE)
    assert result.precision is GeocodePrecision.CITY
    decision = review_geocode_result(result, query=normalize_geocode_query(SOURCE))
    assert decision.select_result
    assert decision.reason is SelectionReason.AUTO_LOCALITY_IN_SCOPE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"municipality": "gmina Inna"}, SelectionReason.ADDRESS_MISMATCH),
        ({"municipality": None}, SelectionReason.MISSING_ADDRESS_EVIDENCE),
        ({"city": "Inna Miejscowość"}, SelectionReason.ADDRESS_MISMATCH),
        ({"country_code": "de"}, SelectionReason.ADDRESS_MISMATCH),
        ({"rank": {"confidence": 0.5}}, SelectionReason.LOW_CONFIDENCE),
        ({"result_type": "building"}, SelectionReason.UNSUPPORTED_PRECISION),
    ],
)
async def test_locality_selection_requires_independent_evidence(
    overrides: dict[str, object], reason: SelectionReason
) -> None:
    result = await _mapped(_locality_feature(**overrides), source=SOURCE)
    decision = review_geocode_result(result, query=normalize_geocode_query(SOURCE))
    assert not decision.select_result
    assert decision.reason is reason


@pytest.mark.asyncio
async def test_same_named_towns_and_outside_bounds_do_not_select() -> None:
    first = _locality_feature()
    second = _locality_feature()
    second["geometry"] = {"coordinates": [21.02, 52.49]}
    result = await _mapped(first, second, source=SOURCE)
    assert (
        review_geocode_result(result, query=normalize_geocode_query(SOURCE)).reason
        is SelectionReason.AMBIGUOUS_CANDIDATES
    )
    unique = await _mapped(first, source=SOURCE)
    outside = replace(unique, latitude=Decimal("53.0"))
    assert (
        review_geocode_result(outside, query=normalize_geocode_query(SOURCE)).reason
        is SelectionReason.OUT_OF_SCOPE
    )


@pytest.mark.asyncio
async def test_city_fallback_cannot_erase_source_street_evidence() -> None:
    result = await _mapped(_locality_feature(), source=SOURCE)
    query = normalize_geocode_query("ul. Testowa 8, Miejscowość Testowa")
    assert not review_geocode_result(result, query=query).select_result
