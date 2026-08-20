"""Live Postgres staging restore helpers for candidate database loading."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scripts.transfer.batch_order import insert_order
from scripts.transfer.checkpoints import BatchCheckpoint
from scripts.transfer.constants import INCLUDED_TABLES
from scripts.transfer.restore import (
    RestorePlan,
    RestorePreflightError,
    apply_batch_checkpoint,
    build_restore_plan,
    ensure_restore_allowed,
)
from scripts.transfer.table_keys import TABLE_PRIMARY_KEYS

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

# Operator-owned SQL is assembled only from validated restore table identifiers.
# ruff: noqa: S608

STAGING_SCHEMA = "wef_restore_staging"
CHECKPOINT_SCHEMA = "wef-restore-checkpoints@1"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COPY_PUBLIC_PATTERN = re.compile(
    r"^COPY public\.([a-z_]+)\s",
    flags=re.MULTILINE,
)


class PostgresRestoreError(RuntimeError):
    """Raised when Postgres restore inputs or execution fail."""


@dataclass(frozen=True, slots=True)
class PsqlTarget:
    """One dockerized Postgres psql target."""

    container: str
    user: str
    database: str


@dataclass(frozen=True, slots=True)
class RestoreCheckpointState:
    """Persisted resumable restore checkpoint file."""

    source_checksum: str
    candidate_database: str
    batch_size: int
    checkpoints: dict[str, BatchCheckpoint]


def rewrite_dump_for_staging(sql_text: str, *, staging_schema: str = STAGING_SCHEMA) -> str:
    """Rewrite one pg_dump COPY target from public to the staging schema."""
    if not staging_schema.replace("_", "").isalnum():
        msg = "staging schema name is invalid"
        raise PostgresRestoreError(msg)
    return COPY_PUBLIC_PATTERN.sub(rf"COPY {staging_schema}.\1 ", sql_text)


def build_staging_setup_sql(
    *,
    tables: Sequence[str] | None = None,
    staging_schema: str = STAGING_SCHEMA,
) -> str:
    """Return SQL that recreates empty staging tables for one restore."""
    selected = insert_order(tuple(tables) if tables is not None else None)
    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {staging_schema};",
    ]
    for table in selected:
        statements.extend(
            [
                f"DROP TABLE IF EXISTS {staging_schema}.{table} CASCADE;",
                (
                    f"CREATE TABLE {staging_schema}.{table} "
                    f"(LIKE public.{table} INCLUDING DEFAULTS INCLUDING CONSTRAINTS);"
                ),
            ],
        )
    return "\n".join(statements) + "\n"


def build_staging_teardown_sql(
    *,
    tables: Sequence[str] | None = None,
    staging_schema: str = STAGING_SCHEMA,
) -> str:
    """Return SQL that drops staging tables after a successful restore."""
    selected = reversed(insert_order(tuple(tables) if tables is not None else None))
    statements = [f"DROP TABLE IF EXISTS {staging_schema}.{table} CASCADE;" for table in selected]
    statements.append(f"DROP SCHEMA IF EXISTS {staging_schema} CASCADE;")
    return "\n".join(statements) + "\n"


def encode_row_key(table: str, values: Sequence[object]) -> object:
    """Encode one primary-key tuple into the restore planner key shape."""
    columns = TABLE_PRIMARY_KEYS[table]
    if len(columns) != len(values):
        msg = f"primary-key value count mismatch for {table}"
        raise PostgresRestoreError(msg)
    if len(columns) == 1:
        return values[0]
    return tuple(values)


def decode_row_key(table: str, key: object) -> tuple[object, ...]:
    """Decode one restore planner key back into SQL literal components."""
    columns = TABLE_PRIMARY_KEYS[table]
    if len(columns) == 1:
        if isinstance(key, tuple):
            msg = f"expected scalar primary key for {table}"
            raise PostgresRestoreError(msg)
        return (key,)
    if not isinstance(key, tuple) or len(key) != len(columns):
        msg = f"expected composite primary key for {table}"
        raise PostgresRestoreError(msg)
    return key


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _row_payload_expression(table: str, alias: str) -> str:
    columns = TABLE_PRIMARY_KEYS[table]
    if len(columns) == 1:
        column = columns[0]
        return f"to_jsonb({alias}) - '{column}'"
    remove = ", ".join(f"'{column}'" for column in columns)
    return f"to_jsonb({alias}) - ARRAY[{remove}]::text[]"


def _key_projection(table: str, alias: str) -> str:
    columns = TABLE_PRIMARY_KEYS[table]
    if len(columns) == 1:
        column = columns[0]
        return f"{alias}.{column}::text"
    parts = ", ".join(f"{alias}.{column}" for column in columns)
    return f"jsonb_build_array({parts})::text"


def _validate_identifier(name: str, *, label: str) -> None:
    if not IDENTIFIER_PATTERN.fullmatch(name):
        msg = f"invalid {label}: {name}"
        raise PostgresRestoreError(msg)


def _validate_table_schema(table: str, schema: str) -> None:
    if table not in TABLE_PRIMARY_KEYS:
        msg = f"unknown restore table: {table}"
        raise PostgresRestoreError(msg)
    _validate_identifier(schema, label="schema name")


def build_snapshot_export_sql(
    *,
    table: str,
    schema: str,
) -> str:
    """Return SQL exporting one keyed snapshot map as JSON."""
    _validate_table_schema(table, schema)
    payload = _row_payload_expression(table, "row_data")
    key_expr = _key_projection(table, "row_data")
    return (
        "SELECT COALESCE("
        f"jsonb_object_agg(key_value, {payload}), '{{}}'::jsonb)::text "
        f"FROM (SELECT {key_expr} AS key_value, t AS row_data FROM {schema}.{table} t) keyed;"
    )


def parse_snapshot_map(raw: object) -> dict[object, object]:
    """Normalize one exported snapshot map for restore planning."""
    if not isinstance(raw, dict):
        msg = "snapshot export must be a JSON object"
        raise PostgresRestoreError(msg)
    normalized: dict[object, object] = {}
    for key, value in raw.items():
        parsed_key: object = key
        if isinstance(key, str):
            if key.startswith("[") and key.endswith("]"):
                parsed_key = tuple(json.loads(key))
            elif key.isdigit():
                parsed_key = int(key)
        normalized[parsed_key] = value
    return normalized


def build_table_snapshots(
    *,
    existing_by_table: Mapping[str, Mapping[object, object]],
    incoming_by_table: Mapping[str, Mapping[object, object]],
) -> dict[str, tuple[dict[object, object], dict[object, object]]]:
    """Pair existing and incoming keyed snapshots for restore planning."""
    snapshots: dict[str, tuple[dict[object, object], dict[object, object]]] = {}
    for table in insert_order(INCLUDED_TABLES):
        if table not in incoming_by_table and table not in existing_by_table:
            continue
        snapshots[table] = (
            dict(existing_by_table.get(table, {})),
            dict(incoming_by_table.get(table, {})),
        )
    return snapshots


def build_restore_plan_from_snapshots(
    *,
    table_snapshots: Mapping[str, tuple[Mapping[object, object], Mapping[object, object]]],
    batch_size: int,
) -> RestorePlan:
    """Build one restore plan from exported table snapshots."""
    try:
        plan = build_restore_plan(
            table_snapshots=dict(table_snapshots),
            batch_size=batch_size,
        )
        ensure_restore_allowed(plan)
    except RestorePreflightError as error:
        raise PostgresRestoreError(str(error)) from error
    return plan


def build_batch_insert_sql(
    *,
    table: str,
    keys: Sequence[object],
    staging_schema: str = STAGING_SCHEMA,
    target_schema: str = "public",
) -> str:
    """Return SQL inserting one bounded batch of staged rows into the target schema."""
    if table not in TABLE_PRIMARY_KEYS:
        msg = f"unknown restore table: {table}"
        raise PostgresRestoreError(msg)
    _validate_identifier(staging_schema, label="staging schema name")
    _validate_identifier(target_schema, label="target schema name")
    if not keys:
        msg = "batch insert requires at least one key"
        raise PostgresRestoreError(msg)

    columns = TABLE_PRIMARY_KEYS[table]
    if len(columns) == 1:
        column = columns[0]
        literals = ", ".join(_sql_literal(decode_row_key(table, key)[0]) for key in keys)
        predicate = f"s.{column} IN ({literals})"
    else:
        tuples = []
        for key in keys:
            values = decode_row_key(table, key)
            tuples.append(f"({', '.join(_sql_literal(value) for value in values)})")
        predicate = f"({', '.join(f's.{column}' for column in columns)}) IN ({', '.join(tuples)})"

    return (
        f"INSERT INTO {target_schema}.{table}\n"
        f"SELECT s.*\n"
        f"FROM {staging_schema}.{table} s\n"
        f"WHERE {predicate}\n"
        f"ON CONFLICT DO NOTHING;\n"
    )


def checkpoint_file_path(wef_root: Path, source_checksum: str) -> Path:
    """Return the default checkpoint file path for one restore."""
    return wef_root / "state" / f"restore-checkpoints-{source_checksum}.json"


def load_checkpoint_state(path: Path) -> RestoreCheckpointState:
    """Load one checkpoint file from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != CHECKPOINT_SCHEMA:
        msg = "checkpoint file schema mismatch"
        raise PostgresRestoreError(msg)
    checkpoints_raw = payload.get("checkpoints")
    if not isinstance(checkpoints_raw, dict):
        msg = "checkpoint file is missing checkpoints"
        raise PostgresRestoreError(msg)
    checkpoints: dict[str, BatchCheckpoint] = {}
    for table, item in checkpoints_raw.items():
        if not isinstance(table, str) or not isinstance(item, dict):
            msg = "checkpoint entries must be table -> object"
            raise PostgresRestoreError(msg)
        checkpoints[table] = BatchCheckpoint(
            table=table,
            completed_batches=int(item["completed_batches"]),
        )
    return RestoreCheckpointState(
        source_checksum=str(payload["source_checksum"]),
        candidate_database=str(payload["candidate_database"]),
        batch_size=int(payload["batch_size"]),
        checkpoints=checkpoints,
    )


