"""CLI for live Postgres candidate restore and resumable batch loading."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.transfer.postgres_restore import (
    PsqlTarget,
    RestoreCheckpointState,
    advance_restore_checkpoint,
    apply_batch,
    build_batch_insert_sql,
    build_restore_plan_from_snapshots,
    build_staging_setup_sql,
    build_staging_teardown_sql,
    checkpoint_file_path,
    export_restore_snapshots,
    load_checkpoint_state,
    parse_snapshot_map,
    rewrite_dump_for_staging,
    save_checkpoint_state,
)
from scripts.transfer.restore import (
    RestorePlan,
    RestorePreflightError,
    build_restore_plan,
    ensure_restore_allowed,
    iter_insert_batches,
)

SnapshotPayload = dict[str, tuple[dict[object, object], dict[object, object]]]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Historical candidate Postgres restore tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rewrite = subparsers.add_parser(
        "rewrite-dump",
        help="Rewrite one database.sql COPY target from public to the staging schema",
    )
    rewrite.add_argument("database_sql", type=Path)
    rewrite.add_argument("--staging-schema", default="wef_restore_staging")

    setup = subparsers.add_parser("staging-setup-sql", help="Render staging table setup SQL")
    setup.add_argument("--staging-schema", default="wef_restore_staging")

    teardown = subparsers.add_parser("staging-teardown-sql", help="Render staging teardown SQL")
    teardown.add_argument("--staging-schema", default="wef_restore_staging")

    preflight = subparsers.add_parser(
        "preflight",
        help="Classify exported or live Postgres snapshots and emit a batch plan",
    )
    preflight.add_argument(
        "--snapshots",
        type=Path,
        help="JSON object of table -> {existing: {...}, incoming: {...}}",
    )
    preflight.add_argument("--batch-size", type=int, default=200)
    preflight.add_argument("--container", help="Docker Postgres container for live export")
    preflight.add_argument("--database", help="Candidate database name for live export")
    preflight.add_argument("--psql-user", default="wef")
    preflight.add_argument("--staging-schema", default="wef_restore_staging")

    batch_sql = subparsers.add_parser("batch-sql", help="Render INSERT SQL for one restore batch")
    batch_sql.add_argument("table")
    batch_sql.add_argument("keys", help="Comma-separated primary-key values or JSON array")
    batch_sql.add_argument("--staging-schema", default="wef_restore_staging")

    apply_one = subparsers.add_parser("apply-batch", help="Apply one restore batch through psql")
    apply_one.add_argument("table")
    apply_one.add_argument("keys", help="Comma-separated primary-key values or JSON array")
    apply_one.add_argument("--container", required=True)
    apply_one.add_argument("--database", required=True)
    apply_one.add_argument("--psql-user", default="wef")
    apply_one.add_argument("--staging-schema", default="wef_restore_staging")

    run = subparsers.add_parser(
        "run",
        help="Apply all remaining restore batches from one checkpoint file",
    )
    run.add_argument("--wef-root", type=Path, required=True)
    run.add_argument("--source-checksum", required=True)
    run.add_argument("--container", required=True)
    run.add_argument("--database", required=True)
    run.add_argument("--snapshots", type=Path, required=True)
    run.add_argument("--psql-user", default="wef")
    run.add_argument("--staging-schema", default="wef_restore_staging")
    run.add_argument("--batch-size", type=int, default=200)
    run.add_argument("--dry-run", action="store_true")

    return parser


def _parse_keys(_table: str, raw: str) -> tuple[object, ...]:
    trimmed = raw.strip()
    if trimmed.startswith("["):
        parsed = json.loads(trimmed)
        if not isinstance(parsed, list):
            msg = "batch keys JSON must be an array"
            raise TypeError(msg)
        return tuple(parsed)
    if "," in trimmed:
        return tuple(part.strip() for part in trimmed.split(",") if part.strip())
    return (trimmed,)


def _load_snapshot_payload(path: Path) -> SnapshotPayload:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "snapshots must be a JSON object"
        raise TypeError(msg)
    table_snapshots: SnapshotPayload = {}
    for table, payload in raw.items():
        if not isinstance(table, str) or not isinstance(payload, dict):
            msg = "each table snapshot must be an object"
            raise TypeError(msg)
        table_snapshots[table] = (
            parse_snapshot_map(payload.get("existing", {})),
            parse_snapshot_map(payload.get("incoming", {})),
        )
    return table_snapshots


def _render_plan_payload(plan: RestorePlan) -> dict[str, Any]:
    batches = iter_insert_batches(plan)
    return {
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
                "keys": list(batch.keys),
            }
            for batch in batches
        ],
    }


def _run_rewrite_dump(arguments: argparse.Namespace) -> int:
    rewritten = rewrite_dump_for_staging(
        arguments.database_sql.read_text(encoding="utf-8"),
        staging_schema=arguments.staging_schema,
    )
    sys.stdout.write(rewritten)
    return 0


def _run_preflight(arguments: argparse.Namespace) -> int:
    if arguments.snapshots is not None:
        table_snapshots = _load_snapshot_payload(arguments.snapshots)
    elif arguments.container and arguments.database:
        target = PsqlTarget(
            container=arguments.container,
            user=arguments.psql_user,
            database=arguments.database,
        )
        table_snapshots = export_restore_snapshots(
            target,
            staging_schema=arguments.staging_schema,
        )
    else:
        msg = "preflight requires --snapshots or live --container and --database"
        raise SystemExit(msg)
    try:
        plan = build_restore_plan(
            table_snapshots=table_snapshots,
            batch_size=arguments.batch_size,
        )
        ensure_restore_allowed(plan)
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
    sys.stdout.write(json.dumps(_render_plan_payload(plan), indent=2, sort_keys=True) + "\n")
    return 0


def _run_apply_batch(arguments: argparse.Namespace) -> int:
    keys = _parse_keys(arguments.table, arguments.keys)
    apply_batch(
        PsqlTarget(
            container=arguments.container,
            user=arguments.psql_user,
            database=arguments.database,
        ),
        table=arguments.table,
        keys=keys,
        staging_schema=arguments.staging_schema,
    )
    return 0


def _run_restore(arguments: argparse.Namespace) -> int:
    table_snapshots = _load_snapshot_payload(arguments.snapshots)
    checkpoint_path = checkpoint_file_path(arguments.wef_root, arguments.source_checksum)
    state = (
        load_checkpoint_state(checkpoint_path)
        if checkpoint_path.is_file()
        else RestoreCheckpointState(
            source_checksum=arguments.source_checksum,
            candidate_database=arguments.database,
            batch_size=arguments.batch_size,
            checkpoints={},
        )
    )
    plan = build_restore_plan_from_snapshots(
        table_snapshots=table_snapshots,
        batch_size=state.batch_size,
    )
    target = PsqlTarget(
        container=arguments.container,
        user=arguments.psql_user,
        database=arguments.database,
    )
    remaining = iter_insert_batches(plan, checkpoints=state.checkpoints)
    if arguments.dry_run:
        payload = {
            "remaining_batches": len(remaining),
            "checkpoint_file": str(checkpoint_path),
            "batches": [
                {
                    "table": batch.table,
                    "batch_index": batch.batch_index,
                    "key_count": len(batch.keys),
                }
                for batch in remaining
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    for batch in remaining:
        apply_batch(
            target,
            table=batch.table,
            keys=batch.keys,
            staging_schema=arguments.staging_schema,
        )
        table_plan = next(item for item in plan.tables if item.table == batch.table)
        completed_keys = (batch.batch_index + 1) * plan.batch_size
        rows_remaining = max(table_plan.new - completed_keys, 0)
        state = advance_restore_checkpoint(
            state,
            table=batch.table,
            batch_size=plan.batch_size,
            rows_remaining_after_batch=rows_remaining,
        )
        save_checkpoint_state(checkpoint_path, state)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run one Postgres restore subcommand."""
    arguments = _build_parser().parse_args(argv)
    handlers: dict[str, Any] = {
        "rewrite-dump": _run_rewrite_dump,
        "preflight": _run_preflight,
        "apply-batch": _run_apply_batch,
        "run": _run_restore,
    }
    handler = handlers.get(arguments.command)
    if handler is not None:
        result: int = handler(arguments)
        return result
    if arguments.command == "staging-setup-sql":
        sys.stdout.write(build_staging_setup_sql(staging_schema=arguments.staging_schema))
        return 0
    if arguments.command == "staging-teardown-sql":
        sys.stdout.write(build_staging_teardown_sql(staging_schema=arguments.staging_schema))
        return 0
    if arguments.command == "batch-sql":
        keys = _parse_keys(arguments.table, arguments.keys)
        sys.stdout.write(
            build_batch_insert_sql(
                table=arguments.table,
                keys=keys,
                staging_schema=arguments.staging_schema,
            ),
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
