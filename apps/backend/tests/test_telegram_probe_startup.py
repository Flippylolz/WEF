"""Prove the production liveness entry point avoids the database import stack."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    WorkerRuntimeState,
    write_worker_heartbeat,
    write_worker_runtime_health,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import CriticalStageStatus

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("age_seconds", [0, 600])
def test_file_only_probe_never_imports_orm(tmp_path: Path, age_seconds: int) -> None:
    moment = datetime.now(UTC) - timedelta(seconds=age_seconds)
    heartbeat = tmp_path / "heartbeat"
    runtime = tmp_path / "runtime.json"
    write_worker_heartbeat(heartbeat, now=moment)
    write_worker_runtime_health(
        runtime,
        WorkerRuntimeState(
            transport_connected=True,
            consumer_running=True,
            reconciliation_status=CriticalStageStatus.RUNNING,
            last_reconciliation_at=moment,
        ).snapshot(now=moment),
    )
    script = """
import builtins
original = builtins.__import__
def checked(name, *args, **kwargs):
    if name == 'sqlalchemy' or name.startswith('sqlalchemy.'):
        raise AssertionError('file-only probe imported the ORM')
    return original(name, *args, **kwargs)
builtins.__import__ = checked
from wef_backend.telegram_worker_status_command import main
main(['--liveness'])
"""
    result = subprocess.run(  # noqa: S603 - fixed test script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "WEF_TELEGRAM_HEARTBEAT_PATH": str(heartbeat),
            "WEF_TELEGRAM_RUNTIME_HEALTH_PATH": str(runtime),
        },
        timeout=10,
    )
    assert result.returncode == (1 if age_seconds else 0), result.stderr
    assert result.stderr == ("Telegram worker liveness failed\n" if age_seconds else "")
