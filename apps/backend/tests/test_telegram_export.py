"""Golden, failure, and bounded-I/O tests for Telegram Desktop exports."""

from __future__ import annotations

import json
import tracemalloc
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Self, cast

import pytest

from wef_backend.features.ingestion.application import (
    ChannelExpectation,
    IncompleteScanError,
    ScanSummary,
    SourceErrorCode,
    SourceScanError,
)
from wef_backend.features.ingestion.domain import (
    MalformedReason,
    MediaKind,
    PrimaryClassification,
    RecordResult,
    ScanCounts,
    SourceIdentity,
    SourceMetadata,
    SourcePlatform,
    canonical_json_bytes,
)
from wef_backend.features.ingestion.infrastructure import TelegramDesktopExportAdapter
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from collections.abc import Callable

    from wef_backend.features.ingestion.domain import RawMessage

FIXTURE_ROOT = Path(__file__).parent / "fixtures/telegram_export"
COMPLETE_FIXTURE = FIXTURE_ROOT / "sanitized-complete.json"
MALFORMED_FIXTURE = FIXTURE_ROOT / "synthetic-malformed-record.json"
TRUNCATED_FIXTURE = FIXTURE_ROOT / "synthetic-truncated.json"
GOLDEN_FIXTURE = FIXTURE_ROOT / "sanitized-complete.golden.json"
EXPECTATION = ChannelExpectation(
    channel_id="9001",
    channel_type="public_channel",
    channel_name="Sanitized Fixture Channel",
)
_LARGE_RECORD_COUNT = 20_000
_MAX_TEST_BUFFER = 4096
_MAX_STREAMING_PEAK_BYTES = 4 * 1024 * 1024


class GuardedReader:
    """Reject unbounded reads while recording the parser's requests."""

    def __init__(self, source: BinaryIO, requests: list[int]) -> None:
        """Store the wrapped source and shared request log."""
        self._source = source
        self._requests = requests

    def read(self, size: int = -1) -> bytes:
        """Delegate only explicitly bounded reads."""
        if size < 0:
            message = "test reader rejected an unbounded read"
            raise AssertionError(message)
        self._requests.append(size)
        return self._source.read(size)

    def close(self) -> None:
        """Close the wrapped file."""
        self._source.close()

    def __enter__(self) -> Self:
        """Enter the wrapped reader context."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the wrapped reader context."""
        del args
        self.close()


def _adapter(
    path: Path = COMPLETE_FIXTURE,
    expectation: ChannelExpectation = EXPECTATION,
    *,
    buffer_size: int = 64 * 1024,
    opener: Callable[[], BinaryIO] | None = None,
) -> TelegramDesktopExportAdapter:
    return TelegramDesktopExportAdapter(
        path,
        expectation,
        buffer_size=buffer_size,
        opener=opener,
    )


def _json_value(value: object) -> object:
    return json.loads(canonical_json_bytes(value))


def _message_snapshot(message: RawMessage) -> dict[str, object]:
    return {
        "source": {
            "platform": message.source.platform.value,
            "channel_id": message.source.channel_id,
            "channel_name": message.source.channel_name,
            "channel_type": message.source.channel_type,
        },
        "external_message_id": message.external_message_id,
        "reply_to_message_id": message.reply_to_message_id,
        "published_at": message.published_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "message_type": message.message_type,
        "media_group_id": message.media_group_id,
        "text": message.text,
        "original_text": _json_value(message.original_text),
        "text_entities": _json_value(message.text_entities),
        "media": [
            {
                key: (value.value if hasattr(value, "value") else value)
                for key, value in asdict(item).items()
            }
            for item in message.media
        ],
        "raw_payload": _json_value(message.raw_payload),
        "checksum": message.checksum,
    }


def _result_snapshot(result: RecordResult) -> dict[str, object]:
    return {
        "source_index": result.source_index,
        "disposition": result.disposition.value,
        "classification": result.classification.value,
        "checksum": result.checksum,
        "reason": result.reason.value if result.reason else None,
        "message": _message_snapshot(result.message) if result.message else None,
    }


