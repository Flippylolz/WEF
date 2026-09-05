"""Live Telegram client contract and entity verification for E8-T2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.domain.model import (
    MediaDescriptor,
    RawMessage,
    SourceIdentity,
    SourcePlatform,
    canonical_json_checksum,
    freeze_json,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from wef_backend.features.ingestion.application.telegram_progress import SourceObservation
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


class TelegramEntityMismatchError(RuntimeError):
    """Raised when the live entity does not match expected non-secret identity."""


@dataclass(frozen=True, slots=True)
class TelegramChannelEntity:
    """Resolved live channel identity (non-secret fields only)."""

    username: str
    channel_id: str
    title: str


class MediaLease(Protocol):
    """Ephemeral download ownership, excluded from archive payloads and checksums."""

    def release(self) -> None:
        """Release staging only after all consumers have finished."""
        ...


@dataclass(frozen=True, slots=True)
class LiveTelegramMessage:
    """Minimal live message surface before RawMessage conversion."""

    external_message_id: int
    text: str
    published_at: datetime
    edited_at: datetime | None
    media_group_id: str | None = None
    media: tuple[MediaDescriptor, ...] = ()
    media_lease: MediaLease | None = field(default=None, compare=False, repr=False)


class TelegramLiveClientPort(Protocol):
    """Inward-owned live Telegram client used by backfill (and later events)."""

    async def observe_messages(
        self, *, username: str, ids: Sequence[int]
    ) -> Sequence[SourceObservation]:
        """Observe at most 100 known IDs without downloading media; omission is unknown."""
        ...

    async def connect(self) -> None:
        """Establish a session connection."""
        ...

    async def disconnect(self) -> None:
        """Close the session connection."""
        ...

    async def resolve_channel(self, username: str) -> TelegramChannelEntity:
        """Resolve one public channel username to numeric ID and title."""
        ...

    async def latest_message_id(self, username: str) -> int:
        """Return the current remote channel head, or zero when empty."""
        ...

    def iter_messages(
        self,
        *,
        username: str,
        min_id: int,
        reverse: bool = True,
        limit: int | None = None,
    ) -> AsyncIterator[LiveTelegramMessage]:
        """Iterate channel messages for backfill (oldest-first when reverse=True)."""
        ...


def verify_channel_entity(
    expected: TelegramChannelIdentity,
    actual: TelegramChannelEntity,
) -> None:
    """Fail closed when live entity disagrees with configured identity."""
    if actual.username.casefold() != expected.username.casefold():
        message = "Telegram channel username does not match expected identity"
        raise TelegramEntityMismatchError(message)
    if actual.channel_id != expected.channel_id:
        message = "Telegram channel id does not match expected identity"
        raise TelegramEntityMismatchError(message)
    if actual.title != expected.channel_title:
        message = "Telegram channel title does not match expected identity"
        raise TelegramEntityMismatchError(message)


def live_message_payload(message: LiveTelegramMessage) -> dict[str, object]:
    """Build the canonical verbatim payload shared by landing and conversion."""
    payload: dict[str, object] = {
        "id": message.external_message_id,
        "type": "message",
        "date_unixtime": str(int(message.published_at.timestamp())),
        "text": message.text,
        "from_live": True,
    }
    if message.edited_at is not None:
        payload["edited_unixtime"] = str(int(message.edited_at.timestamp()))
    if message.media_group_id is not None:
        payload["media_group_id"] = message.media_group_id
    if message.media:
        _apply_primary_media_fields(payload, message.media[0])
    return payload


def _apply_primary_media_fields(payload: dict[str, object], descriptor: MediaDescriptor) -> None:
    """Mirror historical export media keys for the first live descriptor."""
    if descriptor.kind.value == "photo":
        payload["photo"] = descriptor.path
    elif descriptor.kind.value in {"video", "file"}:
        payload["file"] = descriptor.path
        payload["media_type"] = "video_file" if descriptor.kind.value == "video" else "file"
    if descriptor.mime_type is not None:
        payload["mime_type"] = descriptor.mime_type
    if descriptor.size_bytes is not None:
        payload["file_size"] = descriptor.size_bytes
    if descriptor.width is not None:
        payload["width"] = descriptor.width
    if descriptor.height is not None:
        payload["height"] = descriptor.height
    if descriptor.duration_seconds is not None:
        payload["duration_seconds"] = descriptor.duration_seconds


def live_message_to_raw(
    message: LiveTelegramMessage,
    *,
    identity: SourceIdentity,
) -> RawMessage:
    """Convert one live message into the shared RawMessage boundary."""
    payload = live_message_payload(message)
    frozen_payload = freeze_json(payload)
    if not isinstance(frozen_payload, Mapping):
        message_text = "live message payload must freeze as an object"
        raise TypeError(message_text)
    return RawMessage(
        source=identity,
        external_message_id=message.external_message_id,
        reply_to_message_id=None,
        published_at=message.published_at.astimezone(UTC),
        edited_at=None if message.edited_at is None else message.edited_at.astimezone(UTC),
        message_type="message",
        text=message.text,
        original_text=freeze_json(message.text),
        text_entities=(),
        media=message.media,
        raw_payload=frozen_payload,
        checksum=canonical_json_checksum(payload),
        media_group_id=message.media_group_id,
    )


def source_identity_from_channel(identity: TelegramChannelIdentity) -> SourceIdentity:
    """Build the shared source identity for the live channel."""
    return SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id=identity.channel_id,
        channel_name=identity.channel_title,
        channel_type="public_channel",
    )


@dataclass(frozen=True, slots=True)
class LiveBackfillResult:
    """Redacted backfill reconciliation summary."""

    verified_channel_id: str
    messages_seen: int
    checkpoint_external_message_id: int
    created: int
    unchanged: int
    revised: int
    skipped_non_candidate: int
