"""Telegram Desktop record conversion at the source-specific boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from wef_backend.features.ingestion.domain import (
    FrozenJSONValue,
    MalformedReason,
    MediaDescriptor,
    MediaKind,
    PrimaryClassification,
    RawMessage,
    RecordDisposition,
    RecordResult,
    SourceIdentity,
    canonical_json_checksum,
    freeze_json,
)

_MESSAGE_TYPE = "message"
_SERVICE_TYPE = "service"
_VIDEO_MEDIA_TYPES = {"video", "video_file"}


@dataclass(frozen=True, slots=True)
class ConvertedRecord:
    """One result plus its orthogonal reconciliation flags."""

    result: RecordResult
    mixed_text: bool
    reply: bool


class _RecordProblemError(Exception):
    def __init__(self, reason: MalformedReason) -> None:
        self.reason = reason


def convert_record(raw: object, source_index: int, source: SourceIdentity) -> ConvertedRecord:
    """Convert one decoded Telegram item without losing malformed records."""
    checksum = canonical_json_checksum(raw)
    try:
        payload = _record_payload(raw)
        message_id = _message_id(payload)
        message_type = _message_type(payload)
        published_at = cast(
            "datetime",
            _timestamp(
                payload,
                "date_unixtime",
                missing=MalformedReason.MISSING_PUBLISHED_TIMESTAMP,
                invalid=MalformedReason.INVALID_PUBLISHED_TIMESTAMP,
            ),
        )
        edited_at = _timestamp(
            payload,
            "edited_unixtime",
            missing=None,
            invalid=MalformedReason.INVALID_EDITED_TIMESTAMP,
        )
        reply_id = _reply_id(payload)
        text, original_text, entities, mixed_text = _text(payload)
        media = _media(payload)
        classification = _classification(message_type, text, media)
        disposition = (
            RecordDisposition.UNHANDLED
            if classification is PrimaryClassification.UNHANDLED
            else RecordDisposition.ACCEPTED
        )
        frozen_payload = cast("Mapping[str, FrozenJSONValue]", freeze_json(payload))
        message = RawMessage(
            source=source,
            external_message_id=message_id,
            reply_to_message_id=reply_id,
            published_at=published_at,
            edited_at=edited_at,
            message_type=message_type,
            text=text,
            original_text=original_text,
            text_entities=entities,
            media=media,
            raw_payload=frozen_payload,
            checksum=checksum,
        )
        return ConvertedRecord(
            result=RecordResult(
                source_index=source_index,
                disposition=disposition,
                classification=classification,
                checksum=checksum,
                message=message,
            ),
            mixed_text=mixed_text,
            reply=reply_id is not None,
        )
    except _RecordProblemError as problem:
        return ConvertedRecord(
            result=RecordResult(
                source_index=source_index,
                disposition=RecordDisposition.MALFORMED,
                classification=PrimaryClassification.MALFORMED,
                checksum=checksum,
                reason=problem.reason,
            ),
            mixed_text=False,
            reply=False,
        )


def _record_payload(raw: object) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise _RecordProblemError(MalformedReason.RECORD_NOT_OBJECT)
    return cast("Mapping[str, object]", raw)


def _message_id(payload: Mapping[str, object]) -> int:
    if "id" not in payload:
        raise _RecordProblemError(MalformedReason.MISSING_MESSAGE_ID)
    value = payload["id"]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _RecordProblemError(MalformedReason.INVALID_MESSAGE_ID)
    return value


def _message_type(payload: Mapping[str, object]) -> str:
    if "type" not in payload:
        raise _RecordProblemError(MalformedReason.MISSING_MESSAGE_TYPE)
    value = payload["type"]
    if not isinstance(value, str) or not value:
        raise _RecordProblemError(MalformedReason.INVALID_MESSAGE_TYPE)
    return value


def _timestamp(
    payload: Mapping[str, object],
    key: str,
    *,
    missing: MalformedReason | None,
    invalid: MalformedReason,
) -> datetime | None:
    if key not in payload:
        if missing is not None:
            raise _RecordProblemError(missing)
        return None
    raw = payload[key]
    if isinstance(raw, bool) or not isinstance(raw, int | str):
        raise _RecordProblemError(invalid)
    return _parse_timestamp(raw, invalid)


def _parse_timestamp(raw: int | str, invalid: MalformedReason) -> datetime:
    try:
        timestamp = int(raw)
    except ValueError:
        raise _RecordProblemError(invalid) from None
    if isinstance(raw, str) and str(timestamp) != raw:
        raise _RecordProblemError(invalid)
    try:
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except (OSError, OverflowError, ValueError):
        raise _RecordProblemError(invalid) from None


def _reply_id(payload: Mapping[str, object]) -> int | None:
    value = payload.get("reply_to_message_id")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _RecordProblemError(MalformedReason.INVALID_REPLY_ID)
    return value


def _text(
    payload: Mapping[str, object],
) -> tuple[str, FrozenJSONValue, tuple[FrozenJSONValue, ...], bool]:
    original = payload.get("text", "")
    if isinstance(original, str):
        flattened = original
        mixed = False
    elif isinstance(original, list):
        parts: list[str] = []
        for segment in original:
            if isinstance(segment, str):
                parts.append(segment)
            elif isinstance(segment, Mapping) and isinstance(segment.get("text"), str):
                parts.append(cast("str", segment["text"]))
            else:
                raise _RecordProblemError(MalformedReason.INVALID_TEXT)
        flattened = "".join(parts)
        mixed = True
    else:
        raise _RecordProblemError(MalformedReason.INVALID_TEXT)

    raw_entities = payload.get("text_entities", [])
    if not isinstance(raw_entities, list) or not all(
        isinstance(entity, Mapping) for entity in raw_entities
    ):
        raise _RecordProblemError(MalformedReason.INVALID_TEXT)
    frozen_entities = cast("tuple[FrozenJSONValue, ...]", freeze_json(raw_entities))
    return flattened, freeze_json(original), frozen_entities, mixed


def _media(payload: Mapping[str, object]) -> tuple[MediaDescriptor, ...]:
    descriptors: list[MediaDescriptor] = []
    photo = _optional_path(payload, "photo")
    if photo is not None:
        descriptors.append(_descriptor(MediaKind.PHOTO, photo, payload))

    file_path = _optional_path(payload, "file")
    if file_path is not None:
        media_type = payload.get("media_type")
        mime_type = payload.get("mime_type")
        is_video = media_type in _VIDEO_MEDIA_TYPES or (
            isinstance(mime_type, str) and mime_type.startswith("video/")
        )
        descriptors.append(
            _descriptor(MediaKind.VIDEO if is_video else MediaKind.FILE, file_path, payload)
        )

    thumbnail = _optional_path(payload, "thumbnail")
    if thumbnail is not None:
        descriptors.append(MediaDescriptor(kind=MediaKind.THUMBNAIL, path=thumbnail))
    return tuple(descriptors)


def _optional_path(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise _RecordProblemError(MalformedReason.INVALID_MEDIA_DESCRIPTOR)
    return value


def _descriptor(
    kind: MediaKind,
    path: str,
    payload: Mapping[str, object],
) -> MediaDescriptor:
    mime_type = payload.get("mime_type")
    if mime_type is not None and not isinstance(mime_type, str):
        raise _RecordProblemError(MalformedReason.INVALID_MEDIA_DESCRIPTOR)
    return MediaDescriptor(
        kind=kind,
        path=path,
        mime_type=mime_type,
        size_bytes=_optional_integer(payload, "file_size"),
        width=_optional_integer(payload, "width"),
        height=_optional_integer(payload, "height"),
        duration_seconds=_optional_integer(payload, "duration_seconds"),
    )


def _optional_integer(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _RecordProblemError(MalformedReason.INVALID_MEDIA_DESCRIPTOR)
    return value


def _classification(
    message_type: str,
    text: str,
    media: tuple[MediaDescriptor, ...],
) -> PrimaryClassification:
    if message_type == _SERVICE_TYPE:
        classification = PrimaryClassification.SERVICE
    elif message_type != _MESSAGE_TYPE:
        classification = PrimaryClassification.UNHANDLED
    else:
        kinds = {descriptor.kind for descriptor in media}
        if MediaKind.VIDEO in kinds:
            classification = PrimaryClassification.VIDEO
        elif MediaKind.PHOTO in kinds:
            classification = PrimaryClassification.PHOTO
        elif text:
            classification = PrimaryClassification.TEXT
        elif not media:
            classification = PrimaryClassification.EMPTY
        else:
            classification = PrimaryClassification.UNHANDLED
    return classification
