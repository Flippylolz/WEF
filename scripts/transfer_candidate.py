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
from scripts.transfer.restore import (
    RestorePreflightError,
    build_restore_plan,
    ensure_restore_allowed,
    iter_insert_batches,
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

    preflight = subparsers.add_parser(
        "restore-preflight",
        help="Classify fixture table snapshots and emit a checkpointed insert plan",
    )
    preflight.add_argument(
        "snapshots",
        type=Path,
        help=(
            "JSON object of table -> {existing: {key: payload}, incoming: {key: payload}}; "
            "keys may be strings or numbers"
        ),
    )
    preflight.add_argument("--batch-size", type=int, default=200)
    return parser


def _normalize_snapshot_map(raw: object) -> dict[object, object]:
    if not isinstance(raw, dict):
        msg = "snapshot maps must be JSON objects"
        raise TypeError(msg)
    normalized: dict[object, object] = {}
    for key, value in raw.items():
        if isinstance(key, str) and key.isdigit():
            normalized[int(key)] = value
        else:
            normalized[key] = value
    return normalized


def main(argv: list[str] | None = None) -> int:
    """Run one candidate verification subcommand."""
    arguments = _build_parser().parse_args(argv)

    if arguments.command == "reconcile":
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

    if arguments.command == "restore-preflight":
        raw = json.loads(arguments.snapshots.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            msg = "snapshots must be a JSON object"
            raise TypeError(msg)
        table_snapshots: dict[str, tuple[dict[object, object], dict[object, object]]] = {}
        for table, payload in raw.items():
            if not isinstance(table, str) or not isinstance(payload, dict):
                msg = "each table snapshot must be an object"
                raise TypeError(msg)
            table_snapshots[table] = (
                _normalize_snapshot_map(payload.get("existing", {})),
                _normalize_snapshot_map(payload.get("incoming", {})),
            )
        try:
            plan = build_restore_plan(
                table_snapshots=table_snapshots,
                batch_size=arguments.batch_size,
            )
            ensure_restore_allowed(plan)
            batches = iter_insert_batches(plan)
        except RestorePreflightError as error:
            sys.stdout.write(
                json.dumps(
                    {"allowed": False, "refusal_reasons": [str(error)]},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
            return 1
        payload = {
            "allowed": True,
            "batch_size": plan.batch_size,
            "total_new_rows": plan.total_new_rows,
            "tables": [
                {
                    "table": table.table,
                    "identical": table.identical,
                    "new": table.new,
                    "conflicting": table.conflicting,
                }
                for table in plan.tables
            ],
            "batches": [
                {
                    "table": batch.table,
                    "batch_index": batch.batch_index,
                    "key_count": len(batch.keys),
                }
                for batch in batches
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
