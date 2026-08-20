"""Capture and compare redacted inventories for shared-edge cutover rehearsals."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

INVENTORY_SCHEMA = "wef-shared-edge-inventory@1"
WATCHED_LISTENER_PORTS = (22, 80, 443, 3000, 3100, 51820)
EDGE_PROJECT = "wef-shared-edge"
FORECAST_CONTAINER_PREFIX = "ai-forecast-production-"


class SharedEdgeInventoryError(RuntimeError):
    """Raised when inventory capture or comparison fails."""


def _run(*command: str) -> str:
    return subprocess.run(  # noqa: S603 - argv built from trusted literals
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _listeners() -> list[str]:
    ss = shutil.which("ss")
    if ss is None:
        msg = "ss is required to capture host listeners"
        raise SharedEdgeInventoryError(msg)
    watched: list[str] = []
    for line in _run(ss, "-H", "-lntu").splitlines():
        local = line.split()[3]
        if ":" not in local:
            continue
        port_text = local.rsplit(":", maxsplit=1)[-1]
        if port_text.isdigit() and int(port_text) in WATCHED_LISTENER_PORTS:
            watched.append(local)
    return sorted(set(watched))


def _compose_projects() -> list[dict[str, Any]]:
    payload = _run("docker", "compose", "ls", "--all", "--format", "json").strip()
    projects = cast("list[dict[str, Any]]", json.loads(payload or "[]"))
    return sorted(projects, key=lambda item: str(item.get("Name")))


def _containers() -> list[dict[str, Any]]:
    identifiers = _run("docker", "ps", "--all", "--quiet").split()
    if not identifiers:
        return []
    inspected = cast("list[dict[str, Any]]", json.loads(_run("docker", "inspect", *identifiers)))
    selected: list[dict[str, Any]] = []
    for item in inspected:
        state = item["State"]
        health = state.get("Health") or {}
        selected.append(
            {
                "health": health.get("Status"),
                "id": item["Id"],
                "image_id": item["Image"],
                "image_name": item["Config"]["Image"],
                "name": item["Name"].lstrip("/"),
                "ports": item["HostConfig"]["PortBindings"],
                "state": state["Status"],
            }
        )
    return sorted(selected, key=lambda item: str(item["name"]))


def _networks() -> list[dict[str, Any]]:
    payload = _run("docker", "network", "ls", "--format", "{{json .}}")
    networks: list[dict[str, Any]] = []
    for line in payload.splitlines():
        if not line.strip():
            continue
        item = cast("dict[str, Any]", json.loads(line))
        networks.append(
            {
                "driver": item.get("Driver"),
                "id": item.get("ID"),
                "name": item.get("Name"),
                "scope": item.get("Scope"),
            }
        )
    return sorted(networks, key=lambda item: str(item["name"]))


def capture_inventory() -> dict[str, Any]:
    """Capture one redacted server inventory snapshot."""
    return {
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "compose_projects": _compose_projects(),
        "containers": _containers(),
        "hostname": _run("hostname").strip(),
        "listeners": _listeners(),
        "networks": _networks(),
        "schema": INVENTORY_SCHEMA,
        "uid": _run("id", "-u").strip(),
    }


def load_inventory(path: Path) -> dict[str, Any]:
    """Load one inventory object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != INVENTORY_SCHEMA:
        msg = "inventory has an invalid schema"
        raise SharedEdgeInventoryError(msg)
    return cast("dict[str, Any]", payload)


def indexed(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Index a JSON object list by one stable string field."""
    return {str(item[key]): item for item in items}


def unrelated_projects(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return Compose projects outside the WEF and shared-edge namespaces."""
    projects = indexed(inventory["compose_projects"], "Name")
    return {
        name: value
        for name, value in projects.items()
        if name not in {EDGE_PROJECT, "wef-production", "wef-candidate"}
    }


def unrelated_containers(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return containers outside the WEF and shared-edge namespaces."""
    containers = indexed(inventory["containers"], "name")
    prefixes = ("wef-production-", "wef-candidate-", "wef-shared-edge-")
    return {
        name: value
        for name, value in containers.items()
        if not name.startswith(prefixes)
    }


def forecast_containers(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return AI Forecast containers for explicit drift checks."""
    containers = indexed(inventory["containers"], "name")
    return {
        name: value
        for name, value in containers.items()
        if name.startswith(FORECAST_CONTAINER_PREFIX)
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Reject drift in unrelated projects, containers, listeners, or Forecast state."""
    if before["hostname"] != after["hostname"] or before["uid"] != after["uid"]:
        msg = "inventory identity changed"
        raise SharedEdgeInventoryError(msg)
    if unrelated_projects(before) != unrelated_projects(after):
        msg = "an unrelated Compose project changed"
        raise SharedEdgeInventoryError(msg)
    if unrelated_containers(before) != unrelated_containers(after):
        msg = "an unrelated container changed"
        raise SharedEdgeInventoryError(msg)
    if before["listeners"] != after["listeners"]:
        msg = "a watched host listener changed"
        raise SharedEdgeInventoryError(msg)
    if forecast_containers(before) != forecast_containers(after):
        msg = "AI Forecast container state changed"
        raise SharedEdgeInventoryError(msg)


def main(argv: list[str] | None = None) -> int:
    """Capture or compare shared-edge inventories."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="Write one inventory snapshot.")
    capture_parser.add_argument("output", type=Path)

    compare_parser = subparsers.add_parser("compare", help="Compare two inventory snapshots.")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)

    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "capture":
            payload = capture_inventory()
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {arguments.output}")
            return 0
        load_inventory(arguments.before)
        load_inventory(arguments.after)
        compare(load_inventory(arguments.before), load_inventory(arguments.after))
    except (SharedEdgeInventoryError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"shared-edge inventory failed: {error}", file=sys.stderr)
        return 1
    print("Shared-edge inventory comparison passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
