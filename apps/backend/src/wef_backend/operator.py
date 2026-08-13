"""Bounded operator commands used by the local Compose topology."""

from __future__ import annotations

import errno
import json
import sys
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from wef_backend.settings import load_settings

if TYPE_CHECKING:
    from pathlib import Path


class UnsafeSourceMountError(RuntimeError):
    """Raised when the source path is unavailable or writable."""


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """Non-sensitive metadata emitted by the importer safety probe."""

    file_count: int
    read_only: bool
    source: str


def inspect_source(source: Path) -> SourceInspection:
    """Confirm that an import source exists and is mounted read-only."""
    if not source.is_dir():
        message = f"Source directory does not exist: {source}"
        raise UnsafeSourceMountError(message)

    probe = source / ".wef-write-probe"
    try:
        probe.touch(exist_ok=False)
    except OSError as error:
        if error.errno not in {errno.EACCES, errno.EROFS}:
            raise
    else:
        probe.unlink(missing_ok=True)
        message = f"Source directory must be mounted read-only: {source}"
        raise UnsafeSourceMountError(message)

    file_count = sum(path.is_file() for path in source.rglob("*"))
    return SourceInspection(
        file_count=file_count,
        read_only=True,
        source=str(source),
    )


def main() -> None:
    """Run the importer mount-safety probe without reading source contents."""
    inspection = inspect_source(load_settings().source_path)
    sys.stdout.write(json.dumps(asdict(inspection), sort_keys=True) + "\n")
