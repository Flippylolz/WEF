"""Framework-independent source-ingestion values."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]
type FrozenJSONValue = JSONScalar | tuple[FrozenJSONValue, ...] | Mapping[str, FrozenJSONValue]

_CHECKSUM_LENGTH = 64


class JSONValueError(ValueError):
    """Raised when a value cannot be represented as canonical JSON."""


class SourcePlatform(StrEnum):
    """Supported source-system identities."""

    TELEGRAM = "telegram"


class MediaKind(StrEnum):
    """Source media descriptor kinds without storage assumptions."""

    PHOTO = "photo"
    VIDEO = "video"
    FILE = "file"
    THUMBNAIL = "thumbnail"


class PrimaryClassification(StrEnum):
    """Exactly-one primary reconciliation category for a source record."""

    SERVICE = "service"
    PHOTO = "photo"
    VIDEO = "video"
    TEXT = "text"
    EMPTY = "empty"
    UNHANDLED = "unhandled"
    MALFORMED = "malformed"


class RecordDisposition(StrEnum):
    """Whether a source item crossed the raw-message boundary."""

    ACCEPTED = "accepted"
    UNHANDLED = "unhandled"
    MALFORMED = "malformed"


class MalformedReason(StrEnum):
    """Stable reasons for rejecting one structurally invalid item."""

    RECORD_NOT_OBJECT = "record_not_object"
    MISSING_MESSAGE_ID = "missing_message_id"
    INVALID_MESSAGE_ID = "invalid_message_id"
    MISSING_MESSAGE_TYPE = "missing_message_type"
    INVALID_MESSAGE_TYPE = "invalid_message_type"
    MISSING_PUBLISHED_TIMESTAMP = "missing_published_timestamp"
    INVALID_PUBLISHED_TIMESTAMP = "invalid_published_timestamp"
    INVALID_EDITED_TIMESTAMP = "invalid_edited_timestamp"
    INVALID_REPLY_ID = "invalid_reply_id"
    INVALID_TEXT = "invalid_text"
    INVALID_MEDIA_DESCRIPTOR = "invalid_media_descriptor"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Stable source identity shared by historical and future adapters."""

    platform: SourcePlatform
    channel_id: str
    channel_name: str
    channel_type: str

    def __post_init__(self) -> None:
        """Reject incomplete source identities."""
        if not all((self.channel_id, self.channel_name, self.channel_type)):
            message = "source channel identity must be complete"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Validated source-level metadata that is safe to keep in memory."""

    identity: SourceIdentity
    file_size: int

    def __post_init__(self) -> None:
        """Reject impossible source sizes."""
        if self.file_size < 0:
            message = "source file size must not be negative"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MediaDescriptor:
    """A source media reference without file access or trust."""

    kind: MediaKind
    path: str
    mime_type: str | None = None
    size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None

    def __post_init__(self) -> None:
        """Reject empty paths and negative numeric metadata."""
        if not self.path:
            message = "media descriptor path must not be empty"
            raise ValueError(message)
        numeric_values = (
            self.size_bytes,
            self.width,
            self.height,
            self.duration_seconds,
        )
        if any(value is not None and value < 0 for value in numeric_values):
            message = "media descriptor numeric values must not be negative"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class RawMessage:
    """Replayable source-neutral message at the ingestion boundary."""

    source: SourceIdentity
    external_message_id: int
    reply_to_message_id: int | None
    published_at: datetime
    edited_at: datetime | None
    message_type: str
    text: str
    original_text: FrozenJSONValue
    text_entities: tuple[FrozenJSONValue, ...]
    media: tuple[MediaDescriptor, ...]
    raw_payload: Mapping[str, FrozenJSONValue]
    checksum: str

    def __post_init__(self) -> None:
        """Enforce stable identity, UTC timestamps, and checksum shape."""
        if isinstance(self.external_message_id, bool) or self.external_message_id <= 0:
            message = "external message id must be a positive integer"
            raise ValueError(message)
        if self.reply_to_message_id is not None and (
            isinstance(self.reply_to_message_id, bool) or self.reply_to_message_id <= 0
        ):
            message = "reply message id must be a positive integer"
            raise ValueError(message)
        if not self.message_type:
            message = "message type must not be empty"
            raise ValueError(message)
        if not _is_utc(self.published_at) or (
            self.edited_at is not None and not _is_utc(self.edited_at)
        ):
            message = "source timestamps must be timezone-aware UTC"
            raise ValueError(message)
        _validate_checksum(self.checksum)


@dataclass(frozen=True, slots=True)
class RecordResult:
    """One reconciled result for one source array item."""

    source_index: int
    disposition: RecordDisposition
    classification: PrimaryClassification
    checksum: str
    message: RawMessage | None = None
    reason: MalformedReason | None = None

    def __post_init__(self) -> None:
        """Keep accepted, unhandled, and malformed result shapes disjoint."""
        if self.source_index < 0:
            message = "source index must not be negative"
            raise ValueError(message)
        _validate_checksum(self.checksum)
        malformed = self.disposition is RecordDisposition.MALFORMED
        if malformed != (self.classification is PrimaryClassification.MALFORMED):
            message = "malformed disposition and classification must agree"
            raise ValueError(message)
        if malformed != (self.reason is not None):
            message = "only malformed results carry a reason"
            raise ValueError(message)
        if malformed == (self.message is not None):
            message = "only non-malformed results carry a raw message"
            raise ValueError(message)
        if self.disposition is RecordDisposition.UNHANDLED and (
            self.classification is not PrimaryClassification.UNHANDLED
        ):
            message = "unhandled disposition requires unhandled classification"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ScanCounts:
    """Immutable reconciled primary and supplemental source counts."""

    service: int = 0
    photo: int = 0
    video: int = 0
    text: int = 0
    empty: int = 0
    unhandled: int = 0
    malformed: int = 0
    mixed_text: int = 0
    reply: int = 0

    @property
    def total(self) -> int:
        """Return the sum of exactly-one primary categories."""
        return (
            self.service
            + self.photo
            + self.video
            + self.text
            + self.empty
            + self.unhandled
            + self.malformed
        )

    def __post_init__(self) -> None:
        """Reject negative reconciliation values."""
        values = (
            self.service,
            self.photo,
            self.video,
            self.text,
            self.empty,
            self.unhandled,
            self.malformed,
            self.mixed_text,
            self.reply,
        )
        if any(value < 0 for value in values):
            message = "scan counts must not be negative"
            raise ValueError(message)


def freeze_json(value: object) -> FrozenJSONValue:
    """Copy supported JSON data into recursively immutable containers."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            message = "non-finite numbers are not valid canonical JSON"
            raise JSONValueError(message)
        return value
    if isinstance(value, list | tuple):
        return tuple(freeze_json(item) for item in value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            message = "JSON object keys must be strings"
            raise JSONValueError(message)
        return MappingProxyType({str(key): freeze_json(item) for key, item in value.items()})
    message = f"unsupported JSON value type: {type(value).__name__}"
    raise JSONValueError(message)


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON data deterministically with Unicode preserved."""
    normalized = _mutable_json(value)
    try:
        rendered = json.dumps(
            normalized,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        message = "value cannot be serialized as canonical JSON"
        raise JSONValueError(message) from error
    return rendered.encode()


def canonical_json_checksum(value: object) -> str:
    """Return the SHA-256 of canonical compact UTF-8 JSON."""
    return sha256(canonical_json_bytes(value)).hexdigest()


def _mutable_json(value: object) -> JSONValue:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            message = "JSON object keys must be strings"
            raise JSONValueError(message)
        return {str(key): _mutable_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_mutable_json(item) for item in value]
    message = f"unsupported JSON value type: {type(value).__name__}"
    raise JSONValueError(message)


def _is_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None and not value.utcoffset()


def _validate_checksum(value: str) -> None:
    if len(value) != _CHECKSUM_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        message = "checksum must be a lowercase SHA-256 digest"
        raise ValueError(message)
