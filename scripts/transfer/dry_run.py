"""Pre-packaging dry-run summaries for historical transfer bundles."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.transfer.constants import FORBIDDEN_BUNDLE_PATH_FRAGMENTS, HEADROOM_MULTIPLIER


@dataclass(frozen=True, slots=True)
class DryRunSummary:
    """Non-sensitive pre-packaging counts and capacity estimate."""

    table_row_counts: dict[str, int]
    media_object_count: int
    media_bytes: int
    expected_bundle_bytes: int

    @property
    def minimum_headroom_bytes(self) -> int:
        """Return recommended free-space headroom for packaging."""
        return int(self.expected_bundle_bytes * HEADROOM_MULTIPLIER)


def build_dry_run_summary(
    *,
    table_row_counts: dict[str, int],
    media_object_count: int,
    media_bytes: int,
    database_dump_bytes: int,
) -> DryRunSummary:
    """Summarize one packaging dry run without sensitive payloads."""
    expected_bundle_bytes = database_dump_bytes + media_bytes
    return DryRunSummary(
        table_row_counts=dict(sorted(table_row_counts.items())),
        media_object_count=media_object_count,
        media_bytes=media_bytes,
        expected_bundle_bytes=expected_bundle_bytes,
    )


def forbidden_bundle_path(path: str) -> bool:
    """Return whether one candidate bundle path must be rejected."""
    normalized = path.lower()
    return any(fragment in normalized for fragment in FORBIDDEN_BUNDLE_PATH_FRAGMENTS)
