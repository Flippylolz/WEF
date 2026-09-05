"""Evaluate the main/origin/enable production deployment gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
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


def gate_outputs(
    *,
    event_name: str,
    ref: str,
    release_sha: str,
    auto_deploy_enabled: bool,
    associated_pull_requests: list[dict[str, Any]],
) -> dict[str, str]:
    """Explain the existing gate without changing its deployment authorization."""
    allowed = automatic_deploy_allowed(
        event_name=event_name,
        ref=ref,
        release_sha=release_sha,
        auto_deploy_enabled=auto_deploy_enabled,
        associated_pull_requests=associated_pull_requests,
    )
    reason = "missing_merged_pr"
    if event_name == "workflow_dispatch":
        reason = "manual_dispatch"
    elif event_name != "push" or ref != "refs/heads/main":
        reason = "not_main_push"
    elif not auto_deploy_enabled:
        reason = "auto_deploy_disabled"
    elif allowed:
        reason = "merged_pr"
    merged_at = ""
    for pr in associated_pull_requests:
        if (
            pr.get("state") == "closed"
            and pr.get("merge_commit_sha") == release_sha
            and isinstance(pr.get("base"), dict)
            and pr["base"].get("ref") == "main"
        ):
            value = pr.get("merged_at")
            if isinstance(value, str):
                try:
                    parsed = datetime.fromisoformat(value)
                    if parsed.tzinfo:
                        merged_at = parsed.isoformat()
                except ValueError:
                    pass
    return {
        "should_deploy": str(allowed).lower(),
        "gate_reason": reason,
        "merged_at": merged_at,
    }


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
    parser.add_argument("--outputs", action="store_true")
    arguments = parser.parse_args()
    outputs = gate_outputs(
        event_name=arguments.event_name,
        ref=arguments.ref,
        release_sha=arguments.release_sha,
        auto_deploy_enabled=arguments.auto_deploy_enabled == "true",
        associated_pull_requests=load_pull_requests(arguments.associated_pull_requests),
    )
    if arguments.outputs:
        for key, value in outputs.items():
            print(f"{key}={value}")  # noqa: T201
    else:
        print(outputs["should_deploy"])  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
