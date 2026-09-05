"""Constrained storage, overlapping consumers and failed download regressions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from telethon.tl.types import MessageMediaPhoto

from wef_backend.features.ingestion.application.archive_retry import classify_archive_failure
from wef_backend.features.ingestion.application.telegram_live import live_message_payload
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramWorkerSecrets
from wef_backend.features.ingestion.infrastructure import telethon_client as telethon_module
from wef_backend.features.ingestion.infrastructure.media_staging import (
    MediaStaging,
    MediaStagingDeferredError,
    StagedMedia,
)
from wef_backend.features.ingestion.infrastructure.telethon_live_media import (
    LiveMediaDownloadLimits,
    download_live_message_media,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_staging_reserves_unwritten_bytes_and_protects_queued_files(tmp_path: Path) -> None:
    staging = MediaStaging(tmp_path, budget=100, reserve=0)
    first = staging.acquire(1, 60)
    first.open(".jpg").write(b"first")
    with pytest.raises(MediaStagingDeferredError):
        staging.acquire(2, 60)
    with pytest.raises(MediaStagingDeferredError):
        staging.acquire(1, 1)
    second = staging.acquire(2, 40)
    second.open(".jpg").write(b"second")
    first.release()
    first.release()
    assert (tmp_path / "2/0.jpg").read_bytes() == b"second"
    assert not (tmp_path / "1/0.jpg").exists()
    replacement = staging.acquire(1, 60)
    first.release()  # A stale release cannot clear the replacement's reservation.
    with pytest.raises(MediaStagingDeferredError):
        staging.acquire(3, 1)
    replacement.release()
    staging.close()
    assert not list(tmp_path.rglob("*.jpg"))


def test_staging_leaves_heartbeat_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.media_staging.shutil.disk_usage",
        lambda _: SimpleNamespace(free=100),
    )
    staging = MediaStaging(tmp_path, budget=100, reserve=20)
    first = staging.acquire(1, 60)
    with pytest.raises(MediaStagingDeferredError):
        staging.acquire(2, 30)
    first.release()
    with pytest.raises(MediaStagingDeferredError):
        staging.acquire(2, 81)


def test_staging_enforces_byte_limits_before_writes(tmp_path: Path) -> None:
    lease = MediaStaging(tmp_path, reserve=0).acquire(1, 5)
    lease.open(".jpg").write(b"1234")
    with pytest.raises(ValueError, match="download limit"):
        lease.write(b"56")
    assert (tmp_path / "1/0.jpg").read_bytes() == b"1234"
    assert lease.tell() == 4
    lease.release()


def test_staging_detects_external_capacity_pressure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease = MediaStaging(tmp_path, reserve=20).acquire(1, 100)
    lease.open(".jpg")
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.media_staging.shutil.disk_usage",
        lambda _: SimpleNamespace(free=22),
    )
    with pytest.raises(MediaStagingDeferredError):
        lease.write(b"123")
    assert lease.written == 0
    lease.release()


@pytest.mark.parametrize("symlink", [False, True])
def test_staging_never_replaces_unowned_files(tmp_path: Path, *, symlink: bool) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "0.jpg").write_bytes(b"protected")
    if symlink:
        (tmp_path / "1").symlink_to(outside, target_is_directory=True)
    else:
        (tmp_path / "1").mkdir()
        (tmp_path / "1/0.jpg").write_bytes(b"protected")
    lease = MediaStaging(tmp_path, reserve=0).acquire(1, 100)
    with pytest.raises(OSError, match=r"unavailable|File exists"):
        lease.open(".jpg")
    lease.release()
    assert (tmp_path / "1/0.jpg").read_bytes() == b"protected"
    assert (outside / "0.jpg").read_bytes() == b"protected"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "oserror", "cancel", "oversize"])
async def test_failed_download_releases_partial_file_and_reservation(
    tmp_path: Path,
    failure: str,
) -> None:
    staging = MediaStaging(tmp_path, budget=10, reserve=0)
    lease = staging.acquire(1, 10)

    async def download(message: object, *, file: StagedMedia) -> None:
        _ = message
        file.write(b"partial")
        if failure == "oversize":
            file.write(b"excess")
        if failure == "timeout":
            raise TimeoutError
        if failure == "oserror":
            raise OSError
        if failure == "cancel":
            raise asyncio.CancelledError

    client = AsyncMock()
    client.download_media.side_effect = download
    operation = download_live_message_media(
        client,
        SimpleNamespace(id=1, media=MessageMediaPhoto(photo=SimpleNamespace())),
        limits=LiveMediaDownloadLimits(max_bytes=10, timeout_seconds=1),
        lease=lease,
    )
    if failure == "oversize":
        assert await operation == ()
    elif failure == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await operation
    else:
        with pytest.raises(MediaStagingDeferredError) as caught:
            await operation
        assert classify_archive_failure(caught.value).kind == "deferred"
    assert not list(tmp_path.rglob("*.jpg"))  # noqa: ASYNC240 - bounded test fixture
    staging.acquire(1, 10).release()


@pytest.mark.asyncio
async def test_adapter_keeps_descriptor_identity_stable_across_owned_downloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = AsyncMock()

    async def download(message: object, *, file: StagedMedia) -> StagedMedia:
        _ = message
        file.write(b"photo")
        return file

    backend.download_media.side_effect = download
    monkeypatch.setattr(telethon_module, "TelegramClient", lambda *_args, **_kwargs: backend)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="session"),
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(max_bytes=10, timeout_seconds=1),
    )
    source = SimpleNamespace(
        id=1,
        date=datetime(2024, 1, 1, tzinfo=UTC),
        media=MessageMediaPhoto(photo=SimpleNamespace()),
    )
    first = await client.enrich_message(source)
    with pytest.raises(MediaStagingDeferredError):
        await client.enrich_message(source)
    assert first.media_lease is not None
    first.media_lease.release()
    second = await client.enrich_message(source)
    assert live_message_payload(first) == live_message_payload(second)
    assert second.media_lease is not None
    await client.disconnect()
    assert not list(tmp_path.rglob("*.jpg"))  # noqa: ASYNC240 - bounded fixture


@pytest.mark.asyncio
async def test_callback_waits_for_staging_owner_instead_of_failing_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = AsyncMock()

    async def download(message: object, *, file: StagedMedia) -> StagedMedia:
        _ = message
        file.write(b"photo")
        return file

    backend.download_media.side_effect = download
    monkeypatch.setattr(telethon_module, "TelegramClient", lambda *_args, **_kwargs: backend)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    sleep = AsyncMock()
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="session"),
        media_temp_root=tmp_path,
        media_limits=LiveMediaDownloadLimits(max_bytes=10, timeout_seconds=1),
        sleep=sleep,
    )
    source = SimpleNamespace(
        id=1,
        date=datetime(2024, 1, 1, tzinfo=UTC),
        media=MessageMediaPhoto(photo=SimpleNamespace()),
    )
    first = await client.enrich_message(source)
    assert first.media_lease is not None

    async def release(seconds: float) -> None:
        assert seconds == 5
        assert first.media_lease is not None
        first.media_lease.release()

    sleep.side_effect = release
    second = await client._enrich_callback(source)  # noqa: SLF001 - adapter backpressure boundary
    sleep.assert_awaited_once_with(5)
    assert second.media_lease is not None
    second.media_lease.release()