def _summary_snapshot(summary: ScanSummary) -> dict[str, object]:
    return {
        "source": {
            "platform": summary.source.identity.platform.value,
            "channel_id": summary.source.identity.channel_id,
            "channel_name": summary.source.identity.channel_name,
            "channel_type": summary.source.identity.channel_type,
            "file_size": summary.source.file_size,
        },
        "source_checksum": summary.source_checksum,
        "counts": asdict(summary.counts),
    }


def test_sanitized_fixture_matches_complete_raw_message_golden() -> None:
    """All reviewed source shapes stay deterministic at the shared boundary."""
    with _adapter().open_scan() as scan:
        results = list(scan)
        snapshot = {
            "summary": _summary_snapshot(scan.summary),
            "records": [_result_snapshot(result) for result in results],
        }

    expected = json.loads(GOLDEN_FIXTURE.read_text(encoding="utf-8"))
    assert snapshot == expected
    assert results[1].message is not None
    assert results[1].message.raw_payload["fixture_extension"] == {"preserved": True}


def test_structurally_malformed_item_is_reconciled_with_stable_reason() -> None:
    """A bad array item remains counted instead of aborting or disappearing."""
    with _adapter(MALFORMED_FIXTURE).open_scan() as scan:
        results = list(scan)

    assert len(results) == 1
    assert results[0].reason is MalformedReason.MISSING_MESSAGE_ID
    assert results[0].message is None
    assert scan.summary.counts == ScanCounts(malformed=1)


def test_partial_consumer_cannot_claim_checksum_or_reconciliation() -> None:
    """Stopping early leaves terminal evidence inaccessible."""
    scan = _adapter().open_scan()
    first = next(scan)

    assert first.source_index == 0
    assert not scan.is_complete
    with pytest.raises(IncompleteScanError, match="before exhaustion"):
        _ = scan.summary

    scan.close()
    assert list(scan) == []
    with pytest.raises(IncompleteScanError, match="before exhaustion"):
        _ = scan.summary


def test_truncated_document_fails_closed_during_preflight() -> None:
    """A cut-off source cannot expose any record iterator."""
    with pytest.raises(SourceScanError) as error:
        _adapter(TRUNCATED_FIXTURE).open_scan()

    assert error.value.code is SourceErrorCode.TRUNCATED_JSON
    assert str(error.value) == "historical source scan failed: truncated_json"


def test_channel_mismatch_fails_with_redacted_error() -> None:
    """An accidental export cannot cross the configured source boundary."""
    wrong = ChannelExpectation(channel_id="different", channel_type="public_channel")

    with pytest.raises(SourceScanError) as error:
        _adapter(expectation=wrong).open_scan()

    assert error.value.code is SourceErrorCode.CHANNEL_MISMATCH
    assert "Sanitized Fixture Channel" not in str(error.value)
    assert str(COMPLETE_FIXTURE) not in str(error.value)


