"""Synthetic payload contracts extracted from deployment shell probes."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from scripts.deploy import smoke_contracts as contracts

SHA = "a" * 40
FIRST = "10000000-0000-4000-8000-000000000001"
SELECTED = "10000000-0000-4000-8000-000000000002"
HTML = (
    "Apartments and houses for sale in Warsaw; "
    "reviewed historical inventory is live; "
    f"version: <code>{SHA[:7]}</code>"
)
HEADERS = f"HTTP/1.1 200 OK\nX-WEF-Release: {SHA}\n"


def map_fixture() -> dict[str, Any]:
    """Return three invented groups with a clear highest matching count."""
    return {
        "type": "FeatureCollection",
        "meta": {"feature_count": 3},
        "features": [
            {"id": FIRST, "properties": None},
            {"id": SELECTED, "properties": {"matching_offer_count": "4"}},
            {"id": FIRST, "properties": {"matching_offer_count": 0}},
        ],
    }


def districts_fixture() -> dict[str, Any]:
    """Return eighteen named synthetic geometries without source geography."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"type": "Polygon" if index % 2 else "MultiPolygon"},
                "properties": {"name": "Synthetic district"},
            }
            for index in range(18)
        ],
    }


def offers_fixture() -> dict[str, Any]:
    """Return public offer keys, including valid absent optional price values."""
    return {
        "total_count": 1,
        "matching_count": 1,
        "items": [{"id": FIRST, "parking_price_min_minor": None, "storage_price_min_minor": None}],
    }


