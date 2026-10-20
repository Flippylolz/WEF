"""Capture the existing redacted production-host inventory contract."""

from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

WEF_ROOT = Path("/home/nuc/wef")
WEF_PATHS = (
    WEF_ROOT,
    WEF_ROOT / "releases",
    WEF_ROOT / "secrets",
    WEF_ROOT / "secrets/releases",
    WEF_ROOT / "secrets/telegram",
    WEF_ROOT / "postgres",
    WEF_ROOT / "media",
    WEF_ROOT / "media/originals",
    WEF_ROOT / "media/public",
    WEF_ROOT / "media/reports",
    WEF_ROOT / "imports",
    WEF_ROOT / "imports/incoming",
    WEF_ROOT / "imports/extracted",
    WEF_ROOT / "caddy-data",
    WEF_ROOT / "state",
    WEF_ROOT / "logs",
)
WATCHED_PORTS = (22, 3000, 8080, 3100, 51820)
MEMINFO_PATH = Path("/proc/meminfo")
LISTENER_ADDRESS_INDEX = 4


def run(*command: str) -> str:
    """Capture one fixed inventory command without shell interpolation."""
    return subprocess.run(  # noqa: S603 - collector builds fixed tool argv
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def compose_projects() -> list[dict[str, Any]]:
    """Return deterministically ordered Compose metadata."""
    payload = run("docker", "compose", "ls", "--all", "--format", "json").strip()
    projects = cast("list[dict[str, Any]]", json.loads(payload or "[]"))
    return sorted(projects, key=lambda item: str(item.get("Name")))


def containers() -> list[dict[str, Any]]:
    """Project only the existing source-free container inventory fields."""
    identifiers = run("docker", "ps", "--all", "--quiet").split()
    if not identifiers:
        return []
    inspected = cast("list[dict[str, Any]]", json.loads(run("docker", "inspect", *identifiers)))
    selected = []
    for item in inspected:
        state = item["State"]
        health = state.get("Health") or {}
        selected.append(
            {
                "id": item["Id"],
                "name": item["Name"].lstrip("/"),
                "image_id": item["Image"],
                "image_name": item["Config"]["Image"],
                "state": state["Status"],
                "health": health.get("Status"),
                "ports": item["HostConfig"]["PortBindings"],
            },
        )
    return sorted(selected, key=lambda item: str(item["name"]))


def listeners() -> list[str]:
    """Keep the existing protocol/address identities and duplicate socket counts."""
    lines = run("ss", "-H", "-lntu").splitlines()
    watched = []
    for line in lines:
        fields = line.split()
        if len(fields) <= LISTENER_ADDRESS_INDEX:
            continue
        local = fields[LISTENER_ADDRESS_INDEX]
        if any(local.endswith(f":{port}") for port in WATCHED_PORTS):
            watched.append(" ".join((fields[0], local)))
    return sorted(watched)


def http_status(port: int) -> int | None:
    """Read at most one byte from the two existing loopback service probes."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            response.read(1)
            return cast("int", response.status)
    except urllib.error.HTTPError as error:
        return error.code
    except (OSError, TimeoutError):
        return None


def memory_available_kb() -> int:
    """Read the existing MemAvailable aggregate or refuse missing evidence."""
    for line in MEMINFO_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    msg = "MemAvailable is absent"
    raise RuntimeError(msg)


def path_metadata() -> list[dict[str, object]]:
    """Report lstat metadata, preserving directory and dangling symlink identity."""
    entries: list[dict[str, object]] = []
    for path in WEF_PATHS:
        if not path.exists() and not path.is_symlink():
            continue
        metadata = path.lstat()
        entries.append(
            {
                "path": str(path),
                "kind": (
                    "symlink"
                    if stat.S_ISLNK(metadata.st_mode)
                    else "directory"
                    if stat.S_ISDIR(metadata.st_mode)
                    else "other"
                ),
                "mode": stat.S_IMODE(metadata.st_mode),
                "uid": metadata.st_uid,
                "gid": metadata.st_gid,
            },
        )
    return entries


def capture_inventory() -> dict[str, object]:
    """Build the unchanged wef-server-inventory@1 JSON projection."""
    disk = shutil.disk_usage("/home/nuc")
    return {
        "schema": "wef-server-inventory@1",
        "captured_at": datetime.now(UTC).isoformat(),
        "hostname": socket.gethostname(),
        "uid": os.getuid(),
        "compose_projects": compose_projects(),
        "containers": containers(),
        "listeners": listeners(),
        "existing_http": {"3000": http_status(3000), "8080": http_status(8080)},
        "resources": {
            "disk_free_bytes": disk.free,
            "memory_available_kb": memory_available_kb(),
        },
        "wef_paths": path_metadata(),
    }


def main() -> int:
    """Print the existing sorted JSON document without storing host information."""
    print(json.dumps(capture_inventory(), sort_keys=True))  # noqa: T201 - operator inventory output
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
