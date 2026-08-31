"""Unit tests for E8 live Telegram media download and processing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from telethon.tl.types import MessageMediaPhoto

from wef_backend.features.ingestion.application.live_media import LiveMediaPipeline
from wef_backend.features.ingestion.application.media_grouping import StatefulMediaGrouper
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    live_message_to_raw,
    source_identity_from_channel,
)
from wef_backend.features.ingestion.domain import SourceAnchor
from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.telethon_live_media import (
    LiveMediaDownloadLimits,
    download_live_message_media,
)
from wef_backend.telegram_media_wiring import build_live_media_pipeline, live_media_download_limits

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_download_live_message_media_writes_photo_descriptor(tmp_path: Path) -> None:
    message_id = 42
    target = tmp_path / str(message_id) / "0.jpg"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
    client = AsyncMock()
    client.download_media = AsyncMock(return_value=str(target))
    message = SimpleNamespace(id=message_id, media=MessageMediaPhoto(photo=SimpleNamespace()))

    descriptors = await download_live_message_media(
        client,
        message,
        temp_root=tmp_path,
        limits=LiveMediaDownloadLimits(max_bytes=1024, timeout_seconds=5.0),
    )
    assert len(descriptors) == 1
    assert descriptors[0].kind is MediaKind.PHOTO
    assert descriptors[0].path == f"{message_id}/0.jpg"
    assert descriptors[0].mime_type == "image/jpeg"


def test_live_message_to_raw_carries_media_descriptors() -> None:
    identity = source_identity_from_channel(default_live_channel_identity())
    published = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    message = LiveTelegramMessage(
        external_message_id=7,
        text="Cena: 4500 PLN, 2 pokoje, Mokotów",
        published_at=published,
        edited_at=None,
        media=(
            MediaDescriptor(
                kind=MediaKind.PHOTO,
                path="7/0.jpg",
                mime_type="image/jpeg",
                size_bytes=128,
            ),
        ),
    )
    raw = live_message_to_raw(message, identity=identity)
    assert raw.media[0].path == "7/0.jpg"
    assert raw.raw_payload["photo"] == "7/0.jpg"


def test_live_message_to_raw_carries_video_metadata() -> None:
    identity = source_identity_from_channel(default_live_channel_identity())
    message = LiveTelegramMessage(
        external_message_id=8,
        text="",
        published_at=datetime(2024, 1, 2, tzinfo=UTC),
        edited_at=None,
        media=(
            MediaDescriptor(
                kind=MediaKind.VIDEO,
                path="8/0.mp4",
                mime_type="video/mp4",
                duration_seconds=12,
            ),
        ),
    )
    raw = live_message_to_raw(message, identity=identity)
    assert raw.raw_payload["file"] == "8/0.mp4"
    assert raw.raw_payload["media_type"] == "video_file"


@pytest.mark.asyncio
async def test_live_media_pipeline_skips_messages_without_media() -> None:
    processor = AsyncMock()
    anchors = AsyncMock()
    anchors.source_anchors.return_value = {}
    anchors.existing_media_replays.return_value = set()
    pipeline = LiveMediaPipeline(
        processor=processor,
        anchors=anchors,
        grouper=StatefulMediaGrouper(),
    )
    identity = source_identity_from_channel(default_live_channel_identity())
    raw = live_message_to_raw(
        LiveTelegramMessage(
            external_message_id=1,
            text="no media",
            published_at=datetime(2024, 1, 1, tzinfo=UTC),
            edited_at=None,
        ),
        identity=identity,
    )
    processed = await pipeline.process_message(channel=identity, raw=raw)
    assert processed == 0
    processor.assert_not_called()


@pytest.mark.asyncio
async def test_download_live_message_media_rejects_invalid_message_id(tmp_path: Path) -> None:
    message = SimpleNamespace(
        id=0,
        media=MessageMediaPhoto(photo=SimpleNamespace()),
    )
    client = AsyncMock()
    descriptors = await download_live_message_media(
        client,
        message,
        temp_root=tmp_path,
        limits=LiveMediaDownloadLimits(max_bytes=1024, timeout_seconds=5.0),
    )
    assert descriptors == ()
    client.download_media.assert_not_called()


@pytest.mark.asyncio
async def test_download_live_message_media_skips_messages_without_media(tmp_path: Path) -> None:
    client = AsyncMock()
    descriptors = await download_live_message_media(
        client,
        SimpleNamespace(id=12, media=None),
        temp_root=tmp_path,
        limits=LiveMediaDownloadLimits(max_bytes=1024, timeout_seconds=5.0),
    )
    assert descriptors == ()
    client.download_media.assert_not_called()


@pytest.mark.asyncio
async def test_live_media_pipeline_processes_associated_media() -> None:
    processor = AsyncMock()
    processor.return_value = object()
    anchor_id = uuid4()
    revision_id = uuid4()
    offer_id = uuid4()
    anchors = AsyncMock()
    anchors.source_anchors.return_value = {
        9: SourceAnchor(
            source_message_id=anchor_id,
            revision_id=revision_id,
            offer_id=offer_id,
        ),
    }
    anchors.existing_media_replays.return_value = set()
    pipeline = LiveMediaPipeline(
        processor=processor,
        anchors=anchors,
        grouper=StatefulMediaGrouper(),
    )
    identity = source_identity_from_channel(default_live_channel_identity())
    message = LiveTelegramMessage(
        external_message_id=9,
        text="Cena: 4500 PLN, 2 pokoje, Mokotów ul. Puławska",
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        edited_at=None,
        media=(
            MediaDescriptor(
                kind=MediaKind.PHOTO,
                path="9/0.jpg",
                mime_type="image/jpeg",
            ),
        ),
    )
    raw = live_message_to_raw(message, identity=identity)
    processed = await pipeline.process_message(channel=identity, raw=raw)
    assert processed == 1
    processor.assert_awaited_once()


def test_build_live_media_pipeline_creates_processor(tmp_path: Path) -> None:
    pipeline = build_live_media_pipeline(
        session_factory=AsyncMock(),
        source_root=tmp_path / "source",
        originals_root=tmp_path / "originals",
        derivatives_root=tmp_path / "public",
        media_max_bytes=1024,
        media_max_pixels=1024,
        concurrency=1,
    )
    assert pipeline.concurrency == 1


def test_live_media_download_limits_factory() -> None:
    limits = live_media_download_limits(max_bytes=100, timeout_seconds=3.0)
    assert limits.max_bytes == 100
    assert limits.timeout_seconds == 3.0
