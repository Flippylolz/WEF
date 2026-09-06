"""Sampling failures are deduplicated and never stop canonical worker stages."""

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from wef_backend import ingestion_progress_command as command
from wef_backend import ingestion_progress_worker as worker


async def test_monitor_emits_only_persisted_episode_transitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = asyncio.Event()
    events = [
        {"stage": "archive", "transition": "opened", "reason": "eligible_without_unique_progress"}
    ]

    async def sample() -> list[dict[str, str]]:
        stop.set()
        return events

    store = Mock(sample=AsyncMock(side_effect=sample))
    logger = Mock()
    monkeypatch.setattr(worker, "logger", logger)
    await worker.maintain_ingestion_progress(store, stop)
    logger.warning.assert_called_once_with("ingestion_progress_incident", **events[0])


async def test_monitor_outage_deduplicates_and_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    stop = asyncio.Event()
    store = Mock(
        sample=AsyncMock(side_effect=[OSError("private payload"), OSError("private payload"), []])
    )
    logger = Mock()
    monkeypatch.setattr(worker, "logger", logger)
    real_wait = asyncio.wait_for
    sleeps = 0

    async def wait(awaitable: Coroutine[Any, Any, object], *, timeout: int) -> object:  # noqa: ASYNC109 — mock wait_for contract
        nonlocal sleeps
        if timeout == 60:
            awaitable.close()
            sleeps += 1
            if sleeps == 3:
                stop.set()
            raise TimeoutError
        return await real_wait(awaitable, timeout=timeout)

    monkeypatch.setattr(asyncio, "wait_for", wait)
    await worker.maintain_ingestion_progress(store, stop)
    logger.error.assert_called_once_with(
        "ingestion_progress_sampling_unavailable", category="OSError"
    )
    logger.info.assert_called_once_with("ingestion_progress_sampling_recovered")


async def test_monitor_cancellation_propagates() -> None:
    store = Mock(sample=AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await worker.maintain_ingestion_progress(store, asyncio.Event())


@pytest.mark.parametrize("action", ["status", "enable", "disable"])
async def test_private_command_changes_only_monitor_control(
    action: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = Mock(dispose=AsyncMock())
    store = Mock(control=AsyncMock(), status=AsyncMock(return_value={"incidents": []}))
    monkeypatch.setattr(command, "load_settings", lambda: Mock(database_url="synthetic"))
    monkeypatch.setattr(command, "create_async_engine", lambda _: engine)
    monkeypatch.setattr(command, "SQLAlchemyIngestionProgressStore", lambda *_: store)
    assert await command.run(action) == {"incidents": []}
    if action == "status":
        store.control.assert_not_called()
    else:
        store.control.assert_awaited_once_with(enabled=action == "enable")
    engine.dispose.assert_awaited_once()


def test_private_command_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["ingestion-progress", "status"])
    monkeypatch.setattr(command, "run", AsyncMock(return_value={"incidents": []}))
    command.main()
    assert '"incidents": []' in capsys.readouterr().out
