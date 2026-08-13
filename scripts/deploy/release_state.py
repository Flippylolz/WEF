"""Read and atomically write bounded deployment release state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import TypedDict, cast


class ReleaseState(TypedDict):
    """Fields required to reactivate and verify one application release."""

    config_file: str
    public_port: int
    release_dir: str
    release_sha: str


class FailureState(TypedDict):
    """Non-secret evidence for the latest failed application candidate."""

    candidate_release_sha: str
    failure_reason: str
    recorded_at: str
    restored_release_sha: str | None


def read_state(path: Path) -> ReleaseState:
    """Read a state file and validate its primitive field types."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("config_file"), str)
        or not isinstance(raw.get("public_port"), int)
        or not isinstance(raw.get("release_dir"), str)
        or not isinstance(raw.get("release_sha"), str)
    ):
        msg = "release state has an invalid shape"
        raise TypeError(msg)
    return cast("ReleaseState", raw)


def write_state(path: Path, state: ReleaseState) -> None:
    """Write mode-0600 JSON and atomically replace the selected state."""
    write_json_state(path, state)


def write_json_state(path: Path, state: object) -> None:
    """Write one JSON state object through a mode-0600 atomic replacement."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_failure_state(path: Path) -> FailureState:
    """Read and validate bounded failed-candidate evidence."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    restored = raw.get("restored_release_sha") if isinstance(raw, dict) else False
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("candidate_release_sha"), str)
        or not isinstance(raw.get("failure_reason"), str)
        or not isinstance(raw.get("recorded_at"), str)
        or "restored_release_sha" not in raw
        or (restored is not None and not isinstance(restored, str))
    ):
        msg = "failure state has an invalid shape"
        raise TypeError(msg)
    return cast("FailureState", raw)


def activate_release_links(root: Path, release_dir: Path, config_file: Path) -> None:
    """Atomically point release and secret-current links at one verified release."""
    config_dir = config_file.parent
    if release_dir.parent != root / "releases":
        msg = "release link target is outside the release root"
        raise ValueError(msg)
    if config_dir.parent != root / "secrets/releases":
        msg = "secret link target is outside the secret release root"
        raise ValueError(msg)

    for link, target in (
        (root / "releases/current", release_dir),
        (root / "secrets/current", config_dir),
    ):
        temporary = link.with_name(f".{link.name}.{os.getpid()}.tmp")
        try:
            temporary.symlink_to(target, target_is_directory=True)
            temporary.replace(link)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    """Run the bounded state read/write command."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("path", type=Path)
    write_parser.add_argument("release_dir")
    write_parser.add_argument("config_file")
    write_parser.add_argument("release_sha")
    write_parser.add_argument("public_port", type=int)

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("path", type=Path)
    get_parser.add_argument(
        "field",
        choices=("release_dir", "config_file", "release_sha", "public_port"),
    )

    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("root", type=Path)
    activate_parser.add_argument("release_dir", type=Path)
    activate_parser.add_argument("config_file", type=Path)

    failure_parser = subparsers.add_parser("failure")
    failure_parser.add_argument("path", type=Path)
    failure_parser.add_argument("candidate_release_sha")
    failure_parser.add_argument("failure_reason", choices=("health_verification",))
    failure_parser.add_argument("recorded_at")
    failure_parser.add_argument("restored_release_sha", nargs="?")

    arguments = parser.parse_args()
    if arguments.command == "write":
        write_state(
            arguments.path,
            {
                "release_dir": arguments.release_dir,
                "config_file": arguments.config_file,
                "release_sha": arguments.release_sha,
                "public_port": arguments.public_port,
            },
        )
        return 0
    if arguments.command == "activate":
        activate_release_links(
            arguments.root,
            arguments.release_dir,
            arguments.config_file,
        )
        return 0
    if arguments.command == "failure":
        write_json_state(
            arguments.path,
            {
                "candidate_release_sha": arguments.candidate_release_sha,
                "failure_reason": arguments.failure_reason,
                "recorded_at": arguments.recorded_at,
                "restored_release_sha": arguments.restored_release_sha,
            },
        )
        return 0

    state = read_state(arguments.path)
    value: str | int
    if arguments.field == "release_dir":
        value = state["release_dir"]
    elif arguments.field == "config_file":
        value = state["config_file"]
    elif arguments.field == "release_sha":
        value = state["release_sha"]
    else:
        value = state["public_port"]
    print(value)  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
