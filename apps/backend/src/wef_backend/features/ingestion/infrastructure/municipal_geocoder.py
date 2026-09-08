"""Bounded Warsaw WFS lookup with PostGIS verification of municipal geometry."""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from xml.sax.saxutils import escape

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.features.ingestion.application.location_resolution import MunicipalUnavailableError
from wef_backend.features.ingestion.domain.address_evidence import AddressEvidence, fold_address
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    NormalizedGeocodeQuery,
    canonical_warsaw_district,
    within_warsaw,
)
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import ProviderPolicy

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

WFS = "https://wfs.um.warszawa.pl/serwis"
ADDRESS_WFS = "https://wms2.um.warszawa.pl/geoserver/wfs/wfs"
ATTRIBUTION = "Urząd m.st. Warszawy — miejskie dane adresowe i nazewnicze"
_NS = "http://fdo.osgeo.org/schemas/feature/ns92528565"
_GML = "http://www.opengis.net/gml"
_LIMIT = 6
_MAX_BYTES = 1_000_000
_MIN_LINE_VALUES = 4
_MAX_LINE_VALUES = 20_000
_POINT_VALUES = 2


class MunicipalTransport(Protocol):
    """Replaceable, bounded public-data transport."""

    async def get(self, url: str, params: dict[str, str]) -> bytes:
        """Read a bounded body without redirects or credentials."""
        ...


class MunicipalHTTP:
    """One request per second, no retries, and at most one MB per response."""

    def __init__(self) -> None:
        """Set the public-service rate and per-cycle ceiling."""
        self.policy = ProviderPolicy(Decimal(1), 100, 0, 10, "WEF municipal lookup/1.0")

    async def get(self, url: str, params: dict[str, str]) -> bytes:
        """Stream only allowlisted endpoints under the response ceiling."""
        if url not in {WFS, ADDRESS_WFS} or not await self.policy.enter():
            message = "municipal request limit"
            raise ValueError(message)
        async with (
            httpx.AsyncClient(timeout=10, follow_redirects=False) as client,
            client.stream(
                "GET", url, params=params, headers={"User-Agent": "WEF municipal lookup/1.0"}
            ) as response,
        ):
            response.raise_for_status()
            body = bytearray()
            async for part in response.aiter_bytes():
                body.extend(part)
                if len(body) > _MAX_BYTES:
                    message = "municipal response limit"
                    raise ValueError(message)
            return bytes(body)


def _params(layer: str, field: str, value: str) -> dict[str, str]:
    condition = (
        "<PropertyIsEqualTo>"
        f"<PropertyName>{field}</PropertyName><Literal>{escape(value)}</Literal>"
        "</PropertyIsEqualTo>"
    )
    return {
        "SERVICE": "WFS",
        "VERSION": "1.1.0",
        "REQUEST": "GetFeature",
        "TYPENAME": f"ns92528565:{layer}",
        "MAXFEATURES": str(_LIMIT),
        "SRSNAME": "EPSG:2178",
        "FILTER": f'<Filter xmlns="http://www.opengis.net/ogc">{condition}</Filter>',
    }


def _records(body: bytes, layer: str) -> list[ET.Element]:
    if len(body) > _MAX_BYTES or b"<!DOCTYPE" in body or b"<!ENTITY" in body or b"\x00" in body:
        message = "unsafe municipal XML"
        raise ValueError(message)
    root = ET.fromstring(body)  # noqa: S314 - capped UTF-8/ASCII body; DTD/entities/null encodings rejected
    if not root.tag.endswith("FeatureCollection"):
        message = "municipal service exception"
        raise ValueError(message)
    rows = root.findall(f".//{{{_NS}}}{layer}")
    if len(rows) >= _LIMIT:
        message = "truncated municipal response"
        raise ValueError(message)
    return rows


def _field(row: ET.Element, name: str) -> str:
    return (row.findtext(f"{{{_NS}}}{name}") or "").strip()


