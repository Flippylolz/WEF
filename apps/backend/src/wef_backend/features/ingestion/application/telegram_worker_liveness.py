"""Listen-loop heartbeat for telegram-worker Compose healthchecks."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    DEFAULT_HEARTBEAT_MAX_AGE,
    HEARTBEAT_INTERVAL_SECONDS,
    RUNTIME_HEALTH_SCHEMA_VERSION,
    CriticalStageStatus,
    WorkerRuntimeHealth,
    heartbeat_is_fresh,
    parse_heartbeat_timestamp,
    safe_error_category,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import timedelta
    from pathlib import Path


@dataclass(slots=True)
class WorkerRuntimeState:
    """Mutable event-loop-owned state used to publish redacted worker health."""

    transport_connected: bool = False
    consumer_running: bool = False
    reconciliation_status: CriticalStageStatus = CriticalStageStatus.PENDING_IMPLEMENTATION
    last_event_received_at: datetime | None = None
    last_event_committed_at: datetime | None = None
    last_reconciliation_at: datetime | None = None
    remote_head_external_id: int | None = None
    local_checkpoint_external_id: int | None = None
    last_error_category: str | None = None
    release_sha: str | None = None
    applied_high_water_id: int | None = None
    history_limited: bool = True

    def snapshot(self, *, now: datetime | None = None) -> WorkerRuntimeHealth:
        """Freeze current runtime state for one atomic diagnostic write."""
        return WorkerRuntimeHealth(
            schema_version=RUNTIME_HEALTH_SCHEMA_VERSION,
            applied_high_water_id=self.applied_high_water_id,
            history_limited=self.history_limited,
            written_at=(now or datetime.now(UTC)).astimezone(UTC),
            transport_connected=self.transport_connected,
            consumer_running=self.consumer_running,
            reconciliation_status=self.reconciliation_status,
            last_event_received_at=self.last_event_received_at,
            last_event_committed_at=self.last_event_committed_at,
            last_reconciliation_at=self.last_reconciliation_at,
            remote_head_external_id=self.remote_head_external_id,
            local_checkpoint_external_id=self.local_checkpoint_external_id,
            last_error_category=self.last_error_category,
            release_sha=(self.release_sha or "")[:12] or None,
        )

    def record_failure(self, error: BaseException) -> str:
        """Retain only the bounded exception category."""
        category = safe_error_category(error)
        self.last_error_category = category
        return category


def write_worker_heartbeat(path: Path, *, now: datetime | None = None) -> None:
    """Atomically write the current listen-loop timestamp."""
    current = (now or datetime.now(UTC)).astimezone(UTC)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(current.isoformat(), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def write_worker_runtime_health(path: Path, health: WorkerRuntimeHealth) -> None:
    """Atomically publish allowlisted runtime health fields."""
    payload = {
        "schema_version": health.schema_version,
        "applied_high_water_id": health.applied_high_water_id,
        "polled_through_id": health.local_checkpoint_external_id,
        "history_limited": health.history_limited,
        "written_at": _iso(health.written_at),
        "transport_connected": health.transport_connected,
        "consumer_running": health.consumer_running,
        "reconciliation_status": health.reconciliation_status.value,
        "last_event_received_at": _iso(health.last_event_received_at),
        "last_event_committed_at": _iso(health.last_event_committed_at),
        "last_reconciliation_at": _iso(health.last_reconciliation_at),
        "remote_head_external_id": health.remote_head_external_id,
        "local_checkpoint_external_id": health.local_checkpoint_external_id,
        "last_error_category": health.last_error_category,
        "release_sha": health.release_sha,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_worker_runtime_health(path: Path) -> WorkerRuntimeHealth:
    """Parse the versioned allowlisted health document or fail closed."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = "worker runtime health must be an object"
        raise TypeError(message)

    def timestamp(name: str) -> datetime | None:
        value = payload.get(name)
        if value is None:
            return None
        if not isinstance(value, str):
            message = f"{name} must be a timestamp"
            raise TypeError(message)
        return parse_heartbeat_timestamp(value)

    error_category = payload.get("last_error_category")
    release_sha = payload.get("release_sha")
    if error_category is not None and not isinstance(error_category, str):
        message = "last_error_category must be a string"
        raise ValueError(message)
    if release_sha is not None and not isinstance(release_sha, str):
        message = "release_sha must be a string"
        raise ValueError(message)

    def external_id(name: str) -> int | None:
        value = payload.get(name)
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            message = f"{name} must be a non-negative integer"
            raise ValueError(message)
        return value

    return WorkerRuntimeHealth(
        schema_version=int(payload.get("schema_version", 0)),
        applied_high_water_id=external_id("applied_high_water_id"),
        history_limited=payload.get("history_limited", True) is not False,
        written_at=timestamp("written_at") or datetime.min.replace(tzinfo=UTC),
        transport_connected=payload.get("transport_connected") is True,
        consumer_running=payload.get("consumer_running") is True,
        reconciliation_status=CriticalStageStatus(
            str(payload.get("reconciliation_status", CriticalStageStatus.FAILED.value)),
        ),
        last_event_received_at=timestamp("last_event_received_at"),
        last_event_committed_at=timestamp("last_event_committed_at"),
        last_reconciliation_at=timestamp("last_reconciliation_at"),
        remote_head_external_id=external_id("remote_head_external_id"),
        local_checkpoint_external_id=external_id("local_checkpoint_external_id"),
        last_error_category=error_category,
        release_sha=release_sha,
    )


def worker_liveness_ok(
    path: Path,
    *,
    runtime_health_path: Path | None = None,
    now: datetime | None = None,
    max_age: timedelta = DEFAULT_HEARTBEAT_MAX_AGE,
) -> bool:
    """Require the legacy heartbeat plus the critical-loop document when configured."""
    if not path.is_file():
        return False
    try:
        written = parse_heartbeat_timestamp(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    current = now or datetime.now(UTC)
    if not heartbeat_is_fresh(written, now=current, max_age=max_age):
        return False
    if runtime_health_path is None:
        return True
    try:
        runtime = read_worker_runtime_health(runtime_health_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return runtime.is_live(now=current, max_age=max_age)


async def maintain_worker_heartbeat(  # noqa: PLR0913
    path: Path,
    *,
    is_connected: Callable[[], bool],
    stop: asyncio.Event,
    state: WorkerRuntimeState | None = None,
    runtime_health_path: Path | None = None,
    interval: float = HEARTBEAT_INTERVAL_SECONDS,
) -> None:
    """Publish transport and critical-loop health; remove both files on stop."""
    runtime_state = state or WorkerRuntimeState()
    try:
        while not stop.is_set():
            connected = is_connected()
            runtime_state.transport_connected = connected
            try:
                if connected:
                    write_worker_heartbeat(path)
                if runtime_health_path is not None:
                    write_worker_runtime_health(runtime_health_path, runtime_state.snapshot())
            except OSError as error:
                runtime_state.record_failure(error)
                raise
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                continue
    finally:
        path.unlink(missing_ok=True)  # noqa: ASYNC240
        if runtime_health_path is not None:
            runtime_health_path.unlink(missing_ok=True)  # noqa: ASYNC240
