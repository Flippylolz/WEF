"""Unit tests for framework-independent ingestion values."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from wef_backend.features.ingestion.domain import (
    JSONValueError,
    MalformedReason,
    MediaDescriptor,
    MediaKind,
    PrimaryClassification,
    RawMessage,
    RecordDisposition,
    RecordResult,
    ScanCounts,
    SourceIdentity,
    SourceMetadata,
    SourcePlatform,
    canonical_json_bytes,
    canonical_json_checksum,
    freeze_json,
)

_CHECKSUM = "0" * 64


def _source() -> SourceIdentity:
    return SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="fixture",
        channel_name="Fixture",
        channel_type="public_channel",
    )


def _raw_message(*, published_at: datetime) -> RawMessage:
    raw = freeze_json({"id": 1, "text": "ż"})
    assert isinstance(raw, MappingProxyType)
    return RawMessage(
        source=_source(),
        external_message_id=1,
        reply_to_message_id=None,
        published_at=published_at,
        edited_at=None,
        message_type="message",
        text="ż",
        original_text="ż",
        text_entities=(),
        media=(),
        raw_payload=raw,
        checksum=_CHECKSUM,
    )


def test_canonical_json_checksum_preserves_unicode_and_ignores_key_order() -> None:
    """Equivalent objects have one compact UTF-8 checksum."""
    left = {"z": ["ż", 1], "a": {"x": True}}
    right = {"a": {"x": True}, "z": ["ż", 1]}

    assert canonical_json_bytes(left) == b'{"a":{"x":true},"z":["\xc5\xbc",1]}'
    assert canonical_json_checksum(left) == canonical_json_checksum(right)


def test_freeze_json_recursively_prevents_payload_mutation() -> None:
    """Raw evidence cannot be changed through nested containers."""
    frozen = freeze_json({"nested": [{"value": 1}]})

    assert isinstance(frozen, MappingProxyType)
    nested = frozen["nested"]
    assert isinstance(nested, tuple)
    item = nested[0]
    assert isinstance(item, MappingProxyType)
    with pytest.raises(TypeError):
        item["value"] = 2  # type: ignore[index]


def test_raw_message_requires_timezone_aware_utc() -> None:
    """Source instants cannot silently depend on the process timezone."""
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        _raw_message(published_at=datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None))

    message = _raw_message(published_at=datetime(2030, 1, 1, tzinfo=UTC))
    assert message.published_at.tzinfo is UTC


def test_record_result_keeps_malformed_shape_disjoint() -> None:
    """Malformed records cannot masquerade as accepted raw messages."""
    with pytest.raises(ValueError, match="malformed disposition"):
        RecordResult(
            source_index=0,
            disposition=RecordDisposition.ACCEPTED,
            classification=PrimaryClassification.MALFORMED,
            checksum=_CHECKSUM,
            message=_raw_message(published_at=datetime(2030, 1, 1, tzinfo=UTC)),
        )


def test_scan_counts_reconcile_exactly_one_primary_category() -> None:
    """Supplemental mixed/reply counts do not inflate the primary total."""
    counts = ScanCounts(
        service=1,
        photo=2,
        video=3,
        text=4,
        empty=5,
        unhandled=6,
        malformed=7,
        mixed_text=20,
        reply=10,
    )

    assert counts.total == 28
    with pytest.raises(ValueError, match="must not be negative"):
        ScanCounts(text=-1)


def test_source_and_media_values_reject_incomplete_or_negative_data() -> None:
    """Invalid metadata cannot enter the shared source contract."""
    with pytest.raises(ValueError, match="identity must be complete"):
        SourceIdentity(SourcePlatform.TELEGRAM, "", "Fixture", "public_channel")
    with pytest.raises(ValueError, match="must not be negative"):
        SourceMetadata(identity=_source(), file_size=-1)
    with pytest.raises(ValueError, match="path must not be empty"):
        MediaDescriptor(kind=MediaKind.PHOTO, path="")
    with pytest.raises(ValueError, match="numeric values"):
        MediaDescriptor(kind=MediaKind.VIDEO, path="safe/video.mp4", size_bytes=-1)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"external_message_id": 0}, "external message id"),
        ({"reply_to_message_id": 0}, "reply message id"),
        ({"media_group_id": ""}, "media group id"),
        ({"message_type": ""}, "message type"),
        (
            {"edited_at": datetime(2030, 1, 1, tzinfo=timezone(timedelta(hours=1)))},
            "timezone-aware UTC",
        ),
        ({"checksum": "invalid"}, "checksum"),
    ],
)
def test_raw_message_rejects_invalid_identity_and_timestamp_fields(
    changes: dict[str, object],
    message: str,
) -> None:
    """Raw-message invariants fail before downstream replay."""
    raw_message = _raw_message(published_at=datetime(2030, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match=message):
        replace(raw_message, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_index": -1}, "source index"),
        ({"reason": MalformedReason.INVALID_TEXT}, "only malformed"),
        ({"message": None}, "only non-malformed"),
        (
            {
                "disposition": RecordDisposition.UNHANDLED,
                "classification": PrimaryClassification.TEXT,
            },
            "unhandled disposition",
        ),
    ],
)
def test_record_result_rejects_contradictory_shapes(
    changes: dict[str, object],
    message: str,
) -> None:
    """Result state cannot contradict its classification or payload."""
    result = RecordResult(
        source_index=0,
        disposition=RecordDisposition.ACCEPTED,
        classification=PrimaryClassification.TEXT,
        checksum=_CHECKSUM,
        message=_raw_message(published_at=datetime(2030, 1, 1, tzinfo=UTC)),
    )
    with pytest.raises(ValueError, match=message):
        replace(result, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        {1: "non-string key"},
        object(),
    ],
)
def test_freeze_json_rejects_non_json_values(value: object) -> None:
    """Canonical evidence accepts only finite, string-keyed JSON."""
    with pytest.raises(JSONValueError):
        freeze_json(value)


@pytest.mark.parametrize("value", [{1: "bad key"}, object()])
def test_canonical_json_rejects_unsupported_values(value: object) -> None:
    """Checksum generation cannot silently stringify unsupported data."""
    with pytest.raises(JSONValueError):
        canonical_json_bytes(value)
