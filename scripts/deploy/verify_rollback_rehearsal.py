"""Verify redacted server evidence after an application rollback rehearsal."""

from __future__ import annotations

# ruff: noqa: PLR2004, S101, T201
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from scripts.deploy.compare_server_inventory import compare, load_inventory
from scripts.deploy.release_state import read_failure_state, read_state

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_SERVICES = {"api", "db", "edge", "web"}


def read_manifest(root: Path, release_sha: str) -> dict[str, Any]:
    """Read and validate immutable release identity without exposing config."""
    path = root / "releases" / release_sha / "release-manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "release manifest is not an object"
        raise TypeError(msg)
    manifest = cast("dict[str, Any]", payload)
    assert manifest["schema"] == "wef-release@1"
    assert manifest["source_sha"] == release_sha
    assert isinstance(manifest["migration_revision"], str)
    datetime.fromisoformat(manifest["source_timestamp"])
    images = manifest["images"]
    assert isinstance(images, dict)
    assert DIGEST_PATTERN.fullmatch(images["backend"])
    assert DIGEST_PATTERN.fullmatch(images["web"])
    return manifest


def assert_runtime_inventory(after: dict[str, Any]) -> None:
    """Require the isolated WEF project and healthy bounded services."""
    projects = {str(project["Name"]): project for project in after["compose_projects"]}
    assert "wef-production" in projects
    containers = [
        container
        for container in after["containers"]
        if str(container["name"]).startswith("wef-production-")
    ]
    services = {
        str(container["name"]).removeprefix("wef-production-").rsplit("-", maxsplit=1)[0]
        for container in containers
    }
    assert REQUIRED_SERVICES.issubset(services)
    assert all(container["state"] == "running" for container in containers)
    assert all(container["health"] in {None, "healthy"} for container in containers)
    assert any(listener.endswith(":3100") for listener in after["listeners"])


def verify(
    root: Path,
    healthy_sha: str,
    failed_sha: str,
    before_path: Path,
    after_path: Path,
) -> None:
    """Verify state restoration, manifests, isolation, and persistent roots."""
    before = load_inventory(before_path)
    after = load_inventory(after_path)
    compare(before, after)
    assert_runtime_inventory(after)

    current = read_state(root / "state/current.json")
    previous = read_state(root / "state/previous.json")
    failure = read_failure_state(root / "state/last-failure.json")
    assert current["release_sha"] == healthy_sha
    assert previous["release_sha"] == healthy_sha
    assert failure["candidate_release_sha"] == failed_sha
    assert failure["failure_reason"] == "health_verification"
    assert failure["restored_release_sha"] == healthy_sha
    datetime.fromisoformat(failure["recorded_at"])

    healthy_dir = root / "releases" / healthy_sha
    healthy_config = root / "secrets/releases" / healthy_sha / "production.env"
    assert (root / "releases/current").resolve() == healthy_dir.resolve()
    assert (root / "secrets/current").resolve() == healthy_config.parent.resolve()
    assert healthy_config.stat().st_mode & 0o777 == 0o600
    assert read_manifest(root, healthy_sha)
    assert read_manifest(root, failed_sha)
    for directory in ("postgres", "media", "caddy-data"):
        assert (root / directory).is_dir()


def main() -> int:
    """Verify one redacted rehearsal evidence bundle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("healthy_sha")
    parser.add_argument("failed_sha")
    parser.add_argument("before_inventory", type=Path)
    parser.add_argument("after_inventory", type=Path)
    arguments = parser.parse_args()
    verify(
        arguments.root,
        arguments.healthy_sha,
        arguments.failed_sha,
        arguments.before_inventory,
        arguments.after_inventory,
    )
    print("Healthy release restoration and non-interference evidence pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
