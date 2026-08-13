"""Compare safe server inventories and reject non-WEF interference."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import json
from pathlib import Path
from typing import Any, cast

EXPECTED_WEF_PATHS = {
    "/home/nuc/wef": 0o750,
    "/home/nuc/wef/releases": 0o750,
    "/home/nuc/wef/secrets": 0o700,
    "/home/nuc/wef/secrets/releases": 0o700,
    "/home/nuc/wef/postgres": 0o700,
    "/home/nuc/wef/media": 0o750,
    "/home/nuc/wef/imports": 0o750,
    "/home/nuc/wef/imports/incoming": 0o750,
    "/home/nuc/wef/imports/extracted": 0o750,
    "/home/nuc/wef/caddy-data": 0o750,
    "/home/nuc/wef/state": 0o750,
    "/home/nuc/wef/logs": 0o750,
}


class InventoryMismatchError(RuntimeError):
    """Raised when provisioning changed a non-WEF resource."""


def load_inventory(path: Path) -> dict[str, Any]:
    """Load one inventory object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "wef-server-inventory@1":
        msg = "inventory has an invalid schema"
        raise InventoryMismatchError(msg)
    return cast("dict[str, Any]", payload)


def indexed(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Index a JSON object list by one stable string field."""
    return {str(item[key]): item for item in items}


def non_wef_projects(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return existing Compose projects outside the WEF namespace."""
    projects = indexed(inventory["compose_projects"], "Name")
    return {name: value for name, value in projects.items() if name != "wef-production"}


def non_wef_containers(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return existing containers outside the WEF namespace."""
    containers = indexed(inventory["containers"], "name")
    return {
        name: value for name, value in containers.items() if not name.startswith("wef-production-")
    }


def validate_expected_paths(inventory: dict[str, Any]) -> None:
    """Require exact WEF directory kinds, owner UID, and restrictive modes."""
    paths = indexed(inventory["wef_paths"], "path")
    if set(paths) != set(EXPECTED_WEF_PATHS):
        msg = "WEF path set is incomplete or unexpected"
        raise InventoryMismatchError(msg)
    for path, expected_mode in EXPECTED_WEF_PATHS.items():
        metadata = paths[path]
        if (
            metadata["kind"] != "directory"
            or metadata["mode"] != expected_mode
            or metadata["uid"] != inventory["uid"]
        ):
            msg = f"WEF path metadata is unsafe: {path}"
            raise InventoryMismatchError(msg)


def compare(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Reject changes to existing projects, containers, listeners, or health."""
    if before["hostname"] != after["hostname"] or before["uid"] != after["uid"]:
        msg = "inventory identity changed"
        raise InventoryMismatchError(msg)
    if non_wef_projects(before) != non_wef_projects(after):
        msg = "an existing Compose project changed"
        raise InventoryMismatchError(msg)
    if non_wef_containers(before) != non_wef_containers(after):
        msg = "an existing container changed"
        raise InventoryMismatchError(msg)
    if before["listeners"] != after["listeners"]:
        msg = "a watched host listener changed"
        raise InventoryMismatchError(msg)
    if before["existing_http"] != after["existing_http"]:
        msg = "an existing HTTP service changed"
        raise InventoryMismatchError(msg)
    validate_expected_paths(after)


def main() -> int:
    """Compare two inventory files and print one bounded result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    arguments = parser.parse_args()
    compare(load_inventory(arguments.before), load_inventory(arguments.after))
    print("Existing server projects, containers, listeners, and health are unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
