"""Bounded Telegram Desktop JSON export adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING, BinaryIO, Self, cast

import ijson  # type: ignore[import-untyped]

from wef_backend.features.ingestion.application import (
    ChannelExpectation,
    IncompleteScanError,
    ScanSummary,
    SourceErrorCode,
    SourceScanError,
)
from wef_backend.features.ingestion.domain import (
    PrimaryClassification,
    RecordResult,
    ScanCounts,
    SourceIdentity,
    SourceMetadata,
    SourcePlatform,
)
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

SourceOpener = Callable[[], BinaryIO]

_DEFAULT_BUFFER_SIZE = 64 * 1024
_REQUIRED_TOP_LEVEL_KEYS = {"id", "messages", "name", "type"}
_SCALAR_EVENTS = {"boolean", "null", "number", "string"}


class _ScanState(StrEnum):
    NEW = "new"
    ACTIVE = "active"
    COMPLETE = "complete"
    CLOSED = "closed"
    FAILED = "failed"


@dataclass(slots=True)
class _MutableCounts:
    service: int = 0
    photo: int = 0
    video: int = 0
    text: int = 0
    empty: int = 0
    unhandled: int = 0
    malformed: int = 0
    mixed_text: int = 0
    reply: int = 0

    def add(
        self,
        classification: PrimaryClassification,
        *,
        mixed_text: bool,
        reply: bool,
    ) -> None:
        """Add one primary category and optional supplemental flags."""
        setattr(self, classification.value, getattr(self, classification.value) + 1)
        self.mixed_text += int(mixed_text)
        self.reply += int(reply)

    def freeze(self) -> ScanCounts:
        """Return immutable terminal reconciliation counts."""
        return ScanCounts(
            service=self.service,
            photo=self.photo,
            video=self.video,
            text=self.text,
            empty=self.empty,
            unhandled=self.unhandled,
            malformed=self.malformed,
            mixed_text=self.mixed_text,
            reply=self.reply,
        )


class _HashingReader:
    """Hash source bytes while enforcing explicitly bounded reads."""

    def __init__(self, source: BinaryIO) -> None:
        self._source = source
        self._digest = sha256()
        self.bytes_read = 0
        self.maximum_request = 0

    def read(self, size: int = -1) -> bytes:
        """Read and hash one bounded chunk."""
        if size < 0:
            message = "unbounded source reads are prohibited"
            raise ValueError(message)
        self.maximum_request = max(self.maximum_request, size)
        chunk = self._source.read(size)
        self._digest.update(chunk)
        self.bytes_read += len(chunk)
        return chunk

    def hexdigest(self) -> str:
        """Return the digest for all bytes read so far."""
        return self._digest.hexdigest()


class TelegramDesktopExportAdapter:
    """Validate and stream one configured Telegram Desktop export."""

    def __init__(
        self,
        source_path: Path,
        expectation: ChannelExpectation,
        *,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
        opener: SourceOpener | None = None,
    ) -> None:
        """Store source configuration without opening or reading it."""
        if buffer_size <= 0:
            message = "buffer size must be positive"
            raise ValueError(message)
        self._source_path = source_path
        self._expectation = expectation
        self._buffer_size = buffer_size
        self._opener = opener or self._open_path

    def open_scan(self) -> TelegramExportScan:
        """Preflight the complete document, then return a one-use scan."""
        metadata = self._preflight()
        return TelegramExportScan(
            metadata=metadata,
            buffer_size=self._buffer_size,
            opener=self._opener,
        )

    def _open_path(self) -> BinaryIO:
        return self._source_path.open("rb")

    def _preflight(self) -> SourceMetadata:
        try:
            file_size = self._source_path.stat().st_size
            source = self._opener()
            with source:
                metadata = self._parse_top_level(source)
        except ijson.IncompleteJSONError as error:
            raise SourceScanError(SourceErrorCode.TRUNCATED_JSON) from error
        except ijson.JSONError as error:
            raise SourceScanError(SourceErrorCode.INVALID_JSON) from error
        except (OSError, ValueError) as error:
            raise SourceScanError(SourceErrorCode.SOURCE_IO) from error

        channel_id, channel_name, channel_type = metadata
        if (
            channel_id != self._expectation.channel_id
            or channel_type != self._expectation.channel_type
            or (
                self._expectation.channel_name is not None
                and channel_name != self._expectation.channel_name
            )
        ):
            raise SourceScanError(SourceErrorCode.CHANNEL_MISMATCH)
        return SourceMetadata(
            identity=SourceIdentity(
                platform=SourcePlatform.TELEGRAM,
                channel_id=channel_id,
                channel_name=channel_name,
                channel_type=channel_type,
            ),
            file_size=file_size,
        )

    def _parse_top_level(self, source: BinaryIO) -> tuple[str, str, str]:
        top_level_keys: set[str] = set()
        values: dict[str, object] = {}
        root_started = False
        messages_is_array = False
        for prefix, event, value in ijson.parse(
            source,
            buf_size=self._buffer_size,
            use_float=True,
        ):
            if not root_started:
                if prefix != "" or event != "start_map":
                    raise SourceScanError(SourceErrorCode.INVALID_TOP_LEVEL)
                root_started = True
            if prefix == "" and event == "map_key":
                key = cast("str", value)
                if key in top_level_keys:
                    raise SourceScanError(SourceErrorCode.INVALID_TOP_LEVEL)
                top_level_keys.add(key)
            elif prefix in {"id", "name", "type"} and event in _SCALAR_EVENTS:
                values[prefix] = value
            elif prefix == "messages" and event == "start_array":
                messages_is_array = True

        if top_level_keys != _REQUIRED_TOP_LEVEL_KEYS or not messages_is_array:
            raise SourceScanError(SourceErrorCode.INVALID_TOP_LEVEL)
        channel_id = values.get("id")
        channel_name = values.get("name")
        channel_type = values.get("type")
        if (
            isinstance(channel_id, bool)
            or not isinstance(channel_id, int | str)
            or not str(channel_id)
            or not isinstance(channel_name, str)
            or not channel_name
            or not isinstance(channel_type, str)
            or not channel_type
        ):
            raise SourceScanError(SourceErrorCode.INVALID_TOP_LEVEL)
        return str(channel_id), channel_name, channel_type


class TelegramExportScan:
    """One-use iJSON iterator with terminal-only checksum and counts."""

    def __init__(
        self,
        *,
        metadata: SourceMetadata,
        buffer_size: int,
        opener: SourceOpener,
    ) -> None:
        """Initialize a lazy scan without holding decoded records."""
        self._metadata = metadata
        self._buffer_size = buffer_size
        self._opener = opener
        self._state = _ScanState.NEW
        self._source: BinaryIO | None = None
        self._reader: _HashingReader | None = None
        self._records: Iterator[object] | None = None
        self._counts = _MutableCounts()
        self._source_index = 0
        self._summary: ScanSummary | None = None

    def __iter__(self) -> TelegramExportScan:
        """Return this one-use scan."""
        return self

    def __next__(self) -> RecordResult:
        """Yield one converted item or finalize after complete exhaustion."""
        if self._state in {_ScanState.COMPLETE, _ScanState.CLOSED}:
            raise StopIteration
        if self._state is _ScanState.FAILED:
            raise SourceScanError(SourceErrorCode.SCAN_ALREADY_STARTED)
        if self._state is _ScanState.NEW:
            self._start()
        records = cast("Iterator[object]", self._records)
        try:
            raw = next(records)
        except StopIteration:
            self._finish()
            raise
        except ijson.IncompleteJSONError as error:
            self._fail()
            raise SourceScanError(SourceErrorCode.TRUNCATED_JSON) from error
        except ijson.JSONError as error:
            self._fail()
            raise SourceScanError(SourceErrorCode.INVALID_JSON) from error
        except OSError as error:
            self._fail()
            raise SourceScanError(SourceErrorCode.SOURCE_IO) from error

        converted = convert_record(raw, self._source_index, self._metadata.identity)
        self._source_index += 1
        self._counts.add(
            converted.result.classification,
            mixed_text=converted.mixed_text,
            reply=converted.reply,
        )
        return converted.result

    def __enter__(self) -> Self:
        """Enter a scan context without starting reads."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the source, preserving complete state when exhausted."""
        del exc_type, exc_value, traceback
        self.close()

    @property
    def is_complete(self) -> bool:
        """Return whether all source bytes and records reconciled."""
        return self._state is _ScanState.COMPLETE

    @property
    def summary(self) -> ScanSummary:
        """Return final metadata or reject incomplete/failed access."""
        if self._summary is None or not self.is_complete:
            message = "complete scan summary is unavailable before exhaustion"
            raise IncompleteScanError(message)
        return self._summary

    def close(self) -> None:
        """Close a partial scan without creating a terminal summary."""
        self._close_source()
        if self._state not in {_ScanState.COMPLETE, _ScanState.FAILED}:
            self._state = _ScanState.CLOSED

    def _start(self) -> None:
        try:
            self._source = self._opener()
            self._reader = _HashingReader(self._source)
            self._records = iter(
                ijson.items(
                    self._reader,
                    "messages.item",
                    buf_size=self._buffer_size,
                    use_float=True,
                )
            )
        except OSError as error:
            self._fail()
            raise SourceScanError(SourceErrorCode.SOURCE_IO) from error
        self._state = _ScanState.ACTIVE

    def _finish(self) -> None:
        reader = cast("_HashingReader", self._reader)
        if reader.bytes_read != self._metadata.file_size:
            self._fail()
            raise SourceScanError(SourceErrorCode.SOURCE_IO)
        self._summary = ScanSummary(
            source=self._metadata,
            source_checksum=reader.hexdigest(),
            counts=self._counts.freeze(),
        )
        self._close_source()
        self._state = _ScanState.COMPLETE

    def _fail(self) -> None:
        self._close_source()
        self._state = _ScanState.FAILED

    def _close_source(self) -> None:
        if self._source is not None:
            self._source.close()
            self._source = None