def _line(row: ET.Element) -> str:
    lines = []
    for values in row.findall(f".//{{{_GML}}}posList"):
        numbers = [float(value) for value in (values.text or "").split()]
        if (
            not _MIN_LINE_VALUES <= len(numbers) <= _MAX_LINE_VALUES
            or len(numbers) % 2
            or not all(math.isfinite(v) for v in numbers)
        ):
            message = "invalid municipal line"
            raise ValueError(message)
        lines.append(
            "("
            + ",".join(f"{numbers[i]} {numbers[i + 1]}" for i in range(0, len(numbers), 2))
            + ")"
        )
    if not lines:
        message = "missing municipal line"
        raise ValueError(message)
    return "MULTILINESTRING(" + ",".join(lines) + ")"


def _polygon(row: ET.Element) -> ET.Element:
    """Accept a single polygon or the city's single GML Surface patch."""
    polygons = row.findall(f".//{{{_GML}}}Polygon")
    patches = row.findall(f".//{{{_GML}}}PolygonPatch")
    if len(polygons) + len(patches) != 1:
        message = "missing or ambiguous municipal district"
        raise ValueError(message)
    if polygons:
        return polygons[0]
    surface = row.find(f".//{{{_GML}}}Surface")
    if surface is None or surface.get("srsName") != "EPSG:2178":
        message = "invalid municipal district CRS"
        raise ValueError(message)
    polygon = ET.Element(f"{{{_GML}}}Polygon")
    polygon.extend(patches[0])
    return polygon


def _empty(
    error: GeocodeErrorCode = GeocodeErrorCode.NO_RESULT, *, ambiguous: bool = False
) -> GeocodeResult:
    return GeocodeResult(
        provider=GeocodeProvider.MUNICIPAL,
        provider_result_id=None,
        longitude=None,
        latitude=None,
        display_name=None,
        precision=GeocodePrecision.UNKNOWN,
        confidence=Decimal(0),
        within_scope=None,
        attribution_text=ATTRIBUTION,
        error_code=error,
        diagnostic=(("candidate_ambiguity", "true" if ambiguous else "false"),),
    )


