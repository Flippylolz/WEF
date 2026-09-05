"""Tests for Telegram worker ops freshness, reconciliation, and status CLI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self
from uuid import uuid4

import pytest

from wef_backend import telegram_worker_command, telegram_worker_status_command
from wef_backend.features.ingestion.application.telegram_progress import ChannelProgress
from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    WorkerRuntimeState,
    maintain_worker_heartbeat,
    read_worker_runtime_health,
    worker_liveness_ok,
    write_worker_heartbeat,
    write_worker_runtime_health,
)
from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
    rotation_rehearsal_report,
)
from wef_backend.features.ingestion.application.telegram_worker_supervision import (
    CriticalWorkerTaskError,
    supervise_worker_tasks,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramLoginCodeError,
    TelegramSecretError,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    DEFAULT_HEARTBEAT_MAX_AGE,
    CriticalStageStatus,
    FreshnessInput,
    ReconciliationStatus,
    WorkerFreshness,
    classify_freshness,
    heartbeat_is_fresh,
    parse_heartbeat_timestamp,
    reconcile_checkpoints,
    safe_error_category,
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

    async def channel_progress(self, *, channel_external_id: str) -> ChannelProgress:
        _ = channel_external_id
        return ChannelProgress(
            applied_high_water_id=self.max_id, polled_through_id=self.checkpoint or 0
        )

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
    async def get(self, *_args: object) -> None:
        return None

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
    async def get(self, *_args: object) -> object:
        return SimpleNamespace(
            applied_high_water_id=42,
            polled_through_id=42,
            history_limited=False,
            source_retry_at=None,
            last_applied_at=None,
            last_polled_at=datetime(2026, 8, 21, tzinfo=UTC),
            last_sweep_at=None,
        )

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
    async def get(self, *_args: object) -> None:
        return None

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


def test_classify_freshness_and_reconciliation() -> None:
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    assert (
        classify_freshness(
            FreshnessInput(
                credentials_ready=False,
                last_committed_at=now,
                connected=True,
                now=now,
            ),
        )
        is WorkerFreshness.CREDENTIALS_PENDING
    )
    assert (
        classify_freshness(
            FreshnessInput(
                credentials_ready=True,
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
                credentials_ready=True,
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
                credentials_ready=True,
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
                credentials_ready=True,
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


def test_heartbeat_freshness_and_parse() -> None:
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    written = parse_heartbeat_timestamp("2026-08-26T12:00:00+00:00")
    assert heartbeat_is_fresh(written, now=now, max_age=DEFAULT_HEARTBEAT_MAX_AGE)
    naive = parse_heartbeat_timestamp("2026-08-26T12:00:00")
    assert naive.tzinfo is not None
    stale = now - DEFAULT_HEARTBEAT_MAX_AGE - timedelta(seconds=1)
    assert not heartbeat_is_fresh(stale, now=now)
    with pytest.raises(ValueError, match="empty"):
        parse_heartbeat_timestamp("  ")


def test_worker_liveness_ok_requires_fresh_file(tmp_path: Path) -> None:
    path = tmp_path / "heartbeat"
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    assert worker_liveness_ok(path, now=now) is False
    write_worker_heartbeat(path, now=now)
    assert worker_liveness_ok(path, now=now) is True
    assert worker_liveness_ok(path, now=now + timedelta(minutes=2)) is False
    path.write_text("not-a-timestamp", encoding="utf-8")
    assert worker_liveness_ok(path, now=now) is False


def test_worker_liveness_requires_every_implemented_critical_loop(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    runtime_path = tmp_path / "health.json"
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    state = WorkerRuntimeState(
        transport_connected=True,
        consumer_running=True,
        release_sha="abcdef1234567890",
    )
    write_worker_heartbeat(heartbeat, now=now)
    write_worker_runtime_health(runtime_path, state.snapshot(now=now))
    assert worker_liveness_ok(
        heartbeat,
        runtime_health_path=runtime_path,
        now=now,
    )
    health = read_worker_runtime_health(runtime_path)
    assert health.release_sha == "abcdef123456"
    assert health.reconciliation_status is CriticalStageStatus.PENDING_IMPLEMENTATION

    state.consumer_running = False
    write_worker_runtime_health(runtime_path, state.snapshot(now=now))
    assert not worker_liveness_ok(
        heartbeat,
        runtime_health_path=runtime_path,
        now=now,
    )


def test_worker_liveness_requires_recent_completed_reconciliation(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    runtime_path = tmp_path / "health.json"
    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    state = WorkerRuntimeState(
        transport_connected=True,
        consumer_running=True,
        reconciliation_status=CriticalStageStatus.RUNNING,
        last_reconciliation_at=now,
        remote_head_external_id=29_257,
        local_checkpoint_external_id=29_257,
    )
    write_worker_heartbeat(heartbeat, now=now)
    write_worker_runtime_health(runtime_path, state.snapshot(now=now))
    assert worker_liveness_ok(heartbeat, runtime_health_path=runtime_path, now=now)

    health = read_worker_runtime_health(runtime_path)
    assert health.remote_head_external_id == 29_257
    assert health.local_checkpoint_external_id == 29_257
    assert not health.is_live(now=now + timedelta(minutes=4))
    state.consumer_running = True
    state.reconciliation_status = CriticalStageStatus.FAILED
    write_worker_runtime_health(runtime_path, state.snapshot(now=now))
    assert not worker_liveness_ok(
        heartbeat,
        runtime_health_path=runtime_path,
        now=now,
    )


def test_runtime_health_parser_fails_closed_on_bad_document(tmp_path: Path) -> None:
    runtime_path = tmp_path / "health.json"
    runtime_path.write_text('{"schema_version": 1, "consumer_running": true}', encoding="utf-8")
    health = read_worker_runtime_health(runtime_path)
    assert health.is_live(now=datetime.now(UTC)) is False
    runtime_path.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Expecting value"):
        read_worker_runtime_health(runtime_path)


def test_safe_error_category_never_renders_exception_message() -> None:
    error = RuntimeError("password=super-secret source listing text")
    assert safe_error_category(error) == "RuntimeError"
    assert "secret" not in safe_error_category(error)


@pytest.mark.asyncio
async def test_maintain_worker_heartbeat_writes_while_connected_then_unlinks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "heartbeat"
    stop = asyncio.Event()
    task = asyncio.create_task(
        maintain_worker_heartbeat(
            path,
            is_connected=lambda: True,
            stop=stop,
            interval=0.05,
        ),
    )
    for _ in range(40):
        if path.is_file():
            break
        await asyncio.sleep(0.025)
    assert worker_liveness_ok(path) is True
    stop.set()
    await task
    assert path.is_file() is False


@pytest.mark.asyncio
async def test_maintain_worker_heartbeat_publishes_and_removes_runtime_health(
    tmp_path: Path,
) -> None:
    heartbeat = tmp_path / "heartbeat"
    runtime_path = tmp_path / "health.json"
    stop = asyncio.Event()
    state = WorkerRuntimeState(transport_connected=True, consumer_running=True)
    task = asyncio.create_task(
        maintain_worker_heartbeat(
            heartbeat,
            is_connected=lambda: True,
            stop=stop,
            state=state,
            runtime_health_path=runtime_path,
            interval=0.05,
        ),
    )
    for _ in range(40):
        if runtime_path.is_file():
            break
        await asyncio.sleep(0.025)
    assert worker_liveness_ok(heartbeat, runtime_health_path=runtime_path)
    stop.set()
    await task
    assert not heartbeat.exists()
    assert not runtime_path.exists()


@pytest.mark.asyncio
async def test_supervisor_fails_fast_and_cancels_siblings() -> None:
    stop = asyncio.Event()
    sibling_cancelled = asyncio.Event()

    async def fail() -> None:
        message = "source text and password=secret must not escape"
        raise RuntimeError(message)

    async def linger() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            sibling_cancelled.set()

    with pytest.raises(CriticalWorkerTaskError) as captured:
        await supervise_worker_tasks(
            {"consumer": fail(), "transport": linger()},
            stop=stop,
        )
    assert captured.value.stage == "consumer"
    assert captured.value.category == "RuntimeError"
    assert "source text" not in str(captured.value)
    assert stop.is_set()
    assert sibling_cancelled.is_set()


@pytest.mark.asyncio
async def test_supervisor_treats_normal_critical_task_exit_as_failure() -> None:
    async def exits() -> None:
        return None

    stop = asyncio.Event()
    with pytest.raises(CriticalWorkerTaskError) as captured:
        await supervise_worker_tasks({"transport": exits()}, stop=stop)
    assert captured.value.category == "UnexpectedTaskExit"
    assert stop.is_set()


@pytest.mark.asyncio
async def test_maintain_worker_heartbeat_skips_write_while_disconnected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "heartbeat"
    stop = asyncio.Event()
    task = asyncio.create_task(
        maintain_worker_heartbeat(
            path,
            is_connected=lambda: False,
            stop=stop,
            interval=0.05,
        ),
    )
    await asyncio.sleep(0.08)
    stop.set()
    await task
    assert path.is_file() is False


def test_status_liveness_cli_exits_on_missing_heartbeat(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        telegram_worker_status_command,
        "load_settings",
        lambda: Settings(telegram_heartbeat_path=tmp_path / "missing"),
    )
    with pytest.raises(SystemExit) as exited:
        status_main(["--liveness"])
    assert exited.value.code == 1


def test_status_liveness_cli_succeeds_when_heartbeat_is_fresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "heartbeat"
    runtime_path = tmp_path / "health.json"
    write_worker_heartbeat(path)
    write_worker_runtime_health(
        runtime_path,
        WorkerRuntimeState(
            transport_connected=True,
            consumer_running=True,
        ).snapshot(),
    )
    monkeypatch.setattr(
        telegram_worker_status_command,
        "load_settings",
        lambda: Settings(
            telegram_heartbeat_path=path,
            telegram_runtime_health_path=runtime_path,
        ),
    )
    status_main(["--liveness"])


@pytest.mark.asyncio
async def test_build_status_reports_credentials_pending() -> None:
    status = await build_telegram_worker_status(
        _FakeStore(max_id=10, checkpoint=5, finished_at=datetime.now(UTC)),
        options=WorkerStatusOptions(credentials_ready=False, session_ready=False),
    )
    assert status.freshness is WorkerFreshness.CREDENTIALS_PENDING
    assert status.reconciliation.status is ReconciliationStatus.LIVE_BEHIND
    assert status.compose_service == "telegram-worker"


@pytest.mark.asyncio
async def test_build_status_marks_fresh_when_credentials_ready() -> None:
    finished = datetime(2026, 8, 21, 11, 55, tzinfo=UTC)
    status = await build_telegram_worker_status(
        _FakeStore(max_id=42, checkpoint=90, finished_at=finished),
        options=WorkerStatusOptions(
            credentials_ready=True,
            session_ready=True,
            now=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ),
    )
    assert status.credentials_ready is True
    assert status.freshness is WorkerFreshness.FRESH
    assert status.reconciliation.status is ReconciliationStatus.LIVE_AHEAD_UNEXPLAINED
    payload = _serialize_status(status)
    assert payload["last_live_run_finished_at"] == "2026-08-21T11:55:00Z"


def test_rotation_rehearsal_report_is_dry_run() -> None:
    report = rotation_rehearsal_report()
    assert report["mode"] == "dry_run"
    steps = report["steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 5


def test_worker_main_fails_closed_on_secret_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail() -> None:
        message = "missing"
        raise TelegramSecretError(message)

    monkeypatch.setattr(telegram_worker_command, "run_telegram_worker", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_worker_main_exits_when_login_code_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail() -> None:
        message = "login code sent"
        raise TelegramLoginCodeError(message)

    monkeypatch.setattr(telegram_worker_command, "run_telegram_worker", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 3


def test_worker_main_fails_closed_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail() -> None:
        message = "probe failed"
        raise RuntimeError(message)

    monkeypatch.setattr(telegram_worker_command, "run_telegram_worker", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2


def test_worker_main_exits_on_redacted_critical_stage_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fail() -> None:
        raise CriticalWorkerTaskError(stage="consumer", category="PersistenceBatchError")

    monkeypatch.setattr(telegram_worker_command, "run_telegram_worker", _fail)
    with pytest.raises(SystemExit) as exc:
        worker_main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "PersistenceBatchError" in captured.out
    assert "consumer" in captured.out
    assert "Telegram worker failed" in captured.err


def test_worker_main_succeeds_when_loop_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _ok() -> None:
        return None

    monkeypatch.setattr(telegram_worker_command, "run_telegram_worker", _ok)
    worker_main()


def test_status_rotation_dry_run_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    status_main(["--rotation-dry-run"])
    out = capsys.readouterr().out
    assert '"mode": "dry_run"' in out


def test_status_main_exits_on_unexplained_gap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _status() -> dict[str, object]:
        return {"reconciliation": {"unexplained": True}}

    monkeypatch.setattr(telegram_worker_status_command, "run_status", _status)
    with pytest.raises(SystemExit) as exc:
        status_main([])
    assert exc.value.code == 3
    assert "unexplained" in capsys.readouterr().out


def test_status_main_exits_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _status() -> dict[str, object]:
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
    assert checkpoint == 0
    assert finished is None


@pytest.mark.asyncio
async def test_status_store_handles_channel_without_live_run() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_ChannelOnlyFactory())  # type: ignore[arg-type]
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint == 0
    assert finished is None


@pytest.mark.asyncio
async def test_status_store_reads_checkpoint_and_max_id() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_LiveFactory())  # type: ignore[arg-type]
    assert await store.max_external_message_id(channel_external_id="2180077318") == 42
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint == 42
    assert finished is not None


@pytest.mark.asyncio
async def test_status_store_ignores_legacy_run_checkpoint() -> None:
    store = SQLAlchemyTelegramWorkerStatusStore(_InvalidCheckpointFactory())  # type: ignore[arg-type]
    checkpoint, finished = await store.latest_live_checkpoint(channel_external_id="2180077318")
    assert checkpoint == 0
    assert finished is None


@pytest.mark.asyncio
async def test_run_status_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    monkeypatch.setattr("sqlalchemy.ext.asyncio.create_async_engine", _engine)
    monkeypatch.setattr("sqlalchemy.ext.asyncio.async_sessionmaker", _factory)
    runtime_path = tmp_path / "worker-health.json"
    write_worker_runtime_health(
        runtime_path,
        WorkerRuntimeState(
            transport_connected=True,
            consumer_running=True,
            release_sha="abcdef1234567890",
        ).snapshot(now=datetime(2026, 8, 28, tzinfo=UTC)),
    )
    monkeypatch.setattr(
        telegram_worker_status_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=None,
            telegram_api_hash=None,
            telegram_runtime_health_path=runtime_path,
        ),
    )
    payload = await telegram_worker_status_command.run_status()
    assert disposed == ["yes"]
    assert payload["freshness"] == WorkerFreshness.CREDENTIALS_PENDING.value
    runtime_health = payload["runtime_health"]
    assert isinstance(runtime_health, dict)
    assert runtime_health["status"] == "available"
    assert runtime_health["consumer_running"] is True
    assert runtime_health["reconciliation_status"] == "pending_implementation"
    assert runtime_health["release_sha"] == "abcdef123456"


def test_runtime_health_status_reports_remote_gap(tmp_path: Path) -> None:
    runtime_path = tmp_path / "worker-health.json"
    write_worker_runtime_health(
        runtime_path,
        WorkerRuntimeState(
            transport_connected=True,
            consumer_running=True,
            reconciliation_status=CriticalStageStatus.RUNNING,
            last_reconciliation_at=datetime(2026, 8, 28, tzinfo=UTC),
            remote_head_external_id=29_257,
            local_checkpoint_external_id=29_202,
        ).snapshot(now=datetime(2026, 8, 28, tzinfo=UTC)),
    )
    payload = telegram_worker_status_command._serialize_runtime_health(runtime_path)  # noqa: SLF001
    assert payload["remote_head_external_id"] == 29_257
    assert payload["local_checkpoint_external_id"] == 29_202
    assert payload["remote_gap"] is True
