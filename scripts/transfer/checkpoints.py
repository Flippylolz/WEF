"""Resumable batch checkpoint helpers for candidate restore."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BatchCheckpoint:
    """One resumable restore checkpoint."""

    table: str
    completed_batches: int


def next_batch_index(checkpoint: BatchCheckpoint | None) -> int:
    """Return the next batch index to execute."""
    if checkpoint is None:
        return 0
    return checkpoint.completed_batches


def advance_checkpoint(
    checkpoint: BatchCheckpoint | None,
    *,
    table: str,
    batch_size: int,
    rows_remaining: int,
) -> BatchCheckpoint | None:
    """Advance one checkpoint or return None when the table is complete."""
    current = checkpoint or BatchCheckpoint(table=table, completed_batches=0)
    if current.table != table:
        msg = "checkpoint table mismatch"
        raise ValueError(msg)
    if rows_remaining <= 0:
        return None
    if batch_size <= 0:
        msg = "batch size must be positive"
        raise ValueError(msg)
    return BatchCheckpoint(table=table, completed_batches=current.completed_batches + 1)
