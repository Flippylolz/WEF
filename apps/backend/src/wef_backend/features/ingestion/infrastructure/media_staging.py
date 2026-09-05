"""Bounded leases for worker-owned downloads, separate from durable source identity."""

from __future__ import annotations

import os
import shutil
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from pathlib import Path

STAGING_BYTES = 56 * 1024 * 1024
HEARTBEAT_RESERVE_BYTES = 8 * 1024 * 1024


class MediaStagingDeferredError(OSError):
    """Temporary capacity or an overlapping consumer requires source retry."""

    retry_after_seconds = 5


@dataclass
class MediaStaging:
    """Reserve complete download limits before I/O; never evict a consumer's files."""

    root: Path
    budget: int = STAGING_BYTES
    reserve: int = HEARTBEAT_RESERVE_BYTES
    _active: dict[int, StagedMedia] = field(default_factory=dict)

    def forget(self, lease: StagedMedia) -> None:
        """Release a reservation only if it still belongs to this lease."""
        if self._active.get(lease.message_id) is lease:
            del self._active[lease.message_id]

    def close(self) -> None:
        """Release remaining leases after the worker consumers have stopped."""
        for lease in tuple(self._active.values()):
            lease.release()

    def acquire(self, message_id: int, maximum: int) -> StagedMedia:
        """Protect stable descriptor filenames against concurrent source observations."""
        self.root.mkdir(parents=True, exist_ok=True)
        reserved = sum(item.maximum for item in self._active.values())
        # Free space already excludes bytes written by current leases. Reserve the
        # unwritten remainder too, so simultaneous downloads cannot overcommit /tmp.
        unwritten = sum(item.maximum - item.written for item in self._active.values())
        free = shutil.disk_usage(self.root).free
        if (
            message_id in self._active
            or maximum > self.budget - reserved
            or maximum + self.reserve > free - unwritten
        ):
            message = "media staging capacity is busy"
            raise MediaStagingDeferredError(message)
        lease = StagedMedia(self, message_id, maximum)
        self._active[message_id] = lease
        return lease


@dataclass
class StagedMedia:
    """A lease lives until the consumer and synchronous album association finish."""

    owner: MediaStaging
    message_id: int
    maximum: int
    written: int = 0
    _path: Path | None = None
    _stream: BinaryIO | None = None

    def open(self, suffix: str) -> StagedMedia:
        """Create only our own file, refusing stale files and symlink replacement."""
        directory = self.owner.root / str(self.message_id)
        directory.mkdir(exist_ok=True)
        if directory.is_symlink():
            message = "media staging directory is unavailable"
            raise MediaStagingDeferredError(message)
        target = directory / f"0{suffix}"
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._path = target
        self._stream = os.fdopen(descriptor, "wb")
        return self

    def write(self, data: bytes) -> int:
        """Reject excess bytes before writing; Telethon accepts binary file objects."""
        if len(data) > self.maximum - self.written:
            message = "media exceeds the download limit"
            raise ValueError(message)
        if shutil.disk_usage(self.owner.root).free < self.owner.reserve + len(data):
            message = "media staging filesystem is busy"
            raise MediaStagingDeferredError(message)
        if self._stream is None:
            message = "media staging lease is closed"
            raise MediaStagingDeferredError(message)
        size = self._stream.write(data)
        self._stream.flush()
        self.written += size
        return size

    def tell(self) -> int:
        """Expose bytes written to the source downloader."""
        return self.written

    def flush(self) -> None:
        """Expose the binary-stream contract without releasing ownership."""
        if self._stream is not None:
            self._stream.flush()

    def close(self) -> None:
        """Finish writing while retaining the consumer's lease."""
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def release(self) -> None:
        """Idempotently remove only the file created by this exact lease."""
        self.close()
        if self._path is not None:
            self._path.unlink(missing_ok=True)
            self._path = None
            with suppress(OSError):
                (self.owner.root / str(self.message_id)).rmdir()
        self.owner.forget(self)
