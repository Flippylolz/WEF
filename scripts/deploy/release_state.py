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
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
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
