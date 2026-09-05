"""Record sanitized, run-specific deployment observations without changing release state."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# This module also runs directly from an immutable release on the production host.
try:
    from .release_state import write_json_state
except ImportError:
    from release_state import (  # type: ignore[no-redef,import-not-found]
        write_json_state,
    )

SHA = re.compile(r"^[0-9a-f]{40}$")
EVENTS = (
    "started",
    "healthy",
    "activated",
    "rollback_started",
    "restored",
    "rollback_failed",
    "already_current",
    "superseded",
)


def clean_observation(raw: dict[str, Any], release_sha: str) -> dict[str, Any]:
    """Allow only source identity and explicitly named timestamps into public reports."""
    if not SHA.fullmatch(release_sha) or raw.get("release_sha") != release_sha:
        return {}
    result: dict[str, Any] = {"release_sha": release_sha}
    for field in ("previous_sha", "restored_sha"):
        value = raw.get(field)
        result[field] = value if isinstance(value, str) and SHA.fullmatch(value) else None
    for event in EVENTS:
        value = raw.get(f"{event}_at")
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is not None:
                    result[f"{event}_at"] = parsed.astimezone(UTC).isoformat()
            except ValueError:
                pass
    return result


def record(path: Path, event: str, release_sha: str, current: Path) -> None:
    """Append a bounded event atomically, reading only the current SHA from private state."""
    if event not in EVENTS or not SHA.fullmatch(release_sha):
        msg = "invalid release observation identity or event"
        raise ValueError(msg)
    raw = json.loads(path.read_text()) if path.exists() and event != "started" else {}
    raw["release_sha"] = release_sha
    state = json.loads(current.read_text()) if current.exists() else {}
    if event == "started":
        raw["previous_sha"] = state.get("release_sha")
    if event == "restored":
        raw["restored_sha"] = state.get("release_sha")
    raw[f"{event}_at"] = datetime.now(UTC).isoformat()
    write_json_state(path, clean_observation(raw, release_sha))


def main() -> int:
    """Record or sanitize one observation; never export configuration paths or values."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=(*EVENTS, "export"))
    parser.add_argument("path", type=Path)
    parser.add_argument("release_sha")
    parser.add_argument("current", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command == "export":
        raw = json.loads(args.path.read_text())
        print(json.dumps(clean_observation(raw, args.release_sha), separators=(",", ":")))  # noqa: T201
    elif args.current is not None:
        record(args.path, args.command, args.release_sha, args.current)
    else:
        parser.error("recording requires current-state path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
