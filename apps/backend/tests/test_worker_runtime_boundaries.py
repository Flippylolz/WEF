"""Fail-closed worker diagnostics and supervised lifecycle boundaries."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from tests.test_complete_import import NOW
from tests.test_telegram_worker_ops import _FakeStore
from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    WorkerRuntimeState,
    maintain_worker_heartbeat,
    read_worker_runtime_health,
    worker_liveness_ok,
    write_worker_heartbeat,
)
from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
)
from wef_backend.features.ingestion.application.telegram_worker_supervision import (
    maintain_pending_reconciliation_slot,
    supervise_worker_tasks,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import RUNTIME_HEALTH_SCHEMA_VERSION

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("payload", [[], None])
def test_runtime_health_requires_a_json_object(tmp_path: Path, payload: object) -> None:
    path = tmp_path / "health.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(TypeError, match="worker runtime health must be an object"):
        read_worker_runtime_health(path)


@pytest.mark.parametrize(
    "name",
    ["written_at", "last_event_received_at", "last_event_committed_at", "last_reconciliation_at"],
)
def test_runtime_health_requires_timestamp_strings(tmp_path: Path, name: str) -> None:
    path = tmp_path / "health.json"
    payload: dict[str, object] = {
        "schema_version": RUNTIME_HEALTH_SCHEMA_VERSION,
        "written_at": NOW.isoformat(),
        name: 123,
    }
    path.write_text(json.dumps(payload))
    with pytest.raises(TypeError, match=name + " must be a timestamp"):
        read_worker_runtime_health(path)


@pytest.mark.parametrize("name", ["last_error_category", "release_sha"])
def test_runtime_health_refuses_nonstring_diagnostic_values(tmp_path: Path, name: str) -> None:
    path = tmp_path / "health.json"
    path.write_text(json.dumps({"schema_version": RUNTIME_HEALTH_SCHEMA_VERSION, name: 123}))
    with pytest.raises(ValueError, match=name + " must be a string"):
        read_worker_runtime_health(path)


@pytest.mark.parametrize(
    "name", ["applied_high_water_id", "remote_head_external_id", "local_checkpoint_external_id"]
)
@pytest.mark.parametrize("value", [-1, True, "7"])
def test_runtime_health_external_ids_are_nonnegative_integers(
    tmp_path: Path,
    name: str,
    value: object,
) -> None:
    path = tmp_path / "health.json"
    path.write_text(json.dumps({"schema_version": RUNTIME_HEALTH_SCHEMA_VERSION, name: value}))
    with pytest.raises(ValueError, match=name + " must be a non-negative integer"):
        read_worker_runtime_health(path)


@pytest.mark.parametrize("payload", [None, "{", "[]", "{}"])
def test_liveness_refuses_missing_or_invalid_runtime_health(
    tmp_path: Path, payload: str | None
) -> None:
    heartbeat, health = tmp_path / "heartbeat", tmp_path / "health.json"
    write_worker_heartbeat(heartbeat, now=NOW)
    if payload is not None:
        health.write_text(payload)
    assert not worker_liveness_ok(heartbeat, runtime_health_path=health, now=NOW)


async def test_heartbeat_write_failure_records_category_and_removes_stale_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heartbeat, health = tmp_path / "heartbeat", tmp_path / "health.json"
    heartbeat.write_text("stale heartbeat")
    health.write_text("stale health")
    state = WorkerRuntimeState()
    failure = OSError("synthetic private diagnostic")
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.telegram_worker_liveness.write_worker_heartbeat",
        Mock(side_effect=failure),
    )
    with pytest.raises(OSError, match="synthetic private diagnostic") as caught:
        await maintain_worker_heartbeat(
            heartbeat,
            is_connected=lambda: True,
            stop=asyncio.Event(),
            state=state,
            runtime_health_path=health,
        )
    assert caught.value is failure
    assert state.last_error_category == "OSError"
    assert not heartbeat.exists()
    assert not health.exists()


async def test_supervision_requires_a_critical_stage() -> None:
    stop = asyncio.Event()
    with pytest.raises(ValueError, match="at least one critical worker task is required"):
        await supervise_worker_tasks({}, stop=stop)
    assert not stop.is_set()


async def test_pending_reconciliation_slot_remains_running_until_shutdown() -> None:
    stop = asyncio.Event()
    pending = asyncio.create_task(maintain_pending_reconciliation_slot(stop))
    await asyncio.sleep(0)
    assert not pending.done()
    stop.set()
    await pending


async def test_status_explains_pending_session_after_credentials_are_ready() -> None:
    status = await build_telegram_worker_status(
        _FakeStore(finished_at=NOW),
        options=WorkerStatusOptions(credentials_ready=True, session_ready=False, now=NOW),
    )
    assert status.credentials_ready
    assert not status.session_ready
    assert any(note.startswith("String session will be generated") for note in status.notes)
