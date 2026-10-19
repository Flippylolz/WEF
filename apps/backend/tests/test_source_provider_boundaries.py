"""Bounded source parsing failures and municipal geometry fallback boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from xml.etree import ElementTree as ET

import ijson  # type: ignore[import-untyped]
import pytest

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_municipal_geocoder import GML, SOURCE, Transport, addresses, collection, street
from tests.test_telegram_export import EXPECTATION
from wef_backend.features.ingestion.application import (
    IncompleteScanError,
    SourceErrorCode,
    SourceScanError,
)
from wef_backend.features.ingestion.application.location_resolution import MunicipalUnavailableError
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.infrastructure.municipal_geocoder import (
    MunicipalGeocoder,
    _line,
    _polygon,
)
from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
    _HashingReader,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def test_hashing_reader_refuses_unbounded_reads_before_touching_source() -> None:
    source = BytesIO(b"synthetic")
    reader = _HashingReader(source)
    with pytest.raises(ValueError, match="unbounded source reads"):
        reader.read()
    assert source.tell() == 0
    assert reader.bytes_read == 0
    assert reader.read(1) == b"s"


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        '{"id":9001,"id":9001,"name":"Synthetic","type":"public_channel","messages":[]}',
        '{"id":true,"name":"Synthetic","type":"public_channel","messages":[]}',
        '{"id":"","name":"Synthetic","type":"public_channel","messages":[]}',
        '{"id":9001,"name":"","type":"public_channel","messages":[]}',
        '{"id":9001,"name":"Synthetic","type":"","messages":[]}',
    ],
)
def test_export_preflight_rejects_duplicate_or_invalid_top_level_identity(
    text: str, tmp_path: Path
) -> None:
    path = tmp_path / "source.json"
    path.write_text(text)
    with pytest.raises(SourceScanError) as caught:
        TelegramDesktopExportAdapter(path, EXPECTATION).open_scan()
    assert caught.value.code is SourceErrorCode.INVALID_TOP_LEVEL


def test_export_preflight_maps_generic_parser_errors_without_exposing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.json"
    path.write_text("{}")

    def failed(*_args: object, **_kwargs: object) -> Iterator[object]:
        message = "private source parser detail"
        raise ijson.JSONError(message)

    monkeypatch.setattr(ijson, "parse", failed)
    with pytest.raises(SourceScanError) as caught:
        TelegramDesktopExportAdapter(path, EXPECTATION).open_scan()
    assert caught.value.code is SourceErrorCode.INVALID_JSON
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("failure", ["parser", "read"])
def test_export_iteration_failure_closes_scan_without_terminal_summary(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.json"
    path.write_text(
        json.dumps(
            {"id": 9001, "name": EXPECTATION.channel_name, "type": "public_channel", "messages": []}
        )
    )
    scan = TelegramDesktopExportAdapter(path, EXPECTATION).open_scan()

    class FailingRecords:
        def __iter__(self) -> FailingRecords:
            return self

        def __next__(self) -> object:
            message = "private parser or source read body"
            if failure == "parser":
                raise ijson.JSONError(message)
            raise OSError(message)

    monkeypatch.setattr(ijson, "items", lambda *_args, **_kwargs: FailingRecords())
    with pytest.raises(SourceScanError) as caught:
        next(scan)
    assert caught.value.code is (
        SourceErrorCode.INVALID_JSON if failure == "parser" else SourceErrorCode.SOURCE_IO
    )
    assert "private" not in str(caught.value)
    assert not scan.is_complete
    with pytest.raises(IncompleteScanError):
        _ = scan.summary
    with pytest.raises(SourceScanError) as repeated:
        next(scan)
    assert repeated.value.code is SourceErrorCode.SCAN_ALREADY_STARTED


def test_municipal_empty_line_is_refused() -> None:
    with pytest.raises(ValueError, match="missing municipal line"):
        _line(ET.Element("row"))


@pytest.mark.parametrize("surface", [False, True])
def test_municipal_surface_requires_the_declared_projected_crs(*, surface: bool) -> None:
    row = ET.Element("row")
    parent = ET.SubElement(row, f"{{{GML}}}Surface", {"srsName": "EPSG:4326"}) if surface else row
    ET.SubElement(parent, f"{{{GML}}}PolygonPatch")
    with pytest.raises(ValueError, match="invalid municipal district CRS"):
        _polygon(row)


async def test_municipal_district_without_valid_centroid_returns_no_result() -> None:
    session = MagicMock(
        execute=AsyncMock(return_value=MagicMock(one_or_none=MagicMock(return_value=None)))
    )
    result = await MunicipalGeocoder(_factory(session), Transport()).geocode(
        normalize_geocode_query("Praga-Południe, Warszawa")
    )
    assert result.error_code is GeocodeErrorCode.NO_RESULT


async def test_municipal_partial_address_without_street_never_queries_transport() -> None:
    query = normalize_geocode_query(SOURCE)
    assert query.address is not None
    query = replace(query, address=replace(query.address, street=None, house_number="12"))
    transport = Transport()
    assert (
        await MunicipalGeocoder(MagicMock(), transport).geocode(query)
    ).error_code is GeocodeErrorCode.NO_RESULT
    assert transport.calls == []


async def test_municipal_unknown_district_set_is_ambiguous() -> None:
    transport = Transport(road=collection(street(district="Unknown")))
    result = await MunicipalGeocoder(MagicMock(), transport).geocode(
        normalize_geocode_query("ul. Syntetyczna, Warszawa")
    )
    assert dict(result.diagnostic)["candidate_ambiguity"] == "true"
    assert len(transport.calls) == 1


async def test_municipal_failed_projection_never_fabricates_a_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MunicipalGeocoder, "_project", AsyncMock(return_value=None))
    result = await MunicipalGeocoder(MagicMock(), Transport()).geocode(
        normalize_geocode_query(SOURCE)
    )
    assert result.error_code is GeocodeErrorCode.NO_RESULT
    assert result.longitude is result.latitude is None


@pytest.mark.parametrize(
    ("kind", "coordinates"),
    [("LineString", [7505350, 5788920]), ("Point", [7505350]), ("Point", [float("nan"), 5788920])],
)
async def test_municipal_address_geometry_requires_a_finite_point(
    kind: str, coordinates: list[float]
) -> None:
    data = json.loads(addresses())
    data["features"][0]["geometry"] = {"type": kind, "coordinates": coordinates}
    transport = Transport(address=json.dumps(data).encode())
    with pytest.raises(MunicipalUnavailableError):
        await MunicipalGeocoder(MagicMock(), transport).geocode(
            normalize_geocode_query(SOURCE.replace("Syntetyczna", "Syntetyczna 12"))
        )