@dataclass(frozen=True, slots=True)
class MunicipalGeocoder:
    """Match municipal street identity before deriving any coordinate."""

    sessions: async_sessionmaker[AsyncSession]
    transport: MunicipalTransport
    provider: GeocodeProvider = GeocodeProvider.MUNICIPAL

    async def geocode(self, query: NormalizedGeocodeQuery) -> GeocodeResult:
        """Read source-supported municipal evidence without accepting coarse results."""
        address = query.address
        if (
            not address
            or fold_address(address.city) not in {"warszawa", "warsaw"}
            or fold_address(address.country_code) != "pl"
        ):
            return _empty()
        try:
            if not address.street and not address.house_number:
                return await self._district_area(address)
            return await self._lookup(address)
        except (
            httpx.HTTPError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            KeyError,
            ET.ParseError,
        ) as error:
            message = "municipal lookup unavailable"
            raise MunicipalUnavailableError(message) from error

    async def _district_area(self, address: AddressEvidence) -> GeocodeResult:
        """Use one authoritative district polygon only for area-only source evidence."""
        district = canonical_warsaw_district(address.district)
        if district is None:
            return _empty()
        body = await self.transport.get(WFS, _params("GRANICE_DZIELNIC", "DZIELNICA", district))
        rows = [
            row
            for row in _records(body, "GRANICE_DZIELNIC")
            if canonical_warsaw_district(_field(row, "DZIELNICA")) == district
        ]
        if len(rows) != 1:
            return _empty(ambiguous=len(rows) > 1)
        polygon = ET.tostring(_polygon(rows[0]), encoding="unicode")
        async with self.sessions() as session:
            row = (
                await session.execute(
                    text("""
                WITH area AS (SELECT ST_SetSRID(ST_GeomFromGML(:polygon),2178) geom),
                valid AS (SELECT geom FROM area WHERE ST_IsValid(geom)
                    AND NOT ST_IsEmpty(geom) AND ST_Area(geom)>0),
                point AS (SELECT ST_Transform(ST_PointOnSurface(geom),4326) geom FROM valid)
                SELECT ST_X(geom),ST_Y(geom) FROM point
            """),
                    {"polygon": polygon},
                )
            ).one_or_none()
        if row is None:
            return _empty()
        lon, lat = Decimal(str(row[0])), Decimal(str(row[1]))
        return GeocodeResult(
            provider=self.provider,
            provider_result_id=f"GRANICE_DZIELNIC:{district}",
            longitude=lon,
            latitude=lat,
            display_name=f"{district}, Warszawa",
            precision=GeocodePrecision.DISTRICT,
            confidence=Decimal(1),
            within_scope=within_warsaw(lon, lat),
            attribution_text=ATTRIBUTION,
            address=AddressEvidence(
                district=district, city="Warszawa", country_code="PL", result_type="district"
            ),
            diagnostic=(("municipal_district_sha256", hashlib.sha256(body).hexdigest()),),
        )

    async def _lookup(self, address: AddressEvidence) -> GeocodeResult:
        if address.street is None:
            return _empty()
        # Exact municipal identity is required; unsupported spellings use hosted fallback.
        term = address.street.removeprefix("ul. ").removeprefix("ulica ")
        body = await self.transport.get(WFS, _params("ULICE", "NAZWA_SKROC", term))
        rows = [
            row
            for row in _records(body, "ULICE")
            if fold_address(_field(row, "NAZWA_SKROC")) == fold_address(address.street)
        ]
        if address.district:
            rows = [
                row
                for row in rows
                if canonical_warsaw_district(address.district)
                in [canonical_warsaw_district(v) for v in _field(row, "DZIELNICE").split(",")]
            ]
        if len(rows) != 1:
            return _empty(ambiguous=len(rows) > 1)
        row = rows[0]
        district = canonical_warsaw_district(address.district) or canonical_warsaw_district(
            _field(row, "DZIELNICE")
        )
        if not district:
            return _empty(ambiguous=True)
        district_body = await self.transport.get(
            WFS, _params("GRANICE_DZIELNIC", "DZIELNICA", district)
        )
        districts = [
            r
            for r in _records(district_body, "GRANICE_DZIELNIC")
            if canonical_warsaw_district(_field(r, "DZIELNICA")) == district
        ]
        if len(districts) != 1:
            message = "municipal district unavailable"
            raise ValueError(message)
        polygon = _polygon(districts[0])
        point = None
        address_hash = ""
        identity = "ULICE:" + _field(row, "OBJECTID")
        if address.house_number:
            point, identity, address_hash = await self._address_point(
                address, _field(row, "NAZWA_SKROC")
            )
            if point is None:
                return _empty(ambiguous=identity == "ambiguous")
        coordinates = await self._project(
            _line(row), ET.tostring(polygon, encoding="unicode"), point
        )
        if coordinates is None:
            return _empty()
        lon, lat = coordinates
        evidence = AddressEvidence(
            street=_field(row, "NAZWA_SKROC"),
            house_number=address.house_number,
            district=district,
            city="Warszawa",
            country_code="PL",
            result_type="house" if point else "street",
        )
        return GeocodeResult(
            provider=self.provider,
            provider_result_id=identity,
            longitude=lon,
            latitude=lat,
            display_name=(
                f"{evidence.street}"
                f"{' ' + address.house_number if address.house_number else ''}"
                f", {district}, Warszawa"
            ),
            precision=GeocodePrecision.BUILDING if point else GeocodePrecision.STREET,
            confidence=Decimal("0.95"),
            within_scope=True,
            attribution_text=ATTRIBUTION,
            error_code=None,
            address=evidence,
            diagnostic=(
                ("municipal_street_sha256", hashlib.sha256(body).hexdigest()),
                ("municipal_district_sha256", hashlib.sha256(district_body).hexdigest()),
                (
                    "coordinate_method",
                    "address_point" if point else "longest_street_segment_midpoint",
                ),
                ("source_url", ADDRESS_WFS if point else WFS),
                ("municipal_address_sha256", address_hash),
            ),
        )

    async def _address_point(
        self, address: AddressEvidence, street: str
    ) -> tuple[list[float] | None, str, str]:
        def literal(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"

        names = " OR ".join(f"NAZWA_ULICY = {literal(v)}" for v in (street, "ulica " + street))
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "wfs:punkty_adresowe",
            "count": str(_LIMIT),
            "outputFormat": "application/json",
            "srsName": "EPSG:2178",
            "CQL_FILTER": f"({names}) AND NUMER_PORZADKOWY = {literal(address.house_number or '')}",
        }
        body = await self.transport.get(ADDRESS_WFS, params)
        data = json.loads(body)
        features = data["features"]
        if data.get("numberMatched") != len(features) or len(features) >= _LIMIT:
            message = "incomplete municipal address response"
            raise ValueError(message)
        crs = data.get("crs")
        properties = crs.get("properties") if isinstance(crs, dict) else None
        if features and (
            not isinstance(properties, dict)
            or properties.get("name") != "urn:ogc:def:crs:EPSG::2178"
        ):
            message = "wrong municipal CRS"
            raise ValueError(message)
        matches = []
        for feature in features:
            props = feature["properties"]
            if (
                fold_address(props.get("NAZWA_ULICY")) != fold_address(address.street)
                or fold_address(props.get("NUMER_PORZADKOWY")) != fold_address(address.house_number)
                or props.get("NAZWA_MIEJSCOWOSCI") != "Warszawa"
            ):
                continue
            geometry = feature["geometry"]
            coords = geometry["coordinates"]
            if (
                geometry["type"] != "Point"
                or len(coords) != _POINT_VALUES
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in coords)
            ):
                message = "invalid address point"
                raise ValueError(message)
            matches.append((coords, str(props["ID_IIP"])))
        return (
            (*matches[0], hashlib.sha256(body).hexdigest())
            if len(matches) == 1
            else (None, "ambiguous" if len(matches) > 1 else "", "")
        )

    async def _project(
        self, line: str, polygon: str, point: list[float] | None
    ) -> tuple[Decimal, Decimal] | None:
        async with self.sessions() as session:
            row = (
                await session.execute(
                    text("""
                WITH geometry AS (
                    SELECT ST_LineMerge(ST_GeomFromText(:line,2178)) line,
                           ST_SetSRID(ST_GeomFromGML(:polygon),2178) district
                ), valid AS (
                    SELECT *, CASE WHEN ST_Covers(district,line) THEN line
                                   ELSE ST_LineMerge(ST_Intersection(line,district)) END clipped
                    FROM geometry WHERE ST_IsValid(district) AND ST_IsSimple(line)
                ), target AS (
                    SELECT *, CASE WHEN :numbered THEN ST_SetSRID(ST_MakePoint(:x,:y),2178)
                              ELSE (SELECT ST_LineInterpolatePoint(segment.geom,0.5)
                                    FROM ST_Dump(ST_CollectionExtract(clipped,2)) segment
                                    WHERE ST_Length(segment.geom)>0
                                    ORDER BY ST_Length(segment.geom) DESC,
                                             ST_AsEWKB(segment.geom)
                                    LIMIT 1) END point
                    FROM valid
                )
                SELECT ST_X(ST_Transform(point,4326)),ST_Y(ST_Transform(point,4326))
                FROM target WHERE ST_Covers(district,point) AND ST_DWithin(line,point,150)
            """),
                    {
                        "line": line,
                        "polygon": polygon,
                        "numbered": point is not None,
                        "x": point[0] if point else 0,
                        "y": point[1] if point else 0,
                    },
                )
            ).one_or_none()
        if row is None:
            return None
        lon, lat = Decimal(str(row[0])), Decimal(str(row[1]))
        return (lon, lat) if within_warsaw(lon, lat) else None
