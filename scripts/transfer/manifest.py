"""Non-sensitive historical bundle manifest helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from scripts.transfer.constants import BUNDLE_SCHEMA, MIGRATION_HEAD, PIPELINE_ID

CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SOURCE_CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class BundleComponent:
    """One checksum-addressed bundle artifact."""

    name: str
    sha256: str
    size_bytes: int
    mode: str = "0600"


@dataclass(frozen=True, slots=True)
class MediaSummary:
    """Aggregate media counts without object paths."""

    restricted_original_count: int
    restricted_original_bytes: int
    public_derivative_count: int
    public_derivative_bytes: int


def create_manifest(
    *,
    source_checksum: str,
    release_sha: str,
    table_row_counts: dict[str, int],
    media: MediaSummary,
    components: tuple[BundleComponent, ...],
) -> dict[str, Any]:
    """Build one deterministic, non-sensitive bundle manifest."""
    if not SOURCE_CHECKSUM_PATTERN.fullmatch(source_checksum):
        msg = "source checksum must be 64 lowercase hexadecimal characters"
        raise ValueError(msg)
    if not CHECKSUM_PATTERN.fullmatch(release_sha):
        msg = "release SHA must be 64 lowercase hexadecimal characters"
        raise ValueError(msg)

    ordered_components = tuple(sorted(components, key=lambda component: component.name))
    ordered_counts = {key: table_row_counts[key] for key in sorted(table_row_counts)}

    return {
        "schema": BUNDLE_SCHEMA,
        "source_checksum": source_checksum,
        "pipeline_id": PIPELINE_ID,
        "migration_head": MIGRATION_HEAD,
        "release_sha": release_sha,
        "table_row_counts": ordered_counts,
        "media_summary": {
            "restricted_original_count": media.restricted_original_count,
            "restricted_original_bytes": media.restricted_original_bytes,
            "public_derivative_count": media.public_derivative_count,
            "public_derivative_bytes": media.public_derivative_bytes,
        },
        "components": [
            {
                "name": component.name,
                "sha256": component.sha256,
                "size_bytes": component.size_bytes,
                "mode": component.mode,
            }
            for component in ordered_components
        ],
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """Serialize one manifest deterministically."""
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Reject manifests that carry forbidden or malformed fields."""
    if manifest.get("schema") != BUNDLE_SCHEMA:
        msg = "manifest schema mismatch"
        raise ValueError(msg)
    if not SOURCE_CHECKSUM_PATTERN.fullmatch(str(manifest.get("source_checksum", ""))):
        msg = "manifest source checksum is invalid"
        raise ValueError(msg)
    forbidden_keys = {"database_url", "credentials", "contact", "raw_path"}
    if forbidden_keys.intersection(manifest.keys()):
        msg = "manifest contains forbidden sensitive keys"
        raise ValueError(msg)
