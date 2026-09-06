"""Municipal evidence is bounded, exact, and independent of synthetic map coordinates."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from wef_backend.features.ingestion.application.location_resolution import MunicipalUnavailableError
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodePrecision,
    SelectionReason,
    normalize_geocode_query,
    review_geocode_result,
)
from wef_backend.features.ingestion.infrastructure.municipal_geocoder import (
    ADDRESS_WFS,
    WFS,
    MunicipalGeocoder,
    MunicipalHTTP,
    _line,
    _params,
    _records,
)

NS = "http://fdo.osgeo.org/schemas/feature/ns92528565"
GML = "http://www.opengis.net/gml"
SOURCE = "ul. Syntetyczna, Praga-Południe, Warszawa"
LINE = "7505300 5788900 7505400 5788900"
POLYGON = "7505000 5788500 7505800 5788500 7505800 5789300 7505000 5789300 7505000 5788500"


def collection(items: str) -> bytes:
    """Encode only synthetic WFS fixtures."""
    return (
        f'<FeatureCollection xmlns:f="{NS}" xmlns:gml="{GML}">{items}</FeatureCollection>'.encode()
    )


def street(name: str = "Syntetyczna", district: str = "Praga-Południe", line: str = LINE) -> str:
    """Build one named street with projected synthetic geometry."""
    return (
        f"<f:ULICE><f:OBJECTID>1</f:OBJECTID><f:NAZWA_SKROC>{name}</f:NAZWA_SKROC>"
        f"<f:DZIELNICE>{district}</f:DZIELNICE><gml:LineString>"
        f"<gml:posList>{line}</gml:posList></gml:LineString></f:ULICE>"
    )


def district(polygon: str = POLYGON) -> bytes:
    """Build a simple synthetic district boundary."""
    return collection(
        f"<f:GRANICE_DZIELNIC><f:DZIELNICA>Praga-Południe</f:DZIELNICA><gml:Polygon><gml:exterior><gml:LinearRing><gml:posList>{polygon}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></f:GRANICE_DZIELNIC>"
    )


def addresses(*, number: str = "12", name: str = "ulica Syntetyczna", matched: int = 1) -> bytes:
    """Build an address result without any private source material."""
    return json.dumps(
        {
            "numberMatched": matched,
            "crs": {"properties": {"name": "urn:ogc:def:crs:EPSG::2178"}},
            "features": [
                {
                    "properties": {
                        "NAZWA_ULICY": name,
                        "NUMER_PORZADKOWY": number,
                        "NAZWA_MIEJSCOWOSCI": "Warszawa",
                        "ID_IIP": "synthetic-address-12",
                    },
                    "geometry": {"type": "Point", "coordinates": [7505350, 5788920]},
                }
            ],
        }
    ).encode()


class Transport:
    """Return chosen fixture bytes and retain request shape only."""

    def __init__(
        self, road: bytes | None = None, area: bytes | None = None, address: bytes | None = None
    ) -> None:
        self.road = collection(street()) if road is None else road
        self.area = district() if area is None else area
        self.address = addresses() if address is None else address
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, params: dict[str, str]) -> bytes:
        self.calls.append((url, params))
        if url == ADDRESS_WFS:
            return self.address
        return self.road if params["TYPENAME"].endswith(":ULICE") else self.area


@pytest.mark.parametrize("numbered", [False, True])
async def test_municipal_precision_and_evidence(
    monkeypatch: pytest.MonkeyPatch, *, numbered: bool
) -> None:
    transport = Transport()
    projection = AsyncMock(return_value=(Decimal("21.079"), Decimal("52.234")))
    monkeypatch.setattr(MunicipalGeocoder, "_project", projection)
    query = normalize_geocode_query(
        SOURCE.replace("Syntetyczna", "Syntetyczna 12") if numbered else SOURCE
    )
    result = await MunicipalGeocoder(MagicMock(), transport).geocode(query)
    assert review_geocode_result(result, query=query).select_result
    assert result.precision is (GeocodePrecision.BUILDING if numbered else GeocodePrecision.STREET)
    assert len(transport.calls) == (3 if numbered else 2)
    assert dict(result.diagnostic)["municipal_street_sha256"]
    assert result.address
    assert result.address.house_number == ("12" if numbered else None)
    assert projection.await_args
    assert projection.await_args.args[2] == ([7505350, 5788920] if numbered else None)


@pytest.mark.parametrize(
    ("road", "reason"),
    [
        (collection(""), SelectionReason.NO_MATCH),
        (collection(street("Other")), SelectionReason.NO_MATCH),
        (collection(street(district="Wola")), SelectionReason.NO_MATCH),
        (collection(street() + street()), SelectionReason.AMBIGUOUS_CANDIDATES),
    ],
)
async def test_wrong_or_ambiguous_streets_never_acquire_points(
    road: bytes, reason: SelectionReason
) -> None:
    transport = Transport(road=road)
    query = normalize_geocode_query(SOURCE)
    result = await MunicipalGeocoder(MagicMock(), transport).geocode(query)
    assert result.longitude is None
    assert review_geocode_result(result, query=query).reason is reason
    assert len(transport.calls) == 1


@pytest.mark.parametrize("source", ["Mokotów, Warszawa", "ul. Syntetyczna, Kraków, DE"])
async def test_absent_street_or_conflicting_locality_does_not_call_city(source: str) -> None:
    query = normalize_geocode_query(source)
    if "DE" in source:
        assert query.address
        query = replace(query, address=replace(query.address, city="Kraków", country_code="DE"))
    transport = Transport()
    result = await MunicipalGeocoder(MagicMock(), transport).geocode(query)
    assert result.longitude is None
    assert not transport.calls


@pytest.mark.parametrize(
    "body",
    [
        b"<exception/>",
        b"<!DOCTYPE x><FeatureCollection/>",
        b'<!ENTITY x "hi"><FeatureCollection/>',
        b"\x00<FeatureCollection/>",
        b"<invalid",
        b"x" * 1_000_001,
        collection(street() * 6),
    ],
)
async def test_malformed_or_truncated_response_is_transient(body: bytes) -> None:
    with pytest.raises(MunicipalUnavailableError):
        await MunicipalGeocoder(MagicMock(), Transport(road=body)).geocode(
            normalize_geocode_query(SOURCE)
        )


@pytest.mark.parametrize(
    "body",
    [
        collection(""),
        collection(
            "<f:GRANICE_DZIELNIC><f:DZIELNICA>Praga-Południe</f:DZIELNICA></f:GRANICE_DZIELNIC>"
        ),
    ],
)
async def test_missing_district_geometry_is_not_success(body: bytes) -> None:
    with pytest.raises(MunicipalUnavailableError):
        await MunicipalGeocoder(MagicMock(), Transport(area=body)).geocode(
            normalize_geocode_query(SOURCE)
        )


@pytest.mark.parametrize(
    ("number", "name", "matched"),
    [("99", "ulica Syntetyczna", 1), ("12", "Other", 1), ("12", "ulica Syntetyczna", 2)],
)
async def test_address_mismatch_and_truncation_fail_closed(
    number: str, name: str, matched: int
) -> None:
    resolver = MunicipalGeocoder(
        MagicMock(),
        Transport(address=addresses(number=number, name=name, matched=matched)),
    )
    query = normalize_geocode_query(SOURCE.replace("Syntetyczna", "Syntetyczna 12"))
    if matched == 2:
        with pytest.raises(MunicipalUnavailableError):
            await resolver.geocode(query)
    else:
        result = await resolver.geocode(query)
        assert result.longitude is None


@pytest.mark.parametrize("values", ["1 2", "1 2 3", "nan 2 3 4", ""])
def test_line_parser_rejects_invalid_coordinates(values: str) -> None:
    with pytest.raises(ValueError, match="municipal line"):
        _line(_records(collection(street(line=values)), "ULICE")[0])


def test_xml_filter_escapes_literals() -> None:
    params = _params("ULICE", "NAZWA_SKROC", "A&B<street>")
    assert "A&amp;B&lt;street&gt;" in params["FILTER"]
    assert params["MAXFEATURES"] == "6"


@pytest.mark.parametrize(
    ("status", "size", "url"),
    [(200, 4, WFS), (500, 4, WFS), (200, 1_000_001, WFS), (200, 4, "https://example.invalid")],
)
async def test_http_boundary_is_bounded(
    monkeypatch: pytest.MonkeyPatch, status: int, size: int, url: str
) -> None:
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _request: httpx.Response(status, content=b"x" * size))
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )
    client = MunicipalHTTP()
    if status == 200 and size == 4 and url == WFS:
        assert await client.get(url, {}) == b"xxxx"
    else:
        with pytest.raises((ValueError, httpx.HTTPError)):
            await client.get(url, {})


async def test_duplicate_numbered_points_remain_ambiguous() -> None:
    data = json.loads(addresses())
    data["features"] *= 2
    data["numberMatched"] = 2
    result = await MunicipalGeocoder(
        MagicMock(), Transport(address=json.dumps(data).encode())
    ).geocode(normalize_geocode_query(SOURCE.replace("Syntetyczna", "Syntetyczna 12")))
    assert dict(result.diagnostic)["candidate_ambiguity"] == "true"
    assert result.longitude is None