def render_checkpoint_state(state: RestoreCheckpointState) -> str:
    """Render one checkpoint file payload."""
    payload: dict[str, Any] = {
        "schema": CHECKPOINT_SCHEMA,
        "source_checksum": state.source_checksum,
        "candidate_database": state.candidate_database,
        "batch_size": state.batch_size,
        "checkpoints": {
            table: {
                "table": checkpoint.table,
                "completed_batches": checkpoint.completed_batches,
            }
            for table, checkpoint in sorted(state.checkpoints.items())
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def save_checkpoint_state(path: Path, state: RestoreCheckpointState) -> None:
    """Persist one checkpoint file with restrictive permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_checkpoint_state(state), encoding="utf-8")
    path.chmod(0o600)


def run_psql(target: PsqlTarget, sql: str, *, tuples_only: bool = False) -> str:
    """Execute one SQL statement through dockerized psql."""
    command = [
        "docker",
        "exec",
        "-i",
        target.container,
        "psql",
        "-U",
        target.user,
        "-d",
        target.database,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        command.extend(["-t", "-A"])
    completed = subprocess.run(  # noqa: S603
        command,
        input=sql,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        msg = f"psql failed: {detail}"
        raise PostgresRestoreError(msg)
    return completed.stdout.strip()


def export_schema_snapshots(
    target: PsqlTarget,
    *,
    schema: str,
    tables: Sequence[str] | None = None,
) -> dict[str, dict[object, object]]:
    """Export keyed snapshots for one schema from live Postgres."""
    selected = insert_order(tuple(tables) if tables is not None else None)
    snapshots: dict[str, dict[object, object]] = {}
    for table in selected:
        raw = run_psql(
            target,
            build_snapshot_export_sql(table=table, schema=schema),
            tuples_only=True,
        )
        parsed = json.loads(raw or "{}")
        snapshots[table] = parse_snapshot_map(parsed)
    return snapshots


def export_restore_snapshots(
    target: PsqlTarget,
    *,
    staging_schema: str = STAGING_SCHEMA,
    target_schema: str = "public",
) -> dict[str, tuple[dict[object, object], dict[object, object]]]:
    """Export existing/incoming table snapshots from one candidate database."""
    existing = export_schema_snapshots(target, schema=target_schema)
    incoming = export_schema_snapshots(target, schema=staging_schema)
    return build_table_snapshots(existing_by_table=existing, incoming_by_table=incoming)


def apply_batch(
    target: PsqlTarget,
    *,
    table: str,
    keys: Sequence[object],
    staging_schema: str = STAGING_SCHEMA,
    target_schema: str = "public",
) -> None:
    """Insert one restore batch into the live candidate database."""
    sql = build_batch_insert_sql(
        table=table,
        keys=keys,
        staging_schema=staging_schema,
        target_schema=target_schema,
    )
    run_psql(target, sql)


def advance_restore_checkpoint(
    state: RestoreCheckpointState,
    *,
    table: str,
    batch_size: int,
    rows_remaining_after_batch: int,
) -> RestoreCheckpointState:
    """Return updated checkpoint state after one successful batch."""
    checkpoints = dict(state.checkpoints)
    advanced = apply_batch_checkpoint(
        table=table,
        checkpoint=checkpoints.get(table),
        batch_size=batch_size,
        rows_remaining_after_batch=rows_remaining_after_batch,
    )
    if advanced is None:
        checkpoints.pop(table, None)
    else:
        checkpoints[table] = advanced
    return RestoreCheckpointState(
        source_checksum=state.source_checksum,
        candidate_database=state.candidate_database,
        batch_size=state.batch_size,
        checkpoints=checkpoints,
    )
