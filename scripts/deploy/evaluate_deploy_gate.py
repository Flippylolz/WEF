"""Evaluate the main/origin/enable production deployment gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def automatic_deploy_allowed(
    *,
    event_name: str,
    ref: str,
    release_sha: str,
    auto_deploy_enabled: bool,
    associated_pull_requests: list[dict[str, Any]],
) -> bool:
    """Allow manual rehearsal or enabled merged-PR pushes to main only."""
    if event_name == "workflow_dispatch":
        return True
    if event_name != "push" or ref != "refs/heads/main" or not auto_deploy_enabled:
        return False
    return any(
        pull_request.get("state") == "closed"
        and pull_request.get("merged_at") is not None
        and pull_request.get("merge_commit_sha") == release_sha
        and isinstance(pull_request.get("base"), dict)
        and pull_request["base"].get("ref") == "main"
        for pull_request in associated_pull_requests
    )


def load_pull_requests(path: Path) -> list[dict[str, Any]]:
    """Load the bounded associated-PR API response."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        msg = "associated pull-request response is invalid"
        raise TypeError(msg)
    return cast("list[dict[str, Any]]", payload)


def main() -> int:
    """Print a GitHub-output-compatible lowercase boolean."""
    parser = argparse.ArgumentParser()
    parser.add_argument("event_name", choices=("push", "workflow_dispatch"))
    parser.add_argument("ref")
    parser.add_argument("release_sha")
    parser.add_argument("auto_deploy_enabled", choices=("true", "false"))
    parser.add_argument("associated_pull_requests", type=Path)
    arguments = parser.parse_args()
    allowed = automatic_deploy_allowed(
        event_name=arguments.event_name,
        ref=arguments.ref,
        release_sha=arguments.release_sha,
        auto_deploy_enabled=arguments.auto_deploy_enabled == "true",
        associated_pull_requests=load_pull_requests(arguments.associated_pull_requests),
    )
    print(str(allowed).lower())  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
