"""Real PostGIS validates municipal points and clips street lines to source districts."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text

from tests.test_geocoding_integration import TEST_DATABASE_URL, _prepare
from tests.test_municipal_geocoder import POLYGON, SOURCE, Transport, collection, district, street
from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.domain.geocoding import normalize_geocode_query
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.municipal_geocoder import MunicipalGeocoder

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]
POLYGON_GML = f'<gml:Polygon xmlns:gml="http://www.opengis.net/gml"><gml:exterior><gml:LinearRing><gml:posList>{POLYGON}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>'


async def test_real_street_selection_cache_and_weekly_refresh() -> None:
    database, location = await _prepare()
    transport = Transport()
    resolver = ResolveGeocode(
        SQLAlchemyGeocodeStore(database.session_factory),
        MunicipalGeocoder(database.session_factory, transport),
        request_version="municipal-v1-2030-W01",
        fallback_forms=False,
    )
    direct = await resolver.geocoder.geocode(normalize_geocode_query(SOURCE))
    assert direct.longitude is not None, (direct, transport.calls)
    transport.calls.clear()
    first = await resolver(source_query=SOURCE, location_id=location.id)
    assert first.decision.select_result
    second = await resolver(source_query=SOURCE)
    assert second.cache_hit
    assert len(transport.calls) == 2
    refreshed = ResolveGeocode(
        resolver.store,
        resolver.geocoder,
        request_version="municipal-v1-2030-W02",
        fallback_forms=False,
    )
    third = await refreshed(source_query=SOURCE)
    assert not third.cache_hit
    assert third.cached.result_id != first.cached.result_id
    async with database.session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT precision, review_status, ST_X(point), ST_Y(point) "
                    "FROM locations WHERE id=:id"
                ),
                {"id": location.id},
            )
        ).one()
        assert row.precision == "street"
        assert row.review_status == "accepted"
        assert first.cached.result.longitude is not None
        assert abs(Decimal(str(row[2])) - first.cached.result.longitude) < Decimal("0.000000001")


async def test_real_numbered_address_and_source_mismatch() -> None:
    assert TEST_DATABASE_URL
    database = create_database_resources(TEST_DATABASE_URL)
    geocoder = MunicipalGeocoder(database.session_factory, Transport())
    result = await geocoder.geocode(
        normalize_geocode_query(SOURCE.replace("Syntetyczna", "Syntetyczna 12"))
    )
    assert result.longitude is not None
    assert result.precision.value == "building"
    assert result.address
    assert result.address.house_number == "12"


@pytest.mark.parametrize(
    ("line", "point"),
    [
        ("MULTILINESTRING((7505300 5788900,7505400 5788900))", [7505350, 5789500]),
        (
            "MULTILINESTRING((7505300 5788900,7505400 5788900),(7505600 5788900,7505700 5788900))",
            None,
        ),
        ("MULTILINESTRING((7505300 5788900,7505300 5788900))", None),
        ("MULTILINESTRING((7500000 5780000,7500100 5780000))", None),
    ],
)
async def test_real_district_and_disconnected_geometry_reject(
    line: str, point: list[float] | None
) -> None:
    assert TEST_DATABASE_URL
    database = create_database_resources(TEST_DATABASE_URL)
    result = await MunicipalGeocoder(database.session_factory, Transport())._project(  # noqa: SLF001 - prove real geometry boundary
        line, POLYGON_GML, point
    )
    assert result is None


async def test_real_line_is_clipped_to_source_district() -> None:
    assert TEST_DATABASE_URL
    database = create_database_resources(TEST_DATABASE_URL)
    geocoder = MunicipalGeocoder(
        database.session_factory,
        Transport(road=collection(street(line="7504000 5788900 7505400 5788900"))),
    )
    result = await geocoder.geocode(normalize_geocode_query(SOURCE))
    assert result.longitude is not None
    async with database.session_factory() as session:
        x = await session.scalar(
            text("SELECT ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),2178))"),
            {"lon": result.longitude, "lat": result.latitude},
        )
    assert abs(x - 7505200) < 0.01


async def test_real_city_surface_patch_shape() -> None:
    assert TEST_DATABASE_URL
    database = create_database_resources(TEST_DATABASE_URL)
    area = (
        district()
        .replace(
            b"<gml:Polygon>", b'<gml:Surface srsName="EPSG:2178"><gml:patches><gml:PolygonPatch>'
        )
        .replace(b"</gml:Polygon>", b"</gml:PolygonPatch></gml:patches></gml:Surface>")
    )
    result = await MunicipalGeocoder(database.session_factory, Transport(area=area)).geocode(
        normalize_geocode_query(SOURCE)
    )
    assert result.longitude is not None
