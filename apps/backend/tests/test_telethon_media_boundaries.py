"""Offline Telethon media transport outcomes with real bounded staging files."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from telethon.tl.types import DocumentAttributeVideo, MessageMediaDocument, MessageMediaPhoto

from wef_backend.features.ingestion.domain.model import MediaKind
from wef_backend.features.ingestion.infrastructure.media_staging import (
    MediaStaging,
    MediaStagingDeferredError,
)
from wef_backend.features.ingestion.infrastructure.telethon_live_media import (
    LiveMediaDownloadLimits,
    download_live_message_media,
)

if TYPE_CHECKING:
    from pathlib import Path

    from wef_backend.features.ingestion.infrastructure.media_staging import StagedMedia


@pytest.mark.parametrize(
    ("mime", "suffix", "kind"),
    [
        ("video/mp4", ".mp4", MediaKind.VIDEO),
        ("video/unknown", ".bin", MediaKind.VIDEO),
        ("image/jpeg", ".jpeg", MediaKind.PHOTO),
        ("image/png", ".png", MediaKind.PHOTO),
        ("image/webp", ".webp", MediaKind.PHOTO),
        ("image/unknown", ".jpg", MediaKind.PHOTO),
    ],
)
async def test_document_media_preserves_bounded_metadata(
    mime: str, suffix: str, kind: MediaKind, tmp_path: Path
) -> None:
    """Known MIME families retain dimensions and use only controlled suffixes."""
    client = AsyncMock()

    async def download(_message: object, *, file: StagedMedia) -> None:
        file.write(b"synthetic-bytes")

    client.download_media.side_effect = download
    document = SimpleNamespace(
        mime_type=mime,
        size=15,
        attributes=[SimpleNamespace(), DocumentAttributeVideo(12, 640, 480)],
    )
    message = SimpleNamespace(id=42, media=MessageMediaDocument(document=document))
    staging = MediaStaging(tmp_path)
    lease = staging.acquire(42, 64)
    try:
        descriptors = await download_live_message_media(
            client, message, limits=LiveMediaDownloadLimits(64, 1), lease=lease
        )
        assert len(descriptors) == 1
        descriptor = descriptors[0]
        assert descriptor.path == f"42/0{suffix}"
        assert descriptor.kind is kind
        assert descriptor.size_bytes == 15
        assert (descriptor.width, descriptor.height, descriptor.duration_seconds) == (640, 480, 12)
        assert (tmp_path / descriptor.path).read_bytes() == b"synthetic-bytes"
        with pytest.raises(MediaStagingDeferredError):
            staging.acquire(42, 64)
    finally:
        lease.release()
    staging.acquire(42, 64).release()


@pytest.mark.parametrize(
    "mode", ["unknown_media", "unsupported_mime", "oversize", "empty", "zero_metadata"]
)
async def test_document_media_rejects_unsupported_or_unobserved_content(
    mode: str, tmp_path: Path
) -> None:
    """Unsupported documents and absent/oversized bytes cannot become usable assets."""
    client = AsyncMock()

    async def download(_message: object, *, file: StagedMedia) -> None:
        if mode == "zero_metadata":
            file.write(b"synthetic")

    client.download_media.side_effect = download
    document = SimpleNamespace(
        mime_type="application/pdf" if mode == "unsupported_mime" else "video/mp4",
        size=100 if mode == "oversize" else 0,
        attributes=None,
    )
    message = SimpleNamespace(
        id=42,
        media=object() if mode == "unknown_media" else MessageMediaDocument(document=document),
    )
    staging = MediaStaging(tmp_path)
    lease = staging.acquire(42, 64)
    try:
        descriptors = await download_live_message_media(
            client, message, limits=LiveMediaDownloadLimits(64, 1), lease=lease
        )
        if mode == "zero_metadata":
            assert len(descriptors) == 1
            assert (
                descriptors[0].width
                is descriptors[0].height
                is descriptors[0].duration_seconds
                is None
            )
            assert descriptors[0].size_bytes == 9
        else:
            assert descriptors == ()
        assert client.download_media.await_count == (1 if mode in {"empty", "zero_metadata"} else 0)
    finally:
        lease.release()
    staging.acquire(42, 64).release()


@pytest.mark.parametrize("failure", ["timeout", "filesystem", "overflow", "cancelled"])
async def test_download_failure_releases_owned_staging(failure: str, tmp_path: Path) -> None:
    """Every acquisition failure removes owned temporary files and releases capacity."""
    client = AsyncMock()

    async def download(_message: object, *, file: StagedMedia) -> None:
        file.write(b"prefix")
        if failure == "overflow":
            file.write(b"x" * 65)
        elif failure == "timeout":
            raise TimeoutError
        elif failure == "filesystem":
            raise OSError
        else:
            raise asyncio.CancelledError

    client.download_media.side_effect = download
    staging = MediaStaging(tmp_path)
    lease = staging.acquire(42, 64)
    message = SimpleNamespace(id=42, media=MessageMediaPhoto(photo=SimpleNamespace()))
    if failure == "overflow":
        assert (
            await download_live_message_media(
                client, message, limits=LiveMediaDownloadLimits(64, 1), lease=lease
            )
            == ()
        )
    else:
        expected = asyncio.CancelledError if failure == "cancelled" else MediaStagingDeferredError
        with pytest.raises(expected):
            await download_live_message_media(
                client, message, limits=LiveMediaDownloadLimits(64, 1), lease=lease
            )
    assert not (tmp_path / "42/0.jpg").exists()
    staging.acquire(42, 64).release()
