#!/bin/sh

set -eu

python3 - <<'PY'
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

WEF_ROOT = Path("/home/nuc/wef")
WEF_PATHS = (
    WEF_ROOT,
    WEF_ROOT / "releases",
    WEF_ROOT / "secrets",
    WEF_ROOT / "secrets/releases",
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


def run(*command: str) -> str:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def compose_projects() -> list[dict[str, object]]:
    payload = run("docker", "compose", "ls", "--all", "--format", "json").strip()
    return sorted(json.loads(payload or "[]"), key=lambda item: str(item.get("Name")))


def containers() -> list[dict[str, object]]:
    identifiers = run("docker", "ps", "--all", "--quiet").split()
    if not identifiers:
        return []
    inspected = json.loads(run("docker", "inspect", *identifiers))
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
    lines = run("ss", "-H", "-lntu").splitlines()
    watched = []
    for line in lines:
        fields = line.split()
        if len(fields) < 5:
            continue
        local = fields[4]
        if any(local.endswith(f":{port}") for port in WATCHED_PORTS):
            watched.append(" ".join((fields[0], local)))
    return sorted(watched)


def http_status(port: int) -> int | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            response.read(1)
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (OSError, TimeoutError):
        return None


def memory_available_kb() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable is absent")


def path_metadata() -> list[dict[str, object]]:
    entries = []
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


disk = shutil.disk_usage("/home/nuc")
payload = {
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
print(json.dumps(payload, sort_keys=True))
PY