class SmokeContractTests(unittest.TestCase):
    """All validation is in memory or temporary files; no request is made."""

    def test_root_requires_product_inventory_version_and_case_insensitive_release_header(
        self,
    ) -> None:
        contracts.validate_root(HTML, HEADERS, SHA)
        for html, headers in (
            (HTML.replace("Apartments and houses for sale in Warsaw", "wrong product"), HEADERS),
            (HTML.replace("reviewed historical inventory is live", "not live"), HEADERS),
            (HTML.replace(SHA[:7], "different"), HEADERS),
            (HTML, HEADERS.replace(SHA, "b" * 40)),
        ):
            with self.subTest(html=html, headers=headers), self.assertRaises(AssertionError):
                contracts.validate_root(html, headers, SHA)

    def test_health_and_public_origin_semantics_refuse_wrong_success_payloads(self) -> None:
        contracts.validate_health({"status": "live"}, {"status": "ready"})
        contracts.validate_public_https({"status": "live"}, HTML)
        for live, ready in (
            ({"status": "wrong"}, {"status": "ready"}),
            ({"status": "live"}, {"status": "wrong"}),
        ):
            with self.subTest(live=live, ready=ready), self.assertRaises(AssertionError):
                contracts.validate_health(live, ready)
        for live, html in (({}, HTML), ({"status": "live"}, "wrong product")):
            with self.subTest(live=live, html=html), self.assertRaises(AssertionError):
                contracts.validate_public_https(live, html)

    def test_map_selection_preserves_rank_fallbacks_and_refuses_invalid_evidence(self) -> None:
        self.assertEqual(contracts.selected_location(map_fixture()), SELECTED)
        for field, value in (
            ("type", "wrong"),
            ("meta", {"feature_count": 0}),
            ("meta", {"feature_count": 2}),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                contracts.selected_location({**map_fixture(), field: value})
        invalid = map_fixture()
        invalid["features"][1]["id"] = None
        with self.assertRaises(AssertionError):
            contracts.selected_location(invalid)
        invalid = map_fixture()
        invalid["features"][1]["properties"]["matching_offer_count"] = "invalid"
        with self.assertRaises(ValueError):
            contracts.selected_location(invalid)

    def test_district_count_type_polygon_and_name_contract(self) -> None:
        contracts.validate_districts(districts_fixture())
        value: object
        for field, value in (("type", "wrong"), ("features", [])):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                contracts.validate_districts({**districts_fixture(), field: value})
        for field, value in (("geometry", {"type": "LineString"}), ("properties", {"name": ""})):
            payload = districts_fixture()
            payload["features"][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                contracts.validate_districts(payload)

    def test_offer_facets_counts_public_keys_and_source_text_refusal(self) -> None:
        facets = {"districts": ["Synthetic district"], "rooms": [1]}
        offers = offers_fixture()
        contracts.validate_offers(facets, offers, json.dumps(offers))
        for name in ("districts", "rooms"):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                contracts.validate_offers({**facets, name: []}, offers, json.dumps(offers))
        for extra in ({"total_count": 0}, {"matching_count": 2}):
            payload = {**offers, **extra}
            with self.subTest(extra=extra), self.assertRaises(AssertionError):
                contracts.validate_offers(facets, payload, json.dumps(payload))
        for name in ("id", "parking_price_min_minor", "storage_price_min_minor"):
            payload = copy.deepcopy(offers)
            del payload["items"][0][name]
            with self.subTest(name=name), self.assertRaises(AssertionError):
                contracts.validate_offers(facets, payload, json.dumps(payload))
        payload = {**offers, "source_text": "synthetic source must never be public"}
        with self.assertRaises(AssertionError):
            contracts.validate_offers(facets, payload, json.dumps(payload))
        with self.assertRaises(IndexError):
            contracts.validate_offers(facets, {**offers, "items": []}, "{}")

    def test_style_version_and_nonempty_sources_and_layers(self) -> None:
        style = {"version": 8, "sources": {"synthetic": {}}, "layers": [{}]}
        contracts.validate_style(style)
        for key, value in (("version", 7), ("sources", {}), ("layers", [])):
            with self.subTest(key=key), self.assertRaises(AssertionError):
                contracts.validate_style({**style, key: value})

    def test_each_cli_contract_preserves_files_outputs_and_failure_exits(self) -> None:
        with TemporaryDirectory(prefix="wef smoke ") as temporary:
            root = Path(temporary)
            html, headers = root / "root fixture.html", root / "root headers.txt"
            html.write_text(HTML, encoding="utf-8")
            headers.write_text(HEADERS, encoding="utf-8")
            data = {
                "live": {"status": "live"},
                "ready": {"status": "ready"},
                "map": map_fixture(),
                "districts": districts_fixture(),
                "offers": offers_fixture(),
                "facets": {"districts": ["Synthetic district"], "rooms": [1]},
                "style": {"version": 8, "sources": {"synthetic": {}}, "layers": [{}]},
            }
            paths = {}
            for name, payload in data.items():
                paths[name] = str(root / f"{name}.json")
                Path(paths[name]).write_text(json.dumps(payload), encoding="utf-8")
            selected = root / "selected-location.txt"
            args_by_contract = {
                "root": [str(html), str(headers), SHA],
                "health": [paths["live"], paths["ready"]],
                "map": [paths["map"], str(selected)],
                "districts": [paths["districts"]],
                "offers": [paths["facets"], paths["offers"]],
                "style": [paths["style"]],
                "public-https": [paths["live"], str(html)],
            }
            for contract, args in args_by_contract.items():
                with self.subTest(contract=contract):
                    self.assertEqual(contracts.main([contract, *args]), 0)
            self.assertEqual(selected.read_text(), SELECTED)
            with (
                mock.patch("sys.stderr", new_callable=StringIO) as err,
                self.assertRaises(SystemExit) as result,
            ):
                contracts.main(["root", str(html)])
            self.assertEqual(result.exception.code, 2)
            self.assertIn("requires 3 inputs", err.getvalue())
            Path(paths["style"]).write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                contracts.main(["style", paths["style"]])
            child = subprocess.run(  # noqa: S603 - standalone helper and synthetic root inputs
                [sys.executable, str(contracts.__file__), "root", *args_by_contract["root"]],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout, "")
