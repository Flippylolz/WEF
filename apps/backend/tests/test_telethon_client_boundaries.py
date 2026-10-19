"""Offline live client observations, acquisition refusal and callback ownership."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon import types
from telethon.errors import FloodWaitError

from tests.test_media_recovery_runner import source_message
from wef_backend.features.ingestion.application.media_recovery import (
    MediaSourceUnprovenError,
    MediaUnsupportedError,
)
from wef_backend.features.ingestion.application.telegram_events import LiveEventQueue
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
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    transport = MagicMock()
    transport.get_entity = AsyncMock(
        return_value=SimpleNamespace(id=123, title="Synthetic", username=None)
    )
    transport.get_input_entity = AsyncMock(side_effect=FloodWaitError(request=None, capture=3))
    transport.get_messages = AsyncMock()
    transport.download_media = AsyncMock()
    monkeypatch.setattr(client_module, "StringSession", lambda _value: object())
    monkeypatch.setattr(client_module, "TelegramClient", lambda *_args, **_kwargs: transport)
    return transport


def _client(
    tmp_path: Path | None = None, *, independent: bool = False
) -> client_module.TelethonLiveClient:
    return client_module.TelethonLiveClient(
        TelegramWorkerSecrets(1, "synthetic-hash", "synthetic-session"),
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(64, 1),
        independent_media=independent,
    )


@pytest.mark.parametrize("mode", ["empty", "flood"])
async def test_head_observation_handles_empty_history_and_provider_deferral(
    mode: str, provider: MagicMock
) -> None:
    async def stream(*_args: object, **_kwargs: object) -> AsyncIterator[SimpleNamespace]:
        if mode == "flood":
            raise FloodWaitError(request=None, capture=2)
        items: tuple[SimpleNamespace, ...] = ()
        for item in items:
            yield item

    provider.iter_messages.side_effect = stream
    client = _client()
    if mode == "flood":
        with pytest.raises(client_module.TelegramSourceDeferredError) as caught:
            await client.latest_message_id("synthetic")
        assert caught.value.retry_after_seconds == 2
    else:
        assert await client.latest_message_id("synthetic") == 0
    resolved = await client.resolve_channel("synthetic")
    assert resolved.username == "synthetic"
    assert resolved.channel_id == "123"
    with pytest.raises(client_module.TelegramSourceDeferredError) as caught:
        await client.observe_messages(username="synthetic", ids=(1,))
    assert caught.value.retry_after_seconds == 3


@pytest.mark.parametrize("mode", ["no_media", "no_staging", "empty_download", "download_error"])
async def test_inline_enrichment_retains_metadata_on_absent_media_and_cleans_failed_downloads(
    mode: str, provider: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    message = source_message()
    if mode == "no_media":
        message.media = None
    elif mode == "no_staging":
        monkeypatch.setattr(client, "_staging", None)
    elif mode == "download_error":
        provider.download_media.side_effect = ValueError("synthetic download failure")
        # Acquisition rejects invalid bytes and releases its lease, preserving text.
    live = await client.enrich_message(message)
    assert live.text == "synthetic media"
    assert live.media == ()
    assert live.media_lease is None
    assert provider.download_media.await_count == (
        1 if mode in {"empty_download", "download_error"} else 0
    )
    assert not (tmp_path / "7/0.jpg").exists()


async def test_inline_enrichment_releases_lease_when_source_raises(
    provider: MagicMock, tmp_path: Path
) -> None:
    client = _client(tmp_path)
    provider.download_media.side_effect = RuntimeError("synthetic source failure")
    with pytest.raises(RuntimeError, match="synthetic source failure"):
        await client.enrich_message(source_message())
    provider.download_media.side_effect = None
    assert not (await client.enrich_message(source_message())).media


@pytest.mark.parametrize(
    "mode", ["no_staging", "ordinal", "unsupported", "oversize", "empty_download"]
)
async def test_independent_acquisition_refuses_unproven_or_unsupported_assets(
    mode: str, provider: MagicMock, tmp_path: Path
) -> None:
    client = _client(None if mode == "no_staging" else tmp_path, independent=True)
    message = source_message()
    if mode in {"unsupported", "oversize"}:
        message.media = types.MessageMediaDocument(
            document=types.Document(
                id=55,
                access_hash=0,
                file_reference=b"",
                date=message.date,
                mime_type="application/pdf" if mode == "unsupported" else "video/mp4",
                size=65 if mode == "oversize" else 2,
                dc_id=1,
                attributes=[],
            )
        )
    live = await client.enrich_message(message)
    raw = live_message_to_raw(
        live, identity=source_identity_from_channel(default_live_channel_identity())
    )
    provider.get_messages.return_value = message
    expected = (
        MediaUnsupportedError if mode in {"unsupported", "oversize"} else MediaSourceUnprovenError
    )
    with pytest.raises(expected):
        await client.acquire_media(raw, 1 if mode == "ordinal" else 0)
    assert not (tmp_path / "7/0.jpg").exists()
    assert provider.download_media.await_count == (1 if mode == "empty_download" else 0)


async def test_callback_queue_failure_releases_untransferred_lease_and_reports_safe_failure(
    provider: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    lease = MagicMock()
    live = await _client().enrich_message(source_message())
    monkeypatch.setattr(
        client, "enrich_message", AsyncMock(return_value=replace(live, media_lease=lease))
    )
    queue = MagicMock(spec=LiveEventQueue)
    queue.put = AsyncMock(side_effect=RuntimeError("private callback body"))
    queue.fail = AsyncMock()
    client.subscribe_channel("synthetic", queue)
    handlers = [call.args[0] for call in provider.add_event_handler.call_args_list]
    await handlers[0](SimpleNamespace(message=source_message()))
    lease.release.assert_called_once()
    queue.fail.assert_awaited_once()
    await handlers[2](SimpleNamespace(deleted_ids="invalid"))
    assert queue.fail.await_count == 2


async def test_legacy_flood_wait_uses_injected_nonnegative_delay(provider: MagicMock) -> None:
    del provider
    sleep = AsyncMock()
    client = client_module.TelethonLiveClient(
        TelegramWorkerSecrets(1, "synthetic", "synthetic"), sleep=sleep
    )
    await client._wait_flood(-5)  # noqa: SLF001 - retained bounded backoff helper
    sleep.assert_awaited_once_with(0)
