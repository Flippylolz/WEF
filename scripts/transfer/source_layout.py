"""Bundle source directory layout for historical transfer packaging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.transfer.constants import EXCLUDED_TABLES, INCLUDED_TABLES
from scripts.transfer.dry_run import forbidden_bundle_path
from scripts.transfer.manifest import MediaSummary
from scripts.transfer.paths import PathValidationError, validate_media_relative_path

if TYPE_CHECKING:
    from pathlib import Path


class BundleSourceError(ValueError):
    """Raised when a bundle source layout is invalid."""


@dataclass(frozen=True, slots=True)
class MediaTreeSummary:
    """Counts for one media class within a bundle source."""

    object_count: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class BundleSourceSnapshot:
    """Validated, non-sensitive snapshot of one local bundle source."""

    root: Path
    table_row_counts: dict[str, int]
    database_bytes: int
    restricted_originals: MediaTreeSummary
    public_derivatives: MediaTreeSummary

    @property
    def media_summary(self) -> MediaSummary:
        """Return manifest-ready media aggregates."""
        return MediaSummary(
            restricted_original_count=self.restricted_originals.object_count,
            restricted_original_bytes=self.restricted_originals.total_bytes,
            public_derivative_count=self.public_derivatives.object_count,
            public_derivative_bytes=self.public_derivatives.total_bytes,
        )

    @property
    def media_object_count(self) -> int:
        """Return the total logical media object count."""
        return self.restricted_originals.object_count + self.public_derivatives.object_count

    @property
    def media_bytes(self) -> int:
        """Return the total media byte size."""
        return self.restricted_originals.total_bytes + self.public_derivatives.total_bytes


def load_table_counts(path: Path) -> dict[str, int]:
    """Load and validate table row counts from one JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "table counts must be a JSON object"
        raise BundleSourceError(msg)

    counts: dict[str, int] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            msg = "table count keys must be strings"
            raise BundleSourceError(msg)
        if key in EXCLUDED_TABLES:
            msg = f"excluded table must not appear in table counts: {key}"
            raise BundleSourceError(msg)
        if key not in INCLUDED_TABLES:
            msg = f"unknown table in table counts: {key}"
            raise BundleSourceError(msg)
        if not isinstance(value, int) or value < 0:
            msg = f"table count must be a non-negative integer: {key}"
            raise BundleSourceError(msg)
        counts[key] = value

    return dict(sorted(counts.items()))


def _scan_media_tree(root: Path) -> MediaTreeSummary:
    if not root.exists():
        return MediaTreeSummary(object_count=0, total_bytes=0)

    object_count = 0
    total_bytes = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            if path.is_symlink():
                msg = f"media tree must not contain symlinks: {path}"
                raise BundleSourceError(msg)
            continue

        relative = path.relative_to(root).as_posix()
        try:
            validate_media_relative_path(relative)
        except PathValidationError as error:
            msg = f"unsafe media path: {relative}"
            raise BundleSourceError(msg) from error
        if forbidden_bundle_path(relative):
            msg = f"forbidden media path fragment: {relative}"
            raise BundleSourceError(msg)

        object_count += 1
        total_bytes += path.stat().st_size

    return MediaTreeSummary(object_count=object_count, total_bytes=total_bytes)


def inspect_source(root: Path) -> BundleSourceSnapshot:
    """Validate one bundle source directory and return aggregate counts."""
    resolved = root.resolve()
    if not resolved.is_dir():
        msg = "bundle source root must be a directory"
        raise BundleSourceError(msg)

    counts_path = resolved / "table_counts.json"
    database_path = resolved / "database.sql"
    if not counts_path.is_file():
        msg = "bundle source is missing table_counts.json"
        raise BundleSourceError(msg)
    if not database_path.is_file():
        msg = "bundle source is missing database.sql"
        raise BundleSourceError(msg)

    return BundleSourceSnapshot(
        root=resolved,
        table_row_counts=load_table_counts(counts_path),
        database_bytes=database_path.stat().st_size,
        restricted_originals=_scan_media_tree(resolved / "media" / "originals"),
        public_derivatives=_scan_media_tree(resolved / "media" / "public"),
    )