def test_changed_top_level_shape_fails_closed(tmp_path: Path) -> None:
    """Unknown top-level structure requires explicit adapter review."""
    path = tmp_path / "changed.json"
    path.write_text(
        json.dumps(
            {
                "name": "Sanitized Fixture Channel",
                "type": "public_channel",
                "id": 9001,
                "messages": [],
                "schema_version": 2,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceScanError) as error:
        _adapter(path).open_scan()

    assert error.value.code is SourceErrorCode.INVALID_TOP_LEVEL


def test_source_io_failure_is_redacted_before_and_during_scan(tmp_path: Path) -> None:
    """Path and operating-system details never cross the adapter boundary."""
    missing = tmp_path / "private-source-name.json"
    with pytest.raises(SourceScanError) as missing_error:
        _adapter(missing).open_scan()
    assert missing_error.value.code is SourceErrorCode.SOURCE_IO
    assert str(missing) not in str(missing_error.value)

    calls = 0

    def fails_on_scan() -> BinaryIO:
        nonlocal calls
        calls += 1
        if calls == 1:
            return COMPLETE_FIXTURE.open("rb")
        raise PermissionError

    scan = _adapter(opener=fails_on_scan).open_scan()
    with pytest.raises(SourceScanError) as scan_error:
        next(scan)
    assert scan_error.value.code is SourceErrorCode.SOURCE_IO
    with pytest.raises(IncompleteScanError):
        _ = scan.summary


def test_source_change_after_preflight_cannot_be_reported_complete() -> None:
    """A truncated replacement fails the active scan and remains failed."""
    calls = 0

    def replaced_source() -> BinaryIO:
        nonlocal calls
        calls += 1
        path = COMPLETE_FIXTURE if calls == 1 else TRUNCATED_FIXTURE
        return path.open("rb")

    scan = _adapter(opener=replaced_source).open_scan()
    with pytest.raises(SourceScanError) as error:
        list(scan)
    assert error.value.code is SourceErrorCode.TRUNCATED_JSON

    with pytest.raises(SourceScanError) as repeated_error:
        next(scan)
    assert repeated_error.value.code is SourceErrorCode.SCAN_ALREADY_STARTED


def test_source_size_change_after_preflight_blocks_terminal_checksum() -> None:
    """Even valid trailing bytes invalidate the preflight source identity."""
    calls = 0
    complete_bytes = COMPLETE_FIXTURE.read_bytes()

    def changed_size() -> BinaryIO:
        nonlocal calls
        calls += 1
        if calls == 1:
            return COMPLETE_FIXTURE.open("rb")
        return cast("BinaryIO", BytesIO(complete_bytes + b" "))

    scan = _adapter(opener=changed_size).open_scan()
    with pytest.raises(SourceScanError) as error:
        list(scan)

    assert error.value.code is SourceErrorCode.SOURCE_IO
    assert not scan.is_complete


def test_generated_large_source_uses_bounded_reads_and_memory(tmp_path: Path) -> None:
    """Streaming cost stays bounded while record count grows."""
    path = tmp_path / "large.json"
    _write_large_source(path)
    requests: list[int] = []

    def guarded_opener() -> BinaryIO:
        return cast("BinaryIO", GuardedReader(path.open("rb"), requests))

    tracemalloc.start()
    try:
        with _adapter(
            path,
            buffer_size=_MAX_TEST_BUFFER,
            opener=guarded_opener,
        ).open_scan() as scan:
            count = sum(1 for _result in scan)
            summary = scan.summary
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert count == _LARGE_RECORD_COUNT
    assert summary.counts == ScanCounts(text=_LARGE_RECORD_COUNT)
    assert requests
    assert max(requests) <= _MAX_TEST_BUFFER
    assert peak < _MAX_STREAMING_PEAK_BYTES


def test_source_configuration_and_summary_validate_required_values() -> None:
    """Empty expectations and invalid terminal digests are rejected."""
    with pytest.raises(ValueError, match="must not be empty"):
        ChannelExpectation(channel_id="", channel_type="public_channel")
    with pytest.raises(ValueError, match="non-empty"):
        ChannelExpectation(channel_id="9001", channel_type="public_channel", channel_name="")
    with pytest.raises(ValueError, match="SHA-256"):
        ScanSummary(
            source=SourceMetadata(
                identity=SourceIdentity(
                    platform=SourcePlatform.TELEGRAM,
                    channel_id="9001",
                    channel_name="Fixture",
                    channel_type="public_channel",
                ),
                file_size=1,
            ),
            source_checksum="invalid",
            counts=ScanCounts(),
        )
    with pytest.raises(ValueError, match="buffer size"):
        _adapter(buffer_size=0)


def test_record_conversion_categorizes_structural_failures() -> None:
    """Every invalid source field maps to a stable malformed reason."""
    base: dict[str, object] = {
        "id": 1,
        "type": "message",
        "date_unixtime": "1893456000",
        "text": "fixture",
        "text_entities": [],
    }
    cases: list[tuple[object, MalformedReason]] = [
        (["not", "an", "object"], MalformedReason.RECORD_NOT_OBJECT),
        (
            {key: value for key, value in base.items() if key != "id"},
            MalformedReason.MISSING_MESSAGE_ID,
        ),
        ({**base, "id": False}, MalformedReason.INVALID_MESSAGE_ID),
        (
            {key: value for key, value in base.items() if key != "type"},
            MalformedReason.MISSING_MESSAGE_TYPE,
        ),
        ({**base, "type": 1}, MalformedReason.INVALID_MESSAGE_TYPE),
        (
            {key: value for key, value in base.items() if key != "date_unixtime"},
            MalformedReason.MISSING_PUBLISHED_TIMESTAMP,
        ),
        ({**base, "date_unixtime": "not-a-time"}, MalformedReason.INVALID_PUBLISHED_TIMESTAMP),
        ({**base, "date_unixtime": "01"}, MalformedReason.INVALID_PUBLISHED_TIMESTAMP),
        ({**base, "edited_unixtime": []}, MalformedReason.INVALID_EDITED_TIMESTAMP),
        ({**base, "reply_to_message_id": 0}, MalformedReason.INVALID_REPLY_ID),
        ({**base, "text": [1]}, MalformedReason.INVALID_TEXT),
        ({**base, "text": {}}, MalformedReason.INVALID_TEXT),
        ({**base, "text_entities": "bad"}, MalformedReason.INVALID_TEXT),
        ({**base, "photo": []}, MalformedReason.INVALID_MEDIA_DESCRIPTOR),
        ({**base, "file": "safe.bin", "mime_type": 1}, MalformedReason.INVALID_MEDIA_DESCRIPTOR),
        ({**base, "photo": "safe.jpg", "file_size": -1}, MalformedReason.INVALID_MEDIA_DESCRIPTOR),
    ]
    source = SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="9001",
        channel_name="Fixture",
        channel_type="public_channel",
    )

    for raw, expected_reason in cases:
        converted = convert_record(raw, 0, source)
        assert converted.result.reason is expected_reason
        assert converted.result.classification is PrimaryClassification.MALFORMED


def test_generic_file_is_preserved_as_valid_unhandled_media() -> None:
    """Unknown file media remains replayable without invented classification."""
    source = SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="9001",
        channel_name="Fixture",
        channel_type="public_channel",
    )
    converted = convert_record(
        {
            "id": 1,
            "type": "message",
            "date_unixtime": 1_893_456_000,
            "file": "files/sample_document.bin",
            "text": "",
            "text_entities": [],
        },
        0,
        source,
    )

    assert converted.result.classification is PrimaryClassification.UNHANDLED
    assert converted.result.message is not None
    assert converted.result.message.media[0].kind is MediaKind.FILE
    assert converted.result.message.media[0].mime_type is None


