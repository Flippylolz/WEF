"""CLI for non-public historical candidate reconciliation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.deploy.candidate_config import candidate_paths
from scripts.transfer.reconcile import (
    MediaCounts,
    count_media_files,
    load_bundle_manifest,
    reconcile_candidate,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Historical candidate verification tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reconcile = subparsers.add_parser(
        "reconcile",
        help="Reconcile candidate counts and media against one verified bundle",
    )
    reconcile.add_argument("bundle_dir", type=Path)
    reconcile.add_argument(
        "--table-counts",
        type=Path,
        required=True,
        help="JSON object of candidate table_name -> row count",
    )
    reconcile.add_argument(
        "--wef-root",
        type=Path,
        required=True,
        help="WEF root used to locate checksum-scoped candidate media",
    )
    reconcile.add_argument(
        "--production-source-messages",
        type=int,
        required=True,
        help="Live public wef.source_messages count (must remain 0 until E7-T11)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one candidate verification subcommand."""
    arguments = _build_parser().parse_args(argv)
    if arguments.command != "reconcile":
        return 1

    manifest = load_bundle_manifest(arguments.bundle_dir)
    table_payload = json.loads(arguments.table_counts.read_text(encoding="utf-8"))
    if not isinstance(table_payload, dict):
        msg = "table counts must be a JSON object"
        raise TypeError(msg)
    table_row_counts = {str(key): int(value) for key, value in table_payload.items()}

    paths = candidate_paths(arguments.wef_root, str(manifest["source_checksum"]))
    media_counts = MediaCounts(
        restricted_original_count=count_media_files(paths.restricted_originals),
        public_derivative_count=count_media_files(paths.public_derivatives),
    )
    summary = reconcile_candidate(
        manifest=manifest,
        table_row_counts=table_row_counts,
        media_counts=media_counts,
        production_source_messages=arguments.production_source_messages,
    )
    payload = {
        "allowed": summary.allowed,
        "refusal_reasons": list(summary.refusal_reasons),
        "source_checksum": summary.source_checksum,
        "migration_head": summary.migration_head,
        "pipeline_id": summary.pipeline_id,
        "table_mismatches": list(summary.table_mismatches),
        "media_mismatches": list(summary.media_mismatches),
        "media_counts": {
            "restricted_original_count": media_counts.restricted_original_count,
            "public_derivative_count": media_counts.public_derivative_count,
        },
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if summary.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
