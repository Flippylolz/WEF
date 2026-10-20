"""Validate the existing deployment smoke payloads without making requests."""

# Assertions are the existing operator smoke contracts, with nonzero failure exits.
# ruff: noqa: S101

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
WARSAW_DISTRICT_COUNT = 18
MAP_STYLE_VERSION = 8
INPUT_COUNTS = {
    "root": 3,
    "health": 2,
    "map": 2,
    "districts": 1,
    "offers": 2,
    "style": 1,
    "public-https": 2,
}


def validate_root(html: str, headers: str, release_sha: str) -> None:
    """Require the live product, reviewed inventory and exact release identity."""
    assert "Apartments and houses for sale in Warsaw" in html
    assert "reviewed historical inventory is live" in html
    assert f"version: <code>{release_sha[:7]}</code>" in html
    assert f"x-wef-release: {release_sha}".lower() in headers.lower()


def validate_health(live: object, ready: object) -> None:
    """Require the unchanged public liveness and readiness payloads."""
    assert live == {"status": "live"}
    assert ready == {"status": "ready"}


def selected_location(payload: dict[str, Any]) -> str:
    """Return the highest matching-offer group's validated location UUID."""
    assert payload["type"] == "FeatureCollection"
    assert payload["meta"]["feature_count"] >= 1
    assert len(payload["features"]) == payload["meta"]["feature_count"]
    ranked = sorted(
        payload["features"],
        key=lambda feature: int((feature.get("properties") or {}).get("matching_offer_count") or 0),
        reverse=True,
    )
    location_id = str(ranked[0].get("id") or "")
    assert UUID_PATTERN.fullmatch(location_id), location_id
    return location_id


def validate_districts(districts: dict[str, Any]) -> None:
    """Require all eighteen named polygon district features."""
    assert districts["type"] == "FeatureCollection"
    assert len(districts["features"]) == WARSAW_DISTRICT_COUNT
    assert all(
        feature["geometry"]["type"] in {"Polygon", "MultiPolygon"} and feature["properties"]["name"]
        for feature in districts["features"]
    )


def validate_offers(facets: dict[str, Any], offers: dict[str, Any], raw_offers: str) -> None:
    """Require usable facets/offer prices and refuse raw source-text exposure."""
    item = offers["items"][0]
    assert facets["districts"]
    assert facets["rooms"]
    assert offers["total_count"] >= 1
    assert offers["total_count"] >= offers["matching_count"]
    assert offers["items"]
    assert "id" in item
    assert "parking_price_min_minor" in item
    assert "storage_price_min_minor" in item
    assert "source_text" not in raw_offers


def validate_style(style: dict[str, Any]) -> None:
    """Require the unchanged MapLibre style schema and nonempty source/layers."""
    assert style["version"] == MAP_STYLE_VERSION
    assert style["sources"]
    assert style["layers"]


def validate_public_https(live: object, html: str) -> None:
    """Require the existing shared-edge liveness and product-root semantics."""
    assert live == {"status": "live"}
    assert "Apartments and houses for sale in Warsaw" in html


def read_json(path: str) -> dict[str, Any]:
    """Read one caller-owned temporary probe file without changing its JSON shape."""
    return cast("dict[str, Any]", json.loads(Path(path).read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    """Apply one existing smoke contract to its downloaded fixture files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", choices=INPUT_COUNTS)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args(argv)
    if len(args.inputs) != INPUT_COUNTS[args.contract]:
        parser.error(f"{args.contract} requires {INPUT_COUNTS[args.contract]} inputs")
    inputs = args.inputs
    if args.contract == "root":
        validate_root(
            Path(inputs[0]).read_text(encoding="utf-8"),
            Path(inputs[1]).read_text(encoding="utf-8"),
            inputs[2],
        )
    elif args.contract == "health":
        validate_health(read_json(inputs[0]), read_json(inputs[1]))
    elif args.contract == "map":
        Path(inputs[1]).write_text(selected_location(read_json(inputs[0])), encoding="utf-8")
    elif args.contract == "districts":
        validate_districts(read_json(inputs[0]))
    elif args.contract == "offers":
        validate_offers(
            read_json(inputs[0]), read_json(inputs[1]), Path(inputs[1]).read_text(encoding="utf-8")
        )
    elif args.contract == "style":
        validate_style(read_json(inputs[0]))
    else:
        validate_public_https(read_json(inputs[0]), Path(inputs[1]).read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
