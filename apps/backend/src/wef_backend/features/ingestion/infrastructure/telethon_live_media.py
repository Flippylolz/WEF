"""Download Telegram channel media into worker-owned temporary files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from telethon.tl.types import (
    DocumentAttributeVideo,
    MessageMediaDocument,
    MessageMediaPhoto,
)

from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind

if TYPE_CHECKING:
    from telethon import TelegramClient

_IMAGE_MIME_BY_SUFFIX = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass(frozen=True, slots=True)
class LiveMediaDownloadLimits:
    """Bounded live media acquisition policy."""

    max_bytes: int
    timeout_seconds: float


async def download_live_message_media(
    client: TelegramClient,
    message: object,
    *,
    temp_root: Path,
    limits: LiveMediaDownloadLimits,
) -> tuple[MediaDescriptor, ...]:
    """Download supported media for one Telethon message into temp_root."""
    payload = cast("Any", message)
    media = getattr(payload, "media", None)
    if media is None:
        return ()
    message_id = int(getattr(payload, "id", 0) or 0)
    if message_id <= 0:
        return ()
    if isinstance(media, MessageMediaPhoto):
        descriptor = await _download_one(
            client,
            message,
            temp_root=temp_root,
            message_id=message_id,
            ordinal=0,
            kind=MediaKind.PHOTO,
            mime_type="image/jpeg",
            suffix=".jpg",
            limits=limits,
        )
        return () if descriptor is None else (descriptor,)
    if isinstance(media, MessageMediaDocument):
        return await _download_document_media(
            client,
            message,
            media=media,
            temp_root=temp_root,
            message_id=message_id,
            limits=limits,
        )
    return ()


async def _download_document_media(  # noqa: PLR0913
    client: TelegramClient,
    message: object,
    *,
    media: MessageMediaDocument,
    temp_root: Path,
    message_id: int,
    limits: LiveMediaDownloadLimits,
) -> tuple[MediaDescriptor, ...]:
    document = media.document
    mime_type = str(getattr(document, "mime_type", "") or "")
    if mime_type.startswith("video/"):
        kind = MediaKind.VIDEO
        suffix = ".mp4" if mime_type == "video/mp4" else ".bin"
    elif mime_type.startswith("image/"):
        kind = MediaKind.PHOTO
        suffix = _suffix_for_mime(mime_type) or ".jpg"
    else:
        return ()
    width = None
    height = None
    duration_seconds = None
    for attribute in getattr(document, "attributes", ()) or ():
        if isinstance(attribute, DocumentAttributeVideo):
            width = int(getattr(attribute, "w", 0) or 0) or None
            height = int(getattr(attribute, "h", 0) or 0) or None
            duration_seconds = int(getattr(attribute, "duration", 0) or 0) or None
    descriptor = await _download_one(
        client,
        message,
        temp_root=temp_root,
        message_id=message_id,
        ordinal=0,
        kind=kind,
        mime_type=mime_type,
        suffix=suffix,
        limits=limits,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        size_bytes=int(getattr(document, "size", 0) or 0) or None,
    )
    return () if descriptor is None else (descriptor,)


async def _download_one(  # noqa: PLR0913
    client: TelegramClient,
    message: object,
    *,
    temp_root: Path,
    message_id: int,
    ordinal: int,
    kind: MediaKind,
    mime_type: str,
    suffix: str,
    limits: LiveMediaDownloadLimits,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: int | None = None,
    size_bytes: int | None = None,
) -> MediaDescriptor | None:
    if size_bytes is not None and size_bytes > limits.max_bytes:
        return None
    target_dir = temp_root / str(message_id)
    target_path = target_dir / f"{ordinal}{suffix}"
    await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
    try:
        downloaded = await asyncio.wait_for(
            client.download_media(message, file=str(target_path)),
            timeout=limits.timeout_seconds,
        )
    except (TimeoutError, OSError, ValueError):
        return None
    if downloaded is None:
        await asyncio.to_thread(target_path.unlink, missing_ok=True)
        return None
    resolved = Path(str(downloaded))
    inspected = await asyncio.to_thread(_inspect_downloaded_file, resolved, limits.max_bytes)
    if inspected is None:
        return None
    byte_size, filename = inspected
    relative = PurePosixPath(str(message_id)) / filename
    return MediaDescriptor(
        kind=kind,
        path=str(relative),
        mime_type=mime_type,
        size_bytes=byte_size,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )


def _inspect_downloaded_file(path: Path, max_bytes: int) -> tuple[int, str] | None:
    """Validate one downloaded file size without blocking the event loop."""
    if not path.is_file():
        return None
    byte_size = path.stat().st_size
    if byte_size > max_bytes:
        path.unlink(missing_ok=True)
        return None
    return byte_size, path.name


def _suffix_for_mime(mime_type: str) -> str | None:
    for suffix, candidate in _IMAGE_MIME_BY_SUFFIX.items():
        if candidate == mime_type:
            return suffix
    return None
