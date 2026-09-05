"""Download Telegram channel media into worker-owned temporary files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from telethon.tl.types import (
    DocumentAttributeVideo,
    MessageMediaDocument,
    MessageMediaPhoto,
)

from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.infrastructure.media_staging import (
    MediaStagingDeferredError,
    StagedMedia,
)

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
    limits: LiveMediaDownloadLimits,
    lease: StagedMedia,
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
            message_id=message_id,
            ordinal=0,
            kind=MediaKind.PHOTO,
            mime_type="image/jpeg",
            suffix=".jpg",
            limits=limits,
            lease=lease,
        )
        return () if descriptor is None else (descriptor,)
    if isinstance(media, MessageMediaDocument):
        return await _download_document_media(
            client,
            message,
            media=media,
            message_id=message_id,
            limits=limits,
            lease=lease,
        )
    return ()


async def _download_document_media(  # noqa: PLR0913
    client: TelegramClient,
    message: object,
    *,
    media: MessageMediaDocument,
    message_id: int,
    limits: LiveMediaDownloadLimits,
    lease: StagedMedia,
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
        message_id=message_id,
        ordinal=0,
        kind=kind,
        mime_type=mime_type,
        suffix=suffix,
        limits=limits,
        lease=lease,
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
    message_id: int,
    ordinal: int,
    kind: MediaKind,
    mime_type: str,
    suffix: str,
    limits: LiveMediaDownloadLimits,
    lease: StagedMedia,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: int | None = None,
    size_bytes: int | None = None,
) -> MediaDescriptor | None:
    if size_bytes is not None and size_bytes > limits.max_bytes:
        return None
    try:
        target = lease.open(suffix)
        await asyncio.wait_for(
            client.download_media(message, file=target),
            timeout=limits.timeout_seconds,
        )
        lease.close()
    except (TimeoutError, OSError) as error:
        lease.release()
        message = "media acquisition deferred"
        raise MediaStagingDeferredError(message) from error
    except ValueError:
        lease.release()
        return None
    except BaseException:
        lease.release()
        raise
    if not lease.written:
        lease.release()
        return None
    relative = PurePosixPath(str(message_id)) / f"{ordinal}{suffix}"
    return MediaDescriptor(
        kind=kind,
        path=str(relative),
        mime_type=mime_type,
        size_bytes=lease.written,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )


def _suffix_for_mime(mime_type: str) -> str | None:
    for suffix, candidate in _IMAGE_MIME_BY_SUFFIX.items():
        if candidate == mime_type:
            return suffix
    return None
