"""Non-public candidate reconciliation against a verified bundle manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scripts.transfer.bundle import BUNDLE_MANIFEST_NAME
from scripts.transfer.constants import EXCLUDED_TABLES, MIGRATION_HEAD, PIPELINE_ID
from scripts.transfer.manifest import validate_manifest

if TYPE_CHECKING:
    from pathlib import Path


class CandidateReconcileError(ValueError):
    """Raised when candidate reconciliation inputs or results are invalid."""


@dataclass(frozen=True, slots=True)
class MediaCounts:
    """Filesystem media object counts for one candidate media tree pair."""

    restricted_original_count: int
    public_derivative_count: int


@dataclass(frozen=True, slots=True)
class ReconcileSummary:
    """Non-sensitive result of one candidate reconciliation."""

    allowed: bool
    refusal_reasons: tuple[str, ...]
    source_checksum: str
    migration_head: str
    pipeline_id: str
    table_mismatches: tuple[str, ...]
    media_mismatches: tuple[str, ...]


def load_bundle_manifest(bundle_dir: Path) -> dict[str, Any]:
    """Load and validate one on-disk bundle manifest."""
    manifest_path = bundle_dir / BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        msg = "bundle is missing manifest.json"
        raise CandidateReconcileError(msg)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "bundle manifest must be a JSON object"
        raise CandidateReconcileError(msg)
    validate_manifest(payload)
    return payload


def count_media_files(root: Path) -> int:
    """Count regular files beneath one media root; reject symlinks."""
    if not root.is_dir():
        msg = f"media root must be a directory: {root}"
        raise CandidateReconcileError(msg)
    count = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            msg = f"media tree must not contain symlinks: {path}"
            raise CandidateReconcileError(msg)
        if path.is_file():
            count += 1
    return count


def _table_mismatches(
    expected_tables: dict[str, Any],
    table_row_counts: dict[str, int],
) -> list[str]:
    mismatches: list[str] = []
    for table, expected in sorted(expected_tables.items()):
        if not isinstance(table, str) or not isinstance(expected, int):
            msg = "manifest table_row_counts entries must be string:int pairs"
            raise CandidateReconcileError(msg)
        actual = table_row_counts.get(table)
        if actual is None:
            mismatches.append(f"{table}:missing")
        elif actual != expected:
            mismatches.append(f"{table}:{actual}!={expected}")
    unexpected = sorted(set(table_row_counts) - set(expected_tables))
    mismatches.extend(f"{table}:unexpected" for table in unexpected)
    return mismatches


def _media_mismatches(media: dict[str, Any], media_counts: MediaCounts) -> list[str]:
    mismatches: list[str] = []
    expected_originals = int(media["restricted_original_count"])
    expected_derivatives = int(media["public_derivative_count"])
    if media_counts.restricted_original_count != expected_originals:
        mismatches.append(
            f"restricted_originals:{media_counts.restricted_original_count}!={expected_originals}",
        )
    if media_counts.public_derivative_count != expected_derivatives:
        mismatches.append(
            f"public_derivatives:{media_counts.public_derivative_count}!={expected_derivatives}",
        )
    return mismatches


def reconcile_candidate(
    *,
    manifest: dict[str, Any],
    table_row_counts: dict[str, int],
    media_counts: MediaCounts,
    production_source_messages: int,
) -> ReconcileSummary:
    """Compare candidate aggregates to the verified bundle without mutating state."""
    refusal_reasons: list[str] = []
    source_checksum = str(manifest.get("source_checksum", ""))
    migration_head = str(manifest.get("migration_head", ""))
    pipeline_id = str(manifest.get("pipeline_id", ""))

    if migration_head != MIGRATION_HEAD:
        refusal_reasons.append("candidate migration head does not match released head")
    if pipeline_id != PIPELINE_ID:
        refusal_reasons.append("candidate pipeline id does not match released pipeline")
    if production_source_messages != 0:
        refusal_reasons.append("public production still exposes historical source messages")

    expected_tables = manifest.get("table_row_counts")
    if not isinstance(expected_tables, dict):
        msg = "manifest is missing table_row_counts"
        raise CandidateReconcileError(msg)
    media = manifest.get("media_summary")
    if not isinstance(media, dict):
        msg = "manifest is missing media_summary"
        raise CandidateReconcileError(msg)

    table_mismatches = _table_mismatches(expected_tables, table_row_counts)
    media_mismatches = _media_mismatches(media, media_counts)
    refusal_reasons.extend(
        f"excluded table present in candidate counts: {table}"
        for table in EXCLUDED_TABLES
        if table in table_row_counts
    )
    if table_mismatches:
        refusal_reasons.append("candidate table counts do not match bundle manifest")
    if media_mismatches:
        refusal_reasons.append("candidate media counts do not match bundle manifest")

    return ReconcileSummary(
        allowed=not refusal_reasons,
        refusal_reasons=tuple(sorted(refusal_reasons)),
        source_checksum=source_checksum,
        migration_head=migration_head,
        pipeline_id=pipeline_id,
        table_mismatches=tuple(table_mismatches),
        media_mismatches=tuple(media_mismatches),
    )
