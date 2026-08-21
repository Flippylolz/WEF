"""Tests for Telegram worker ops freshness, reconciliation, and status CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Self
from uuid import uuid4

import pytest

from wef_backend import telegram_worker_command, telegram_worker_status_command
from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
    rotation_rehearsal_report,
)
from wef_backend.features.ingestion.domain.telegram_channel import TelegramWorkerSecretPaths
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramSecretError
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    FreshnessInput,
    ReconciliationStatus,
    WorkerFreshness,
    classify_freshness,
    production_activation_allowed,
    reconcile_checkpoints,
)
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.settings import Settings
from wef_backend.telegram_worker_command import main as worker_main
from wef_backend.telegram_worker_status_command import _serialize_status
from wef_backend.telegram_worker_status_command import (
    main as status_main,
)

if TYPE_CHECKING:
    from pathlib import Path


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


class _EmptyResult:
    def first(self) -> None:
        return None


class _EmptySession:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _stmt: object) -> None:
        return None

    async def execute(self, _stmt: object) -> _EmptyResult:
        return _EmptyResult()


class _EmptyFactory:
    def __call__(self) -> _EmptySession:
        return _EmptySession()


class _ChannelOnlyFactory:
    def __call__(self) -> _ChannelOnlySession:
        return _ChannelOnlySession()


class _ChannelOnlySession:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _stmt: object) -> object:
        return uuid4()

    async def execute(self, _stmt: object) -> _EmptyResult:
        return _EmptyResult()


class _LiveResult:
    def first(self) -> tuple[dict[str, int], datetime]:
        return {"last_source_index": 42}, datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


class _LiveSession:
    def __init__(self) -> None:
        self._scalar_calls = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _stmt: object) -> object:
        self._scalar_calls += 1
        if self._scalar_calls == 1:
            return uuid4()
        return 42

    async def execute(self, _stmt: object) -> _LiveResult:
        return _LiveResult()


class _LiveFactory:
    def __call__(self) -> _LiveSession:
        return _LiveSession()


class _InvalidCheckpointResult:
    def first(self) -> tuple[dict[str, object], datetime]:
        return {"last_source_index": "nope"}, datetime(2026, 8, 21, tzinfo=UTC)


class _InvalidCheckpointSession:
    def __init__(self) -> None:
        self._scalar_calls = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _stmt: object) -> object:
        self._scalar_calls += 1
        if self._scalar_calls == 1:
            return uuid4()
        return 42

    async def execute(self, _stmt: object) -> _InvalidCheckpointResult:
        return _InvalidCheckpointResult()


class _InvalidCheckpointFactory:
    def __call__(self) -> _InvalidCheckpointSession:
        return _InvalidCheckpointSession()


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
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=True,
                activation_enabled=True,
                last_committed_at=now,
                connected=False,
                now=now,
            ),
        )
        is WorkerFreshness.DISCONNECTED
    )
    assert (
        classify_freshness(
            FreshnessInput(
                secrets_ready=True,
                activation_enabled=True,
                last_committed_at=None,
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.NEVER_STARTED
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
    empty = reconcile_checkpoints(
        channel_id="2180077318",
        max_persisted_external_id=0,
        live_checkpoint_external_id=0,
    )
    assert empty.status is ReconciliationStatus.NO_SOURCE_DATA
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
async def test_build_status_marks_fresh_when_activated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_LIVE_LOOP", "1")
    finished = datetime(2026, 8, 21, 11, 55, tzinfo=UTC)
    status = await build_telegram_worker_status(
        _FakeStore(max_id=42, checkpoint=90, finished_at=finished),
        secret_paths=_secret_paths(tmp_path, ready=True),
        options=WorkerStatusOptions(
            activation_enabled=True,
            owner_gate_open=True,
            now=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ),
    )
    assert status.secrets_ready is True
    assert status.freshness is WorkerFreshness.FRESH
    assert status.live_loop_enabled is True
    assert status.reconciliation.status is ReconciliationStatus.LIVE_AHEAD_UNEXPLAINED
    assert status.production_activation_gate_open is True
    payload = _serialize_status(status)
    assert payload["last_live_run_finished_at"] == "2026-08-21T11:55:00Z"


def test_rotation_rehearsal_report_is_dry_run() -> None:
    report = rotation_rehearsal_report()
    assert report["mode"] == "dry_run"
    steps = report["steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 5


def test_worker_main_fails_closed_without_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEF_TELEGRAM_WORKER_ACTIVATE", raising=False)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_worker_main_fails_closed_on_secret_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_ACTIVATE", "1")

    async def _fail() -> None:
        message = "missing"
        raise TelegramSecretError(message)

    monkeypatch.setattr(telegram_worker_command, "_probe_authorized_session", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_worker_main_fails_closed_on_probe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_ACTIVATE", "1")

    async def _fail() -> None:
        message = "probe failed"
        raise RuntimeError(message)

    monkeypatch.setattr(telegram_worker_command, "_probe_authorized_session", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_worker_main_succeeds_when_loop_gated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_ACTIVATE", "1")
    monkeypatch.delenv("WEF_TELEGRAM_WORKER_LIVE_LOOP", raising=False)

    class _Client:
        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

        async def resolve_channel(self, username: str) -> object:
            assert username == "elestate_warszawa"
            return object()

    monkeypatch.setattr(
        telegram_worker_command,
        "load_telegram_worker_secrets",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(telegram_worker_command, "TelethonLiveClient", lambda _secrets: _Client())
    monkeypatch.setattr(telegram_worker_command, "verify_channel_entity", lambda *_args: None)
    monkeypatch.setattr(telegram_worker_command, "load_settings", Settings)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 0
    assert "continuous live loop remains gated" in capsys.readouterr().out


def test_worker_main_refuses_live_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_ACTIVATE", "1")
    monkeypatch.setenv("WEF_TELEGRAM_WORKER_LIVE_LOOP", "1")

    async def _ok() -> None:
        return None

    monkeypatch.setattr(telegram_worker_command, "_probe_authorized_session", _ok)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_status_rotation_dry_run_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    status_main(["--rotation-dry-run"])
    out = capsys.readouterr().out
    assert '"mode": "dry_run"' in out


def test_status_main_exits_on_unexplained_gap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _status(*, owner_gate_open: bool) -> dict[str, object]:
        _ = owner_gate_open
        return {"reconciliation": {"unexplained": True}}

    monkeypatch.setattr(telegram_worker_status_command, "run_status", _status)
    with pytest.raises(SystemExit) as exc:
        status_main(["--owner-gate-open"])
    assert exc.value.code == 3
    assert "unexplained" in capsys.readouterr().out


def test_status_main_exits_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _status(*, owner_gate_open: bool) -> dict[str, object]:
        _ = owner_gate_open
        message = "db down"
        raise RuntimeError(message)

    monkeypatch.setattr(telegram_worker_status_command, "run_status", _status)
    with pytest.raises(SystemExit) as exc:
        status_main([])
    assert exc.value.code == 2


@pytest.mark.asyncio
async def test_status_store_returns_zeros_without_channel() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_EmptyFactory())  # type: ignore[arg-type]
    assert await store.max_external_message_id(channel_external_id="2180077318") == 0
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint is None
    assert finished is None


@pytest.mark.asyncio
async def test_status_store_handles_channel_without_live_run() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_ChannelOnlyFactory())  # type: ignore[arg-type]
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint is None
    assert finished is None


@pytest.mark.asyncio
async def test_status_store_reads_checkpoint_and_max_id() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_LiveFactory())  # type: ignore[arg-type]
    assert await store.max_external_message_id(channel_external_id="2180077318") == 42
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint == 42
    assert finished is not None


@pytest.mark.asyncio
async def test_status_store_ignores_invalid_checkpoint() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_InvalidCheckpointFactory())  # type: ignore[arg-type]
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint is None
    assert finished is not None


@pytest.mark.asyncio
async def test_run_status_disposes_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed: list[str] = []

    class _Engine:
        async def dispose(self) -> None:
            disposed.append("yes")

    def _engine(_url: str) -> _Engine:
        return _Engine()

    def _factory(_engine: object, *, expire_on_commit: bool) -> _EmptyFactory:
        _ = expire_on_commit
        return _EmptyFactory()

    monkeypatch.setattr(telegram_worker_status_command, "create_async_engine", _engine)
    monkeypatch.setattr(telegram_worker_status_command, "async_sessionmaker", _factory)
    monkeypatch.setattr(
        telegram_worker_status_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id_file=tmp_path / "missing-id",
            telegram_api_hash_file=tmp_path / "missing-hash",
            telegram_session_file=tmp_path / "missing-session",
        ),
    )
    payload = await telegram_worker_status_command.run_status(owner_gate_open=False)
    assert disposed == ["yes"]
    assert payload["freshness"] == WorkerFreshness.SECRETS_PENDING.value
    assert payload["production_activation_gate_open"] is False
