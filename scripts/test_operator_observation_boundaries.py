"""Synthetic worker observations and source-free operator diagnostics."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest import mock

from scripts.deploy import check_telegram_passive_events as passive
from scripts.deploy import operator_diagnostics as diagnostics


def status_fixture() -> dict[str, Any]:
    """Create a source-free synthetic worker snapshot."""
    return {
        "runtime_health": {"transport_connected": True, "consumer_running": True},
        "reconciliation": {"status": "aligned"},
        "max_persisted_external_id": "17",
    }


class PassiveObservationBoundaryTests(unittest.TestCase):
    """Docker calls are replaced and actual CLI execution only reads a fixture."""

    def test_snapshot_coercion_missing_metadata_and_unhealthy_consumer(self) -> None:
        for value, expected in (
            (None, None),
            (True, None),
            (17, 17),
            ("17", 17),
            ("invalid", None),
            (1.5, None),
        ):
            payload = status_fixture()
            payload["max_persisted_external_id"] = value
            payload["runtime_health"] = {
                "remote_head_external_id": value,
                "release_sha": 23,
                "transport_connected": "unknown",
                "consumer_running": "unknown",
                "last_event_received_at": None,
                "last_event_committed_at": "2026-10-19T00:00:00Z",
            }
            with self.subTest(value=value):
                snapshot = passive.snapshot_from_status(payload)
                self.assertEqual(snapshot.remote_head_external_id, expected)
                self.assertEqual(snapshot.max_persisted_external_id, expected)
                self.assertEqual(snapshot.release_sha, "23")
                self.assertIsNone(snapshot.transport_connected)
                self.assertIsNone(snapshot.consumer_running)
                self.assertEqual(snapshot.last_event_committed_at, "2026-10-19T00:00:00Z")
        reconciliation: object
        for reconciliation in (None, [], {"status": 1}):
            self.assertIsNone(
                passive.snapshot_from_status(
                    {**status_fixture(), "reconciliation": reconciliation}
                ).reconciliation_status
            )
        payload = status_fixture()
        payload["runtime_health"]["consumer_running"] = False
        self.assertEqual(
            passive.evaluate_snapshot(passive.snapshot_from_status(payload)), passive.EXIT_ERROR
        )

    def test_worker_collection_uses_fixed_argv_and_refuses_tool_process_and_json_failures(
        self,
    ) -> None:
        with (
            mock.patch(
                "scripts.deploy.check_telegram_passive_events.shutil.which", return_value=None
            ),
            self.assertRaisesRegex(passive.PassiveEventCheckError, "not found"),
        ):
            passive.collect_worker_status(
                compose_project="fixture-project", worker_service="fixture-worker"
            )
        for code, stdout, stderr in (
            (0, json.dumps(status_fixture()), ""),
            (1, "", "synthetic stderr"),
            (1, "synthetic stdout", ""),
            (1, "", ""),
            (0, "[]", ""),
            (0, "{", ""),
        ):
            with (
                mock.patch(
                    "scripts.deploy.check_telegram_passive_events.shutil.which",
                    return_value="/fixture/docker",
                ),
                mock.patch(
                    "scripts.deploy.check_telegram_passive_events.subprocess.run",
                    return_value=subprocess.CompletedProcess([], code, stdout, stderr),
                ) as run,
                self.subTest(code=code, stdout=stdout),
            ):
                if code or stdout in {"[]", "{"}:
                    with self.assertRaises((passive.PassiveEventCheckError, json.JSONDecodeError)):
                        passive.collect_worker_status(
                            compose_project="fixture-project", worker_service="fixture-worker"
                        )
                else:
                    self.assertEqual(
                        passive.collect_worker_status(
                            compose_project="fixture-project", worker_service="fixture-worker"
                        ),
                        status_fixture(),
                    )
                run.assert_called_once_with(
                    [
                        "/fixture/docker",
                        "compose",
                        "-p",
                        "fixture-project",
                        "exec",
                        "-T",
                        "fixture-worker",
                        "wef-telegram-worker-status",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

    def test_cli_reports_fixture_events_and_bounded_errors_without_contacting_worker(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "status.json"
            payload = status_fixture()
            payload["runtime_health"]["last_event_received_at"] = "2026-10-19T00:00:00Z"
            payload["source_text"] = "synthetic source must not be projected"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch("sys.stdout", new_callable=StringIO) as out:
                self.assertEqual(
                    passive.main(["--status-json", str(path)]), passive.EXIT_EVENT_DETECTED
                )
            report = json.loads(out.getvalue())
            self.assertTrue(report["passive_event_observed"])
            self.assertEqual(report["schema"], "wef-telegram-passive-event-check@1")
            self.assertNotIn("source_text", out.getvalue())
            child = subprocess.run(  # noqa: S603 - fixed CLI and synthetic status file
                [
                    sys.executable,
                    "-m",
                    "scripts.deploy.check_telegram_passive_events",
                    "--status-json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, passive.EXIT_EVENT_DETECTED, child.stderr)
            self.assertTrue(json.loads(child.stdout)["passive_event_observed"])
            for raw in ("[]", "{", "{}"):
                path.write_text(raw, encoding="utf-8")
                with mock.patch("sys.stderr", new_callable=StringIO) as err, self.subTest(raw=raw):
                    self.assertEqual(passive.main(["--status-json", str(path)]), passive.EXIT_ERROR)
                    self.assertIn("passive_event_check:", err.getvalue())
            path.unlink()
            with mock.patch("sys.stderr", new_callable=StringIO):
                self.assertEqual(passive.main(["--status-json", str(path)]), passive.EXIT_ERROR)
        with (
            mock.patch.object(
                passive, "collect_worker_status", return_value=status_fixture()
            ) as collect,
            mock.patch("sys.stdout", new_callable=StringIO),
        ):
            self.assertEqual(passive.main([]), passive.EXIT_OK)
        collect.assert_called_once_with(
            compose_project="wef-production", worker_service="telegram-worker"
        )


class OperatorDiagnosticsBoundaryTests(unittest.TestCase):
    """Read-only fixture collection never queries a real database or host."""

    def test_recursive_list_redaction_and_zero_capacity_disk_sample(self) -> None:
        report = diagnostics.redact_mapping(
            {
                "items": [
                    {"API_KEY": "synthetic-private", "value": 3},
                    {4: "kept", "Token": "synthetic-private"},
                ],
                "healthy": True,
            }
        )
        self.assertEqual(
            report,
            {
                "items": [{"API_KEY": "***", "value": 3}, {"4": "kept", "Token": "***"}],
                "healthy": True,
            },
        )
        for total, used, free, expected in ((0, 0, 0, 0.0), (100, 63, 37, 0.63)):
            with mock.patch(
                "scripts.deploy.operator_diagnostics.shutil.disk_usage",
                return_value=SimpleNamespace(total=total, used=used, free=free),
            ):
                self.assertEqual(diagnostics.disk_usage_for(Path("fixture")).used_ratio, expected)

    def test_absent_and_invalid_release_failure_json_and_empty_release_name(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "state").mkdir()
            self.assertIsNone(diagnostics.load_release(root))
            self.assertIsNone(diagnostics.load_last_failure(root))
            current = root / "state/current.json"
            current.write_text("{}", encoding="utf-8")
            self.assertEqual(
                diagnostics.load_release(root),
                {"release_sha": None, "public_port": None, "release_dir_name": None},
            )
            for name in ("current.json", "last-failure.json"):
                path = root / "state" / name
                path.write_text("[]", encoding="utf-8")
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(
                        diagnostics.OperatorDiagnosticsError, "expected object JSON"
                    ),
                ):
                    (
                        diagnostics.load_release
                        if name == "current.json"
                        else diagnostics.load_last_failure
                    )(root)

    def test_import_query_fixed_argv_empty_result_and_bounded_aggregate_fields(self) -> None:
        arguments = {
            "db_container": "fixture-db",
            "database": "fixture_database",
            "postgres_user": "fixture_user",
        }
        with (
            mock.patch("scripts.deploy.operator_diagnostics.shutil.which", return_value=None),
            self.assertRaisesRegex(diagnostics.OperatorDiagnosticsError, "not found"),
        ):
            diagnostics.query_last_successful_import(**arguments)
        for code, stdout, stderr in (
            (0, "", ""),
            (0, "succeeded|complete|pipeline|checksum1234|", ""),
            (0, "succeeded|complete|pipeline|checksum1234|2026-10-19T00:00:00Z", ""),
            (1, "", "synthetic stderr"),
            (1, "synthetic stdout", ""),
            (1, "", ""),
        ):
            with (
                mock.patch(
                    "scripts.deploy.operator_diagnostics.shutil.which",
                    return_value="/fixture/docker",
                ),
                mock.patch(
                    "scripts.deploy.operator_diagnostics.subprocess.run",
                    return_value=subprocess.CompletedProcess([], code, stdout, stderr),
                ) as run,
                self.subTest(code=code, stdout=stdout),
            ):
                if code:
                    with self.assertRaisesRegex(
                        diagnostics.OperatorDiagnosticsError, "import query failed"
                    ):
                        diagnostics.query_last_successful_import(**arguments)
                else:
                    value = diagnostics.query_last_successful_import(**arguments)
                    if stdout:
                        self.assertIsNotNone(value)
                        self.assertEqual(value and value["source_checksum_prefix"], "checksum1234")
                        self.assertEqual(
                            value and value["finished_at"], stdout.rsplit("|", 1)[1] or None
                        )
                    else:
                        self.assertIsNone(value)
                command = run.call_args.args[0]
                self.assertEqual(
                    command[:10],
                    [
                        "/fixture/docker",
                        "exec",
                        "fixture-db",
                        "psql",
                        "-U",
                        "fixture_user",
                        "-d",
                        "fixture_database",
                        "-tAc",
                        command[-1],
                    ],
                )
                self.assertIn("left(source_checksum, 12)", command[-1])
                self.assertIn("LIMIT 1", command[-1])
                self.assertNotIn("source_text", command[-1])
                self.assertNotIn("contact", command[-1])

    def test_collection_query_and_cli_options_error_and_safe_real_entrypoint(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(
                diagnostics, "query_last_successful_import", return_value={"status": "succeeded"}
            ) as query:
                report = diagnostics.collect_diagnostics(
                    root,
                    db_container="fixture-db",
                    database="fixture_database",
                    postgres_user="fixture_user",
                )
            self.assertEqual(report["last_successful_import"], {"status": "succeeded"})
            query.assert_called_once_with(
                db_container="fixture-db", database="fixture_database", postgres_user="fixture_user"
            )
            self.assertEqual(len(report["disk"]), 5)
            self.assertTrue(all(item["path"] == str(root) for item in report["disk"]))
            with (
                mock.patch.object(
                    diagnostics, "collect_diagnostics", return_value=report
                ) as collect,
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(diagnostics.main(["--root", str(root), "--skip-import-query"]), 0)
            collect.assert_called_once_with(
                root, db_container=None, database="wef_hist_candidate", postgres_user="wef"
            )
            self.assertEqual(json.loads(out.getvalue())["schema"], "wef-operator-diagnostics@1")
            with (
                mock.patch.object(
                    diagnostics,
                    "collect_diagnostics",
                    side_effect=diagnostics.OperatorDiagnosticsError("synthetic refusal"),
                ),
                mock.patch("sys.stderr", new_callable=StringIO) as err,
            ):
                self.assertEqual(diagnostics.main([]), 1)
                self.assertIn("operator_diagnostics: synthetic refusal", err.getvalue())
            child = subprocess.run(  # noqa: S603 - fixture root and explicit no-query mode
                [
                    sys.executable,
                    "-m",
                    "scripts.deploy.operator_diagnostics",
                    "--root",
                    str(root),
                    "--skip-import-query",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertIsNone(json.loads(child.stdout)["last_successful_import"])


if __name__ == "__main__":
    unittest.main()
