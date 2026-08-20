"""Tests for live Postgres restore helpers and operator CLI."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.transfer.checkpoints import BatchCheckpoint
from scripts.transfer.postgres_restore import (
    PostgresRestoreError,
    RestoreCheckpointState,
    advance_restore_checkpoint,
    build_batch_insert_sql,
    build_restore_plan_from_snapshots,
    build_snapshot_export_sql,
    build_staging_setup_sql,
    build_table_snapshots,
    checkpoint_file_path,
    load_checkpoint_state,
    parse_snapshot_map,
    rewrite_dump_for_staging,
    save_checkpoint_state,
)
from scripts.transfer_restore import main as transfer_restore_main


class PostgresRestoreTests(unittest.TestCase):
    """Verify staging SQL generation and snapshot-driven restore planning."""

    def test_rewrite_dump_targets_staging_schema(self) -> None:
        sql = "COPY public.locations (id) FROM stdin;\nCOPY public.offers (id) FROM stdin;\n"
        rewritten = rewrite_dump_for_staging(sql)
        self.assertIn("COPY wef_restore_staging.locations", rewritten)
        self.assertIn("COPY wef_restore_staging.offers", rewritten)
        self.assertNotIn("COPY public.locations", rewritten)

    def test_staging_setup_sql_creates_all_included_tables(self) -> None:
        sql = build_staging_setup_sql()
        self.assertIn("CREATE SCHEMA IF NOT EXISTS wef_restore_staging;", sql)
        self.assertIn("CREATE TABLE wef_restore_staging.locations", sql)
        self.assertIn("CREATE TABLE wef_restore_staging.offer_media", sql)

    def test_snapshot_export_sql_uses_primary_key_projection(self) -> None:
        single = build_snapshot_export_sql(table="locations", schema="public")
        self.assertIn("row_data.id::text", single)
        composite = build_snapshot_export_sql(table="offer_media", schema="wef_restore_staging")
        self.assertIn("jsonb_build_array", composite)

    def test_build_batch_insert_sql_for_scalar_and_composite_keys(self) -> None:
        scalar = build_batch_insert_sql(
            table="locations",
            keys=("11111111-1111-4111-8111-111111111111",),
        )
        self.assertIn("INSERT INTO public.locations", scalar)
        self.assertIn("ON CONFLICT DO NOTHING", scalar)
        composite = build_batch_insert_sql(
            table="offer_media",
            keys=(
                (
                    "22222222-2222-4222-8222-222222222222",
                    "33333333-3333-4333-8333-333333333333",
                ),
            ),
        )
        self.assertIn("offer_id", composite)
        self.assertIn("media_asset_id", composite)

    def test_plan_from_snapshots_refuses_conflicts(self) -> None:
        snapshots = build_table_snapshots(
            existing_by_table={"locations": {1: {"name": "a"}}},
            incoming_by_table={"locations": {1: {"name": "A"}, 2: {"name": "b"}}},
        )
        with self.assertRaises(PostgresRestoreError):
            build_restore_plan_from_snapshots(table_snapshots=snapshots, batch_size=10)

    def test_checkpoint_file_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = checkpoint_file_path(root, "a" * 64)
            state = RestoreCheckpointState(
                source_checksum="a" * 64,
                candidate_database="wef_hist_candidate",
                batch_size=200,
                checkpoints={"locations": BatchCheckpoint(table="locations", completed_batches=1)},
            )
            save_checkpoint_state(path, state)
            loaded = load_checkpoint_state(path)
            self.assertEqual(loaded.batch_size, 200)
            self.assertEqual(loaded.checkpoints["locations"].completed_batches, 1)

    def test_advance_restore_checkpoint_clears_completed_table(self) -> None:
        state = RestoreCheckpointState(
            source_checksum="a" * 64,
            candidate_database="wef_hist_candidate",
            batch_size=2,
            checkpoints={"locations": BatchCheckpoint(table="locations", completed_batches=1)},
        )
        advanced = advance_restore_checkpoint(
            state,
            table="locations",
            batch_size=2,
            rows_remaining_after_batch=0,
        )
        self.assertNotIn("locations", advanced.checkpoints)

    def test_parse_snapshot_map_decodes_composite_keys(self) -> None:
        parsed = parse_snapshot_map(
            {
                "11111111-1111-4111-8111-111111111111": {"display_name": "a"},
                '["22222222-2222-4222-8222-222222222222","33333333-3333-4333-8333-333333333333"]': {
                    "position": 0,
                },
            },
        )
        self.assertIn("11111111-1111-4111-8111-111111111111", parsed)
        self.assertIn(
            ("22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"),
            parsed,
        )


class TransferRestoreCliTests(unittest.TestCase):
    """Verify operator CLI surfaces for Postgres restore."""

    def test_preflight_from_fixture_snapshots(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.json"
            path.write_text(
                json.dumps(
                    {
                        "locations": {
                            "existing": {},
                            "incoming": {"1": {"name": "a"}, "2": {"name": "b"}},
                        },
                        "offers": {
                            "existing": {},
                            "incoming": {"10": {"location_id": 2}},
                        },
                    },
                )
                + "\n",
                encoding="utf-8",
            )
            buffer = StringIO()
            with mock.patch("sys.stdout", buffer):
                exit_code = transfer_restore_main(
                    ["preflight", "--snapshots", str(path), "--batch-size", "1"],
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["allowed"])
            self.assertEqual(payload["total_new_rows"], 3)
            self.assertEqual(len(payload["batches"]), 3)

    def test_rewrite_dump_cli(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "database.sql"
            path.write_text("COPY public.offers (id) FROM stdin;\n", encoding="utf-8")
            buffer = StringIO()
            with mock.patch("sys.stdout", buffer):
                exit_code = transfer_restore_main(["rewrite-dump", str(path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("wef_restore_staging.offers", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
