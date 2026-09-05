"""Fail-closed release ordering and guarded host-state reconciliation."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")


def snapshot(root: Path) -> dict[str, Any]:
    """Read source and digest identity only; reject unfinished or inconsistent activation."""
    if (root / "state/activation-pending.json").exists():
        msg = "unfinished activation requires health/state reconciliation before another release"
        raise ValueError(msg)
    path = root / "state/current.json"
    active = root / "releases/current"
    if not path.exists():
        if active.exists() or active.is_symlink():
            msg = "active release exists without durable current state"
            raise ValueError(msg)
        return {"release_sha": None, "images": {}}
    state = json.loads(path.read_text())
    sha = state.get("release_sha", "")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        msg = "current release SHA is invalid"
        raise ValueError(msg)
    expected = root / "releases" / sha
    if not active.is_symlink() or active.resolve() != expected.resolve():
        msg = "active release links and durable current state disagree"
        raise ValueError(msg)
    secret_dir = root / "secrets/releases" / sha
    active_secret = root / "secrets/current"
    if (
        Path(state.get("release_dir", "")).resolve() != expected.resolve()
        or Path(state.get("config_file", "")).resolve() != (secret_dir / "production.env").resolve()
        or not active_secret.is_symlink()
        or active_secret.resolve() != secret_dir.resolve()
    ):
        msg = "active configuration links and durable current state disagree"
        raise ValueError(msg)
    manifest = json.loads((expected / "release-manifest.json").read_text())
    if manifest.get("source_sha") != sha:
        msg = "current release manifest and state disagree"
        raise ValueError(msg)
    return {"release_sha": sha, "images": manifest.get("images", {})}


def ancestor(older: str, newer: str) -> bool:
    """Use source ancestry rather than commit timestamps or queue order."""
    git = shutil.which("git")
    if git is None or not SHA.fullmatch(older) or not SHA.fullmatch(newer):
        msg = "full source history is required for release ordering"
        raise ValueError(msg)
    result = subprocess.run([git, "merge-base", "--is-ancestor", older, newer], check=False)  # noqa: S603
    if result.returncode not in (0, 1):
        msg = "release ancestry could not be verified"
        raise ValueError(msg)
    return result.returncode == 0


def decide(current: dict[str, Any], manifest: dict[str, Any]) -> str:
    """Return activate, same, or superseded; inconsistent source/digest evidence fails closed."""
    candidate, live = manifest.get("source_sha"), current.get("release_sha")
    if not isinstance(candidate, str) or not SHA.fullmatch(candidate):
        msg = "candidate source identity is invalid"
        raise ValueError(msg)
    if live is None:
        return "activate"
    if not isinstance(live, str) or not SHA.fullmatch(live):
        msg = "current source identity is invalid"
        raise ValueError(msg)
    if live == candidate:
        if not manifest.get("images") or current.get("images") != manifest["images"]:
            msg = "already-current SHA has different image digests"
            raise ValueError(msg)
        return "same"
    if ancestor(candidate, live):
        return "superseded"
    if ancestor(live, candidate):
        return "activate"
    msg = "candidate and healthy release have unrelated ancestry"
    raise ValueError(msg)


def guard(root: Path, expected: str) -> None:
    """Compare state again while deploy.sh holds the host lock, before any migration."""
    observed = snapshot(root).get("release_sha") or "none"
    if observed != expected:
        msg = "healthy release changed after ordering; refuse activation"
        raise ValueError(msg)


def mark_pending(root: Path, sha: str) -> None:
    """Persist mutation uncertainty before migration so interrupted activation is explicit."""
    if not SHA.fullmatch(sha):
        msg = "pending source identity is invalid"
        raise ValueError(msg)
    path = root / "state/activation-pending.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({"release_sha": sha, "started_at": datetime.now(UTC).isoformat()}, stream)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    """Support a read-only SSH snapshot, local ancestry decision, and locked mutation guard."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("snapshot", "decide", "guard", "pending", "observation")
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    if args.command == "snapshot":
        # The caller's Actions lock covers the whole deployment; this also detects
        # a remote activation still running after a lost runner/SSH connection.
        with (args.path / "state/deploy.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = snapshot(args.path)
        print(json.dumps(payload))  # noqa: T201
    elif args.command == "decide":
        current = json.loads(args.path.read_text())
        manifest = json.loads(Path(args.value or "").read_text())
        print(decide(current, manifest))  # noqa: T201
    elif args.command == "guard":
        guard(args.path, args.value or "")
    elif args.command == "pending":
        mark_pending(args.path, args.value or "")
    elif args.command == "observation":
        sha = args.path.name
        if not SHA.fullmatch(sha) or args.value not in {"already_current", "superseded"}:
            parser.error("invalid no-op observation")
        now = datetime.now(UTC).isoformat()
        observation = {"release_sha": sha, f"{args.value}_at": now}
        if args.value == "already_current":
            observation["healthy_at"] = now
        print("observation=" + json.dumps(observation, separators=(",", ":")))  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
