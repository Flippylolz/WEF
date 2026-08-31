"""Check production telegram-worker status for passive live events."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PassiveEventCheckError(RuntimeError):
    """Raised when worker status cannot be collected or parsed."""


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_EVENT_DETECTED = 2


@dataclass(frozen=True, slots=True)
class PassiveEventSnapshot:
    """Redacted worker fields needed for B-003 observation."""

    release_sha: str | None
    transport_connected: bool | None
    consumer_running: bool | None
    last_event_received_at: str | None
    last_event_committed_at: str | None
    remote_head_external_id: int | None
    max_persisted_external_id: int | None
    reconciliation_status: str | None

    @property
    def passive_event_observed(self) -> bool:
        """Return True when the worker recorded a passive queue event."""
        return self.last_event_received_at is not None


def _coerce_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def snapshot_from_status(payload: dict[str, Any]) -> PassiveEventSnapshot:
    """Build a redacted snapshot from wef-telegram-worker-status JSON."""
    runtime = payload.get("runtime_health")
    if not isinstance(runtime, dict):
        msg = "runtime_health missing from worker status"
        raise PassiveEventCheckError(msg)
    reconciliation = payload.get("reconciliation")
    reconciliation_status = None
    if isinstance(reconciliation, dict):
        status = reconciliation.get("status")
        if isinstance(status, str):
            reconciliation_status = status
    release_sha = runtime.get("release_sha")
    received = runtime.get("last_event_received_at")
    committed = runtime.get("last_event_committed_at")
    return PassiveEventSnapshot(
        release_sha=str(release_sha) if release_sha is not None else None,
        transport_connected=(
            runtime.get("transport_connected")
            if isinstance(runtime.get("transport_connected"), bool)
            else None
        ),
        consumer_running=(
            runtime.get("consumer_running")
            if isinstance(runtime.get("consumer_running"), bool)
            else None
        ),
        last_event_received_at=str(received) if received is not None else None,
        last_event_committed_at=str(committed) if committed is not None else None,
        remote_head_external_id=_coerce_int(runtime.get("remote_head_external_id")),
        max_persisted_external_id=_coerce_int(payload.get("max_persisted_external_id")),
        reconciliation_status=reconciliation_status,
    )


def load_status_json(raw: str) -> dict[str, Any]:
    """Parse worker status JSON."""
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        msg = "worker status must be a JSON object"
        raise PassiveEventCheckError(msg)
    return payload


def collect_worker_status(
    *,
    compose_project: str,
    worker_service: str,
) -> dict[str, Any]:
    """Run wef-telegram-worker-status inside the production worker container."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker executable not found on PATH"
        raise PassiveEventCheckError(msg)
    result = subprocess.run(  # noqa: S603 - absolute docker path with fixed argv
        [
            docker,
            "compose",
            "-p",
            compose_project,
            "exec",
            "-T",
            worker_service,
            "wef-telegram-worker-status",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        msg = f"worker status command failed ({result.returncode}): {detail}"
        raise PassiveEventCheckError(msg)
    return load_status_json(result.stdout)


def evaluate_snapshot(snapshot: PassiveEventSnapshot) -> int:
    """Return process exit code for one snapshot."""
    if snapshot.transport_connected is False or snapshot.consumer_running is False:
        return EXIT_ERROR
    if snapshot.passive_event_observed:
        return EXIT_EVENT_DETECTED
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """CLI entry for passive-event monitoring."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose-project",
        default="wef-production",
        help="Docker Compose project name (default: wef-production).",
    )
    parser.add_argument(
        "--worker-service",
        default="telegram-worker",
        help="Worker service name (default: telegram-worker).",
    )
    parser.add_argument(
        "--status-json",
        help="Use existing worker status JSON instead of running docker.",
    )
    arguments = parser.parse_args(argv)
    try:
        if arguments.status_json is not None:
            payload = load_status_json(Path(arguments.status_json).read_text(encoding="utf-8"))
        else:
            payload = collect_worker_status(
                compose_project=arguments.compose_project,
                worker_service=arguments.worker_service,
            )
        snapshot = snapshot_from_status(payload)
    except (PassiveEventCheckError, json.JSONDecodeError, OSError) as error:
        print(f"passive_event_check: {error}", file=sys.stderr)
        return EXIT_ERROR

    document = {
        "schema": "wef-telegram-passive-event-check@1",
        "release_sha": snapshot.release_sha,
        "transport_connected": snapshot.transport_connected,
        "consumer_running": snapshot.consumer_running,
        "last_event_received_at": snapshot.last_event_received_at,
        "last_event_committed_at": snapshot.last_event_committed_at,
        "remote_head_external_id": snapshot.remote_head_external_id,
        "max_persisted_external_id": snapshot.max_persisted_external_id,
        "reconciliation_status": snapshot.reconciliation_status,
        "passive_event_observed": snapshot.passive_event_observed,
    }
    print(json.dumps(document, sort_keys=True, indent=2))
    return evaluate_snapshot(snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
