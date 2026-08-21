"""Tests for Telegram worker ops freshness, reconciliation, and status CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
    rotation_rehearsal_report,
)
from wef_backend.features.ingestion.domain.telegram_channel import TelegramWorkerSecretPaths
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    FreshnessInput,
    ReconciliationStatus,
    WorkerFreshness,
    classify_freshness,
    production_activation_allowed,
    reconcile_checkpoints,
)
from wef_backend.telegram_worker_command import main as worker_main
from wef_backend.telegram_worker_status_command import main as status_main

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch


@dataclass
class _FakeStore:
    max_id: int = 0
    checkpoint: int | None = None
    finished_at: datetime | None = None

    async def max_external_message_id(self, *, channel_external_id: str) -> int:
        _ = channel_external_id
        return self.max_id

    async def latest_live_checkpoint(
        self,
        *,
        channel_external_id: str,
    ) -> tuple[int | None, datetime | None]:
        _ = channel_external_id
        return self.checkpoint, self.finished_at


def _secret_paths(tmp_path: Path, *, ready: bool) -> TelegramWorkerSecretPaths:
    paths = TelegramWorkerSecretPaths(
        api_id_file=tmp_path / "wef_telegram_api_id",
        api_hash_file=tmp_path / "wef_telegram_api_hash",
        session_file=tmp_path / "wef_telegram_session",
    )
    if ready:
        for path in paths.required_files():
            path.write_text("x", encoding="utf-8")
            path.chmod(0o600)
    return paths


def test_classify_freshness_and_reconciliation() -> None:
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=False,
                activation_enabled=True,
                last_committed_at=now,
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.SECRETS_PENDING
    )
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=True,
                activation_enabled=False,
                last_committed_at=now,
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.ACTIVATION_CLOSED
    )
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=True,
                activation_enabled=True,
                last_committed_at=now - timedelta(minutes=20),
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.STALE
    )
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=True,
                activation_enabled=True,
                last_committed_at=now - timedelta(minutes=5),
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.FRESH
    )
    aligned = reconcile_checkpoints(
        channel_id="2180077318",
        max_persisted_external_id=100,
        live_checkpoint_external_id=100,
    )
    assert aligned.status is ReconciliationStatus.ALIGNED
    assert not aligned.unexplained
    ahead = reconcile_checkpoints(
        channel_id="2180077318",
        max_persisted_external_id=50,
        live_checkpoint_external_id=100,
    )
    assert ahead.status is ReconciliationStatus.LIVE_AHEAD_UNEXPLAINED
    assert ahead.unexplained
    assert production_activation_allowed(secrets_ready=True, owner_gate_open=False) is False
    assert production_activation_allowed(secrets_ready=True, owner_gate_open=True) is True


@pytest.mark.asyncio
async def test_build_status_reports_secrets_pending(tmp_path: Path) -> None:
    status = await build_telegram_worker_status(
        _FakeStore(max_id=10, checkpoint=5, finished_at=datetime.now(UTC)),
        secret_paths=_secret_paths(tmp_path, ready=False),
        options=WorkerStatusOptions(activation_enabled=False, owner_gate_open=False),
    )
    assert status.freshness is WorkerFreshness.SECRETS_PENDING
    assert status.reconciliation.status is ReconciliationStatus.LIVE_BEHIND
    assert status.production_activation_gate_open is False
    assert status.compose_profile == "telegram-worker"


@pytest.mark.asyncio
async def test_build_status_marks_fresh_when_activated(tmp_path: Path) -> None:
    finished = datetime(2026, 8, 21, 11, 55, tzinfo=UTC)
    status = await build_telegram_worker_status(
        _FakeStore(max_id=42, checkpoint=42, finished_at=finished),
        secret_paths=_secret_paths(tmp_path, ready=True),
        options=WorkerStatusOptions(
            activation_enabled=True,
            owner_gate_open=True,
            now=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ),
    )
    assert status.secrets_ready is True
    assert status.freshness is WorkerFreshness.FRESH
    assert status.reconciliation.status is ReconciliationStatus.ALIGNED
    assert status.production_activation_gate_open is True


def test_rotation_rehearsal_report_is_dry_run() -> None:
    report = rotation_rehearsal_report()
    assert report["mode"] == "dry_run"
    steps = report["steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 5


def test_worker_main_fails_closed_without_activation(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("WEF_TELEGRAM_WORKER_ACTIVATE", raising=False)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_status_rotation_dry_run_prints_json(capsys: CaptureFixture[str]) -> None:
    status_main(["--rotation-dry-run"])
    out = capsys.readouterr().out
    assert '"mode": "dry_run"' in out
