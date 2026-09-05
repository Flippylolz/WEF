"""Cancellation, ownership loss and source acquisition do not block canonical work."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from telethon import types
from telethon.errors import FloodWaitError

from wef_backend.features.ingestion.application import media_recovery as runner_module
from wef_backend.features.ingestion.application.media_recovery import (
    MediaRecoveryOutcome,
    MediaRecoveryRunner,
    MediaSourceUnprovenError,
)
from wef_backend.features.ingestion.application.telegram_live import (
    live_message_to_raw,
    source_identity_from_channel,
)
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramWorkerSecrets
from wef_backend.features.ingestion.infrastructure import telethon_client as client_module
from wef_backend.features.ingestion.infrastructure.telethon_live_media import (
    LiveMediaDownloadLimits,
)

if TYPE_CHECKING:
    from pathlib import Path

    from wef_backend.features.ingestion.infrastructure.media_staging import StagedMedia


async def test_runner_continues_after_failure_and_finishes_later_item() -> None:
    store = AsyncMock()
    first, second = uuid4(), uuid4()
    store.claim.side_effect = [first, second, None]
    recover = AsyncMock(side_effect=[OSError("synthetic"), MediaRecoveryOutcome("completed")])
    assert await MediaRecoveryRunner(store, recover).run_once() == 1
    failure = store.fail.await_args.args[1]
    assert failure.kind == "deferred"
    store.finish.assert_awaited_once_with(second, MediaRecoveryOutcome("completed"))


async def test_runner_cancels_inflight_work_after_lease_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AsyncMock()
    store.claim.side_effect = [uuid4(), None]
    store.renew.return_value = False
    cleaned = asyncio.Event()

    async def recover(claim: object) -> MediaRecoveryOutcome:
        _ = claim
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return MediaRecoveryOutcome("completed")

    monkeypatch.setattr(runner_module, "LEASE_SECONDS", 0.003)
    assert await MediaRecoveryRunner(store, recover).run_once() == 0
    assert cleaned.is_set()
    store.finish.assert_not_awaited()


async def test_runner_shutdown_awaits_media_cleanup() -> None:
    store = AsyncMock()
    store.claim.return_value = uuid4()
    started, cleaned = asyncio.Event(), asyncio.Event()

    async def recover(claim: object) -> MediaRecoveryOutcome:
        _ = claim
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return MediaRecoveryOutcome("completed")

    task = asyncio.create_task(MediaRecoveryRunner(store, recover).run_once())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleaned.is_set()
    store.fail.assert_not_awaited()


def source_message(*, photo_id: int = 55) -> types.Message:
    return types.Message(
        id=7,
        peer_id=types.PeerChannel(int(default_live_channel_identity().channel_id)),
        date=datetime(2024, 1, 1, tzinfo=UTC),
        message="synthetic media",
        grouped_id=88,
        reply_to=types.MessageReplyHeader(reply_to_msg_id=3),
        media=types.MessageMediaPhoto(
            photo=types.Photo(
                id=photo_id,
                access_hash=0,
                file_reference=b"",
                date=datetime(2024, 1, 1, tzinfo=UTC),
                sizes=[],
                dc_id=1,
            )
        ),
    )


async def test_metadata_lands_without_downloading_and_acquisition_retains_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AsyncMock()
    monkeypatch.setattr(client_module, "StringSession", lambda _: object())
    monkeypatch.setattr(client_module, "TelegramClient", lambda *_args, **_kwargs: provider)
    client = client_module.TelethonLiveClient(
        TelegramWorkerSecrets(1, "hash", "session"),
        independent_media=True,
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(1024, 2),
    )
    message = source_message()
    live = await client.enrich_message(message)
    assert live.reply_to_message_id == 3
    assert live.media[0].path == "telegram/7/photo-55"
    assert live.media_lease is None
    provider.download_media.assert_not_awaited()
    raw = live_message_to_raw(
        live, identity=source_identity_from_channel(default_live_channel_identity())
    )
    provider.get_messages.return_value = message

    async def download(source: object, *, file: StagedMedia) -> None:
        _ = source
        file.write(b"synthetic")

    provider.download_media.side_effect = download
    descriptor, lease = await client.acquire_media(raw, 0)
    assert descriptor.path == "7/0.jpg"
    assert (tmp_path / descriptor.path).exists()
    lease.release()
    assert not (tmp_path / descriptor.path).exists()


@pytest.mark.parametrize("failure", ["changed", "deleted", "flood", "download"])
async def test_acquisition_defers_or_rejects_without_leaking_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    provider = AsyncMock()
    monkeypatch.setattr(client_module, "StringSession", lambda _: object())
    monkeypatch.setattr(client_module, "TelegramClient", lambda *_args, **_kwargs: provider)
    client = client_module.TelethonLiveClient(
        TelegramWorkerSecrets(1, "hash", "session"),
        independent_media=True,
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(1024, 2),
    )
    live = await client.enrich_message(source_message())
    raw = live_message_to_raw(
        live, identity=source_identity_from_channel(default_live_channel_identity())
    )
    provider.get_messages.return_value = (
        source_message(photo_id=99) if failure == "changed" else source_message()
    )
    expected: type[Exception] = MediaSourceUnprovenError
    if failure == "deleted":
        provider.get_messages.return_value = None
    elif failure == "flood":
        provider.get_messages.side_effect = FloodWaitError(request=None, capture=900)
        expected = OSError
    elif failure == "download":
        provider.download_media.side_effect = OSError("synthetic")
        expected = OSError
    with pytest.raises(expected):
        await client.acquire_media(raw, 0)
    assert not list(tmp_path.rglob("*.jpg"))  # noqa: ASYNC240 — bounded synthetic directory


async def test_systemic_discovery_failure_pauses_only_media() -> None:
    store = AsyncMock()
    store.discover.side_effect = ValueError("synthetic malformed recovery state")
    stop = asyncio.Event()

    async def pause(reason: str) -> None:
        assert reason == "ValueError"
        stop.set()

    store.pause.side_effect = pause
    await MediaRecoveryRunner(store, AsyncMock()).run(stop)
    store.pause.assert_awaited_once()
    store.claim.assert_not_awaited()


async def test_live_and_sweep_media_metadata_are_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AsyncMock()
    monkeypatch.setattr(client_module, "StringSession", lambda _: object())
    monkeypatch.setattr(client_module, "TelegramClient", lambda *_args, **_kwargs: provider)
    client = client_module.TelethonLiveClient(
        TelegramWorkerSecrets(1, "hash", "session"),
        independent_media=True,
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(1024, 2),
    )
    message = source_message()
    live = await client.enrich_message(message)
    provider.get_input_entity.return_value = types.InputPeerChannel(1, 0)
    provider.return_value = SimpleNamespace(messages=[message])
    observations = await client.observe_messages(username="synthetic", ids=[7])
    assert observations[0].message == live
    provider.download_media.assert_not_awaited()
