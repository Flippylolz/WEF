"""Tests for staging restore preflight and checkpointed batch planning."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import unittest

from scripts.transfer.checkpoints import BatchCheckpoint
from scripts.transfer.restore import (
    RestorePreflightError,
    apply_batch_checkpoint,
    build_restore_plan,
    ensure_restore_allowed,
    iter_insert_batches,
)


class RestorePreflightTests(unittest.TestCase):
    """Verify conflict-gated restore planning and checkpoint resume."""

    def test_plan_classifies_identical_new_and_conflict(self) -> None:
        plan = build_restore_plan(
            table_snapshots={
                "locations": (
                    {1: {"name": "a"}, 2: {"name": "b"}},
                    {1: {"name": "a"}, 2: {"name": "B"}, 3: {"name": "c"}},
                ),
                "offers": (
                    {},
                    {10: {"location_id": 3}},
                ),
            },
            batch_size=10,
            tables=("locations", "offers"),
        )
        by_table = {table.table: table for table in plan.tables}
        self.assertEqual(by_table["locations"].identical, 1)
        self.assertEqual(by_table["locations"].new, 1)
        self.assertEqual(by_table["locations"].conflicting, 1)
        self.assertEqual(by_table["offers"].new, 1)
        self.assertTrue(plan.blocks_restore)
        with self.assertRaises(RestorePreflightError):
            ensure_restore_allowed(plan)

    def test_batches_follow_fk_order_and_resume_from_checkpoint(self) -> None:
        plan = build_restore_plan(
            table_snapshots={
                "locations": ({}, {1: {"name": "a"}, 2: {"name": "b"}, 3: {"name": "c"}}),
                "offers": ({}, {10: {"location_id": 1}, 11: {"location_id": 2}}),
            },
            batch_size=2,
            tables=("locations", "offers"),
        )
        ensure_restore_allowed(plan)
        first_pass = iter_insert_batches(plan)
        self.assertEqual(
            [batch.table for batch in first_pass],
            ["locations", "locations", "offers"],
        )
        self.assertEqual(first_pass[0].keys, (1, 2))
        self.assertEqual(first_pass[1].keys, (3,))

        resumed = iter_insert_batches(
            plan,
            checkpoints={"locations": BatchCheckpoint(table="locations", completed_batches=1)},
        )
        self.assertEqual(resumed[0].table, "locations")
        self.assertEqual(resumed[0].batch_index, 1)
        self.assertEqual(resumed[0].keys, (3,))
        self.assertEqual(resumed[1].table, "offers")

        advanced = apply_batch_checkpoint(
            table="locations",
            checkpoint=BatchCheckpoint(table="locations", completed_batches=1),
            batch_size=2,
            rows_remaining_after_batch=0,
        )
        self.assertIsNone(advanced)


if __name__ == "__main__":
    unittest.main()
