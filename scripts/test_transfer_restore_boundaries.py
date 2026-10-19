"""Failure and resume boundaries for the operator's PostgreSQL restore."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import transfer_restore as cli
from scripts.transfer import postgres_restore as restore


class PostgresRestoreBoundaryTests(unittest.TestCase):
    """Assert SQL safety, snapshot validation and process failure semantics."""

    def test_key_shapes_and_literals(self) -> None:
        self.assertEqual(restore.encode_row_key("locations", (3,)), 3)
        self.assertEqual(restore.encode_row_key("offer_media", (3, 4)), (3, 4))
        with self.assertRaisesRegex(restore.PostgresRestoreError, "value count mismatch"):
            restore.encode_row_key("locations", ())
        for table, key in (("locations", (1,)), ("offer_media", 1), ("offer_media", (1,))):
            with (
                self.subTest(table=table, key=key),
                self.assertRaisesRegex(
                    restore.PostgresRestoreError,
                    "expected .* primary key",
                ),
            ):
                restore.decode_row_key(table, key)
        sql = restore.build_batch_insert_sql(
            table="locations",
            keys=(None, True, False, 3, 1.25, "O'Brien"),
        )
        self.assertIn("s.id IN (NULL, TRUE, FALSE, 3, 1.25, 'O''Brien')", sql)

    def test_sql_refuses_unknown_tables_schemas_and_empty_batches(self) -> None:
        cases = (
            {"table": "no_table", "keys": (1,)},
            {"table": "locations", "keys": ()},
            {"table": "locations", "keys": (1,), "staging_schema": "bad; DROP SCHEMA public"},
            {"table": "locations", "keys": (1,), "target_schema": "bad-name"},
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(restore.PostgresRestoreError):
                restore.build_batch_insert_sql(**values)
        for table, schema in (("unknown", "public"), ("locations", "bad-name")):
            with (
                self.subTest(table=table, schema=schema),
                self.assertRaises(
                    restore.PostgresRestoreError,
                ),
            ):
                restore.build_snapshot_export_sql(table=table, schema=schema)
        with self.assertRaisesRegex(restore.PostgresRestoreError, "schema name is invalid"):
            restore.rewrite_dump_for_staging("COPY public.locations (id)", staging_schema="bad;")
        self.assertEqual(
            restore.build_staging_teardown_sql(tables=("offers", "locations")),
            "DROP TABLE IF EXISTS wef_restore_staging.offers CASCADE;\n"
            "DROP TABLE IF EXISTS wef_restore_staging.locations CASCADE;\n"
            "DROP SCHEMA IF EXISTS wef_restore_staging CASCADE;\n",
        )

    def test_snapshot_maps_preserve_nonnumeric_and_native_keys(self) -> None:
        self.assertEqual(
            restore.parse_snapshot_map({"1": "a", 2: "b", "uuid": "c"}),
            {1: "a", 2: "b", "uuid": "c"},
        )
        with self.assertRaisesRegex(restore.PostgresRestoreError, "must be a JSON object"):
            restore.parse_snapshot_map([])
        plan = restore.build_restore_plan_from_snapshots(
            table_snapshots={"locations": ({}, {1: {"name": "synthetic"}})},
            batch_size=1,
        )
        self.assertEqual(plan.total_new_rows, 1)

    def test_checkpoint_files_reject_invalid_schema_and_entries(self) -> None:
        valid = {
            "schema": restore.CHECKPOINT_SCHEMA,
            "source_checksum": "a" * 64,
            "candidate_database": "wef_test_candidate",
            "batch_size": 1,
            "checkpoints": {},
        }
        payloads: tuple[object, ...] = (
            [],
            {},
            {**valid, "checkpoints": []},
            {**valid, "checkpoints": {"locations": 1}},
        )
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint.json"
            for payload in payloads:
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(restore.PostgresRestoreError):
                    restore.load_checkpoint_state(path)
        advanced = restore.advance_restore_checkpoint(
            restore.RestoreCheckpointState("a" * 64, "wef_test_candidate", 1, {}),
            table="locations",
            batch_size=1,
            rows_remaining_after_batch=2,
        )
        self.assertEqual(advanced.checkpoints["locations"].completed_batches, 1)

    def test_psql_process_options_and_error_details(self) -> None:
        target = restore.PsqlTarget("synthetic-postgres", "fixture-user", "wef_test_candidate")
        with mock.patch("scripts.transfer.postgres_restore.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "  result\n", "")
            self.assertEqual(restore.run_psql(target, "SELECT 1", tuples_only=True), "result")
            arguments, options = run.call_args
            self.assertEqual(
                arguments[0],
                [
                    "docker",
                    "exec",
                    "-i",
                    "synthetic-postgres",
                    "psql",
                    "-U",
                    "fixture-user",
                    "-d",
                    "wef_test_candidate",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-t",
                    "-A",
                ],
            )
            self.assertEqual(options["input"], "SELECT 1")
            self.assertFalse(options["check"])
            restore.apply_batch(target, table="locations", keys=(1,))
            self.assertNotIn("-t", run.call_args.args[0])
            self.assertIn("ON CONFLICT DO NOTHING", run.call_args.kwargs["input"])
            for stdout, stderr, detail in (
                ("ignored", " denied\n", "denied"),
                ("fallback\n", "", "fallback"),
            ):
                run.return_value = subprocess.CompletedProcess([], 1, stdout, stderr)
                with (
                    self.subTest(detail=detail),
                    self.assertRaisesRegex(
                        restore.PostgresRestoreError,
                        f"psql failed: {detail}",
                    ),
                ):
                    restore.run_psql(target, "SELECT 1")

    def test_live_exports_pair_target_and_staging_snapshots(self) -> None:
        target = restore.PsqlTarget("synthetic", "wef", "wef_test_candidate")
        with mock.patch.object(restore, "run_psql", side_effect=['{"1":{"name":"a"}}', ""]):
            snapshots = restore.export_schema_snapshots(
                target,
                schema="public",
                tables=("locations", "offers"),
            )
        self.assertEqual(snapshots, {"locations": {1: {"name": "a"}}, "offers": {}})
        with mock.patch.object(restore, "run_psql", return_value="{}") as run:
            self.assertTrue(restore.export_restore_snapshots(target))
        sql_statements = [call.args[1] for call in run.call_args_list]
        self.assertTrue(any("FROM public.locations" in sql for sql in sql_statements))
        self.assertTrue(any("FROM wef_restore_staging.locations" in sql for sql in sql_statements))


class RestoreCliBoundaryTests(unittest.TestCase):
    """Exercise operator commands against synthetic snapshots and a process double."""

    def test_cli_sql_commands_and_key_formats(self) -> None:
        for command, expected in (
            ("staging-setup-sql", "CREATE SCHEMA"),
            ("staging-teardown-sql", "DROP SCHEMA"),
        ):
            with (
                self.subTest(command=command),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(cli.main([command]), 0)
                self.assertIn(expected, out.getvalue())
        for raw, expected in (("1", "'1'"), ("1, ,2", "'1', '2'"), ("[1,2]", "1, 2")):
            with self.subTest(raw=raw), mock.patch("sys.stdout", new_callable=StringIO) as out:
                self.assertEqual(cli.main(["batch-sql", "locations", raw]), 0)
                self.assertIn(f"s.id IN ({expected})", out.getvalue())
        with mock.patch("scripts.transfer.postgres_restore.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            self.assertEqual(
                cli.main(
                    [
                        "apply-batch",
                        "locations",
                        "[1]",
                        "--container",
                        "synthetic",
                        "--database",
                        "wef_test_candidate",
                    ]
                ),
                0,
            )
            self.assertIn("s.id IN (1)", run.call_args.kwargs["input"])

    def test_preflight_requires_complete_live_target_and_reports_conflicts(self) -> None:
        for options in ([], ["--container", "synthetic"], ["--database", "wef_test_candidate"]):
            with (
                self.subTest(options=options),
                self.assertRaisesRegex(SystemExit, "preflight requires"),
            ):
                cli.main(["preflight", *options])
        snapshots = {"locations": ({1: {"name": "old"}}, {1: {"name": "new"}})}
        with mock.patch.object(cli, "export_restore_snapshots", return_value=snapshots) as export:
            with mock.patch("sys.stdout", new_callable=StringIO) as out:
                self.assertEqual(
                    cli.main(
                        [
                            "preflight",
                            "--container",
                            "synthetic",
                            "--database",
                            "wef_test_candidate",
                        ]
                    ),
                    1,
                )
                self.assertFalse(json.loads(out.getvalue())["allowed"])
                self.assertIn("conflicting rows", out.getvalue())
            self.assertEqual(export.call_args.args[0].database, "wef_test_candidate")

    def test_parser_and_json_decoder_reject_invalid_dispatch_inputs(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            cli.main(["batch-sql", "locations", "[1"])
        with (
            mock.patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            cli.main(["unknown-command"])
        self.assertEqual(error.exception.code, 2)

    def test_snapshot_file_rejects_nonobject_payloads(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "snapshots.json"
            payload: object
            for payload in ([], {"locations": []}):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(TypeError):
                    cli.main(["preflight", "--snapshots", str(path)])

    def test_restore_dry_run_failure_and_checkpoint_resume(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshots = root / "snapshots.json"
            snapshots.write_text(
                json.dumps(
                    {
                        "locations": {
                            "incoming": {
                                "1": {"name": "first"},
                                "2": {"name": "second"},
                                "3": {"name": "third"},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = [
                "run",
                "--wef-root",
                str(root),
                "--source-checksum",
                "a" * 64,
                "--container",
                "synthetic",
                "--database",
                "wef_test_candidate",
                "--snapshots",
                str(snapshots),
                "--batch-size",
                "1",
            ]
            checkpoint = restore.checkpoint_file_path(root, "a" * 64)
            with mock.patch.object(cli, "apply_batch") as apply:
                with mock.patch("sys.stdout", new_callable=StringIO) as out:
                    self.assertEqual(cli.main([*args, "--dry-run"]), 0)
                    self.assertEqual(json.loads(out.getvalue())["remaining_batches"], 3)
                apply.assert_not_called()
                self.assertFalse(checkpoint.exists())
                apply.side_effect = [None, restore.PostgresRestoreError("synthetic interruption")]
                with self.assertRaisesRegex(restore.PostgresRestoreError, "synthetic interruption"):
                    cli.main(args)
                state = restore.load_checkpoint_state(checkpoint)
                self.assertEqual(state.checkpoints["locations"].completed_batches, 1)
                self.assertEqual(checkpoint.stat().st_mode & 0o777, 0o600)
                apply.reset_mock(side_effect=True)
                self.assertEqual(cli.main(args), 0)
                self.assertEqual(
                    [call.kwargs["keys"] for call in apply.call_args_list], [(2,), (3,)]
                )
                self.assertEqual(restore.load_checkpoint_state(checkpoint).checkpoints, {})
                snapshots.write_text("{}", encoding="utf-8")
                apply.reset_mock()
                self.assertEqual(cli.main(args), 0)
                apply.assert_not_called()