def test_telegram_image_descriptors_infer_candidates_for_byte_verification() -> None:
    """Photo and thumbnail paths gain only supported image MIME candidates."""
    source = SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="9001",
        channel_name="Fixture",
        channel_type="public_channel",
    )
    converted = convert_record(
        {
            "id": 1,
            "type": "message",
            "date_unixtime": 1_893_456_000,
            "photo": "photos/sample_photo.JPG",
            "thumbnail": "video_files/sample_thumb.webp",
            "text": "",
            "text_entities": [],
        },
        0,
        source,
    )

    assert converted.result.message is not None
    assert [item.mime_type for item in converted.result.message.media] == [
        "image/jpeg",
        "image/webp",
    ]


def _write_large_source(path: Path) -> None:
    prefix = b'{"name":"Sanitized Fixture Channel","type":"public_channel","id":9001,"messages":['
    suffix = b"]}"
    text = "bounded-" + ("x" * 256)
    with path.open("wb") as source:
        source.write(prefix)
        for index in range(_LARGE_RECORD_COUNT):
            if index:
                source.write(b",")
            record = {
                "id": index + 1,
                "type": "message",
                "date_unixtime": str(1_893_456_000 + index),
                "text": text,
                "text_entities": [],
            }
            source.write(json.dumps(record, separators=(",", ":")).encode())
        source.write(suffix)
