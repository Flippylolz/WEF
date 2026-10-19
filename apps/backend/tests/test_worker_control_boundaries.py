"""Worker status credentials, supervised consumer state and archive drain cadence."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from tests.test_complete_import_integration import NOW
from tests.test_telegram_worker_ops import _EmptyFactory, _FakeStore
from wef_backend import telegram_worker_command as worker
from wef_backend import telegram_worker_status_command as status_command
from wef_backend.features.ingestion.application.raw_archive import ArchiveDrainResult
from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.application.telegram_progress import ChannelProgress
from wef_backend.features.ingestion.application.telegram_worker_liveness import WorkerRuntimeState
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path


@pytest.mark.parametrize("exists", [False, True])
async def test_status_reads_session_presence_without_serializing_secret(
    *, exists: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic-session"
    if exists:
        path.write_text("synthetic-private-session")
    engine = MagicMock(dispose=AsyncMock())
    monkeypatch.setattr("sqlalchemy.ext.asyncio.create_async_engine", lambda _url: engine)
    monkeypatch.setattr(
        "sqlalchemy.ext.asyncio.async_sessionmaker", lambda *_args, **_kwargs: _EmptyFactory()
    )
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.telegram_worker_status_store.SQLAlchemyTelegramWorkerStatusStore",
        lambda _factory: _FakeStore(),
    )
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.ingestion_progress_store.SQLAlchemyIngestionProgressStore.status",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.media_recovery_store.SQLAlchemyMediaRecoveryStore.status",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        status_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=1,
            telegram_api_hash=SecretStr("synthetic-hash"),
            telegram_session=None,
            telegram_session_path=path,
            telegram_runtime_health_path=tmp_path / "missing-health",
        ),
    )
    result = await status_command.run_status()
    assert result["session_ready"] is exists
    assert result["runtime_health"] == {"status": "unavailable"}
    assert "synthetic-private-session" not in json.dumps(result)
    engine.dispose.assert_awaited_once()


def test_status_cli_accepts_a_missing_reconciliation_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        status_command, "run_status", AsyncMock(return_value={"freshness": "unknown"})
    )
    status_command.main([])
    assert json.loads(capsys.readouterr().out) == {"freshness": "unknown"}


@pytest.mark.parametrize("mode", ["stopped", "new_commit", "older_commit", "empty"])
async def test_archive_drain_tracks_only_new_durable_commits_and_stops_at_cadence(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = asyncio.Event()
    state = WorkerRuntimeState(
        last_event_committed_at=NOW + timedelta(seconds=1) if mode == "older_commit" else None
    )
    if mode == "stopped":
        stop.set()
    result = ArchiveDrainResult(
        selected=0 if mode == "empty" else 1,
        newly_terminal=0 if mode == "empty" else 1,
        last_committed_at=NOW if mode != "empty" else None,
    )
    drainer = MagicMock(drain_once=AsyncMock(return_value=result))

    async def cadence(_seconds: float) -> None:
        stop.set()

    monkeypatch.setattr(asyncio, "sleep", cadence)
    lock = asyncio.Lock()
    await worker._maintain_raw_archive_drain(drainer, state, stop, "synthetic", lock)  # noqa: SLF001 - bounded worker loop
    assert drainer.drain_once.await_count == int(mode != "stopped")
    if mode == "new_commit":
        assert state.last_event_committed_at == NOW
    elif mode == "older_commit":
        assert state.last_event_committed_at == NOW + timedelta(seconds=1)
    else:
        assert state.last_event_committed_at is None


@pytest.mark.parametrize("cancelled", [False, True])
async def test_connected_consumer_updates_progress_and_cleans_up_cancellation(
    *, cancelled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A committed event publishes observed progress; cancelled consumers clear liveness."""
    event = LiveTelegramEvent(LiveTelegramEventKind.DELETE, deleted_ids=(1,))
    queue = MagicMock(
        get=AsyncMock(side_effect=asyncio.CancelledError() if cancelled else [event, None]),
        close=AsyncMock(),
    )
    state = WorkerRuntimeState()
    checkpoints = MagicMock(
        latest_live_checkpoint=AsyncMock(return_value=(3, None)),
        channel_progress=AsyncMock(
            return_value=ChannelProgress(
                polled_through_id=3, applied_high_water_id=4, history_limited=False
            )
        ),
    )
    processor = AsyncMock()
    monkeypatch.setattr(worker, "LiveEventQueue", lambda: queue)
    monkeypatch.setattr(worker, "WorkerRuntimeState", lambda **_kwargs: state)
    monkeypatch.setattr(worker, "LiveTelegramEventProcessor", lambda **_kwargs: processor)
    monkeypatch.setattr(
        worker, "build_media_recovery", lambda *_args, **_kwargs: SimpleNamespace(run=AsyncMock())
    )

    async def supervise(tasks: dict[str, Coroutine[Any, Any, None]], **_kwargs: object) -> None:
        for name, task in tasks.items():
            if name != "consumer":
                task.close()
        await tasks["consumer"]

    monkeypatch.setattr(worker, "supervise_worker_tasks", supervise)

    async def run() -> None:
        await worker._run_connected_worker(  # noqa: SLF001 - real supervised consumer composition
            settings=Settings(),
            identity=default_live_channel_identity(),
            client=MagicMock(),
            store=MagicMock(),
            archive=MagicMock(),
            checkpoint_store=checkpoints,
            session_factory=MagicMock(),
        )

    if cancelled:
        with pytest.raises(asyncio.CancelledError):
            await run()
        processor.assert_not_awaited()
    else:
        await run()
        assert state.local_checkpoint_external_id == 3
        assert state.applied_high_water_id == 4
        assert not state.history_limited
        assert state.last_event_received_at == event.received_at
        assert state.last_event_committed_at is not None
        processor.assert_awaited_once()
    assert not state.consumer_running
    queue.close.assert_awaited_once()
