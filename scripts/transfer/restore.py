"""Staging restore preflight and checkpointed batch planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.transfer.batch_order import insert_order
from scripts.transfer.checkpoints import BatchCheckpoint, advance_checkpoint, next_batch_index
from scripts.transfer.conflicts import ConflictClass, classify_row, summarize_conflicts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class RestorePreflightError(ValueError):
    """Raised when restore preflight inputs are invalid or blocked."""


@dataclass(frozen=True, slots=True)
class TableRestorePlan:
    """One table's restore plan after conflict classification."""

    table: str
    identical: int
    new: int
    conflicting: int
    insert_keys: tuple[object, ...]

    @property
    def blocks_restore(self) -> bool:
        """Return whether conflicting rows block this table."""
        return self.conflicting > 0


@dataclass(frozen=True, slots=True)
class RestorePlan:
    """FK-safe multi-table restore plan for one candidate load."""

    tables: tuple[TableRestorePlan, ...]
    batch_size: int

    @property
    def blocks_restore(self) -> bool:
        """Return whether any table blocks the restore."""
        return any(table.blocks_restore for table in self.tables)

    @property
    def total_new_rows(self) -> int:
        """Return total insert rows across all tables."""
        return sum(table.new for table in self.tables)


@dataclass(frozen=True, slots=True)
class BatchSpec:
    """One bounded insert batch for a restore table."""

    table: str
    batch_index: int
    keys: tuple[object, ...]


def plan_table_restore(
    *,
    table: str,
    existing: Mapping[object, object],
    incoming: Mapping[object, object],
) -> TableRestorePlan:
    """Classify one table's keyed rows and collect insert keys for NEW rows only."""
    existing_index = {(table, key): value for key, value in existing.items()}
    classes: list[ConflictClass] = []
    insert_keys: list[object] = []
    for key, payload in sorted(incoming.items(), key=lambda item: repr(item[0])):
        outcome = classify_row(
            key=(table, key),
            existing=existing_index,
            incoming=payload,
        )
        classes.append(outcome)
        if outcome is ConflictClass.NEW:
            insert_keys.append(key)
    summary = summarize_conflicts(classes)
    return TableRestorePlan(
        table=table,
        identical=summary.identical,
        new=summary.new,
        conflicting=summary.conflicting,
        insert_keys=tuple(insert_keys),
    )


def build_restore_plan(
    *,
    table_snapshots: Mapping[str, tuple[Mapping[object, object], Mapping[object, object]]],
    batch_size: int,
    tables: Sequence[str] | None = None,
) -> RestorePlan:
    """Build one FK-safe restore plan; refuse creation when batch_size is invalid."""
    if batch_size <= 0:
        msg = "batch size must be positive"
        raise RestorePreflightError(msg)

    ordered = insert_order(tuple(tables) if tables is not None else None)
    missing = sorted(set(table_snapshots) - set(ordered))
    if missing:
        msg = f"unknown restore tables: {', '.join(missing)}"
        raise RestorePreflightError(msg)

    planned: list[TableRestorePlan] = []
    for table in ordered:
        if table not in table_snapshots:
            continue
        existing, incoming = table_snapshots[table]
        planned.append(
            plan_table_restore(table=table, existing=existing, incoming=incoming),
        )
    return RestorePlan(tables=tuple(planned), batch_size=batch_size)


def ensure_restore_allowed(plan: RestorePlan) -> None:
    """Raise when any conflicting row would make merge unsafe."""
    if plan.blocks_restore:
        blocked = [table.table for table in plan.tables if table.blocks_restore]
        msg = f"restore blocked by conflicting rows in: {', '.join(blocked)}"
        raise RestorePreflightError(msg)


def iter_insert_batches(
    plan: RestorePlan,
    *,
    checkpoints: Mapping[str, BatchCheckpoint] | None = None,
) -> list[BatchSpec]:
    """Return remaining insert batches in FK-safe order from optional checkpoints."""
    ensure_restore_allowed(plan)
    active = checkpoints or {}
    batches: list[BatchSpec] = []
    for table_plan in plan.tables:
        checkpoint = active.get(table_plan.table)
        start = next_batch_index(checkpoint) * plan.batch_size
        remaining_keys = table_plan.insert_keys[start:]
        offset = start
        while remaining_keys:
            chunk = remaining_keys[: plan.batch_size]
            batch_index = offset // plan.batch_size
            batches.append(
                BatchSpec(table=table_plan.table, batch_index=batch_index, keys=tuple(chunk)),
            )
            remaining_keys = remaining_keys[plan.batch_size :]
            offset += plan.batch_size
    return batches


def apply_batch_checkpoint(
    *,
    table: str,
    checkpoint: BatchCheckpoint | None,
    batch_size: int,
    rows_remaining_after_batch: int,
) -> BatchCheckpoint | None:
    """Advance one table checkpoint after a successful batch."""
    return advance_checkpoint(
        checkpoint,
        table=table,
        batch_size=batch_size,
        rows_remaining=rows_remaining_after_batch,
    )
