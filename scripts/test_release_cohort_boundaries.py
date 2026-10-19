"""Release performance evidence rejects unavailable, foreign and malformed observations."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import release_cohort as cohort
from scripts.test_release_cohort import row
from scripts.test_release_report import END, SHA, START


class ReleaseCohortBoundaryTests(unittest.TestCase):
    """The only artifact downloads and API reads are controlled process doubles."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workflow_run = {
            "id": 1,
            "run_attempt": 1,
            "head_sha": SHA,
            "event": "push",
            "created_at": START,
            "conclusion": "success",
            "head_repository": {"full_name": "fixture/repo"},
            "head_branch": "main",
        }
        self.report = {
            "schema": "wef-release-outcome/v1",
            "release_sha": SHA,
            "run_id": 1,
            "run_attempt": 1,
            "event": "push",
            "outcome": "deployed",
            "verified": True,
            "eligible": True,
            "healthy_sha": SHA,
            "cache_state": "warm",
            "observation": {"release_sha": SHA, "healthy_at": END, "activated_at": END},
        }

    def test_missing_or_expired_artifacts_do_not_invoke_a_download(self) -> None:
        with (
            mock.patch("scripts.deploy.release_cohort.shutil.which", return_value=None),
            mock.patch(
                "scripts.deploy.release_cohort.read_api",
            ) as api,
        ):
            self.assertEqual(cohort.observation("fixture/repo", self.workflow_run), {})
            api.assert_not_called()
        for artifacts in (
            [],
            [{"name": "release-outcome-1-1", "expired": True}],
            [{"name": "unrelated", "expired": False}],
        ):
            with (
                self.subTest(artifacts=artifacts),
                mock.patch(
                    "scripts.deploy.release_cohort.shutil.which", return_value="/fixture/gh"
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    return_value={"artifacts": artifacts},
                ),
                mock.patch("scripts.deploy.release_cohort.subprocess.run") as download,
            ):
                self.assertEqual(cohort.observation("fixture/repo", self.workflow_run), {})
                download.assert_not_called()

    def test_downloaded_observations_require_bounded_regular_same_run_evidence(self) -> None:
        cases: tuple[str, ...] = (
            "missing",
            "failed",
            "symlink",
            "oversized",
            "at-limit",
            "malformed",
            "nonobject",
            "foreign",
            "valid",
        )
        for case in cases:

            def download(
                command: list[str], case: str = case, **_options: object
            ) -> subprocess.CompletedProcess[bytes]:
                path = Path(command[command.index("--dir") + 1]) / "release-outcome.json"
                if case == "symlink":
                    target = self.root / "linked-report.json"
                    target.write_text(json.dumps(self.report), encoding="utf-8")
                    path.symlink_to(target)
                elif case in {"oversized", "at-limit"}:
                    size = cohort.MAX_REPORT_BYTES + int(case == "oversized")
                    path.write_text(json.dumps(self.report).ljust(size), encoding="utf-8")
                elif case == "malformed":
                    path.write_text("{", encoding="utf-8")
                elif case == "nonobject":
                    path.write_text("[]", encoding="utf-8")
                elif case in {"valid", "foreign"}:
                    path.write_text(
                        json.dumps({**self.report, "run_attempt": 1 if case == "valid" else 2}),
                        encoding="utf-8",
                    )
                return subprocess.CompletedProcess(command, 1 if case == "failed" else 0, b"", b"")

            with (
                self.subTest(case=case),
                mock.patch(
                    "scripts.deploy.release_cohort.shutil.which", return_value="/fixture/gh"
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    return_value={"artifacts": [{"name": "release-outcome-1-1", "expired": False}]},
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.subprocess.run", side_effect=download
                ) as process,
            ):
                self.assertEqual(
                    cohort.observation("fixture/repo", self.workflow_run),
                    self.report if case in {"valid", "at-limit"} else {},
                )
                self.assertEqual(
                    process.call_args.args[0][:6],
                    ["/fixture/gh", "run", "download", "1", "--repo", "fixture/repo"],
                )
                self.assertEqual(process.call_args.kwargs["timeout"], 60)
        for error in (OSError("synthetic offline"), subprocess.TimeoutExpired("fixture", 60)):
            with (
                self.subTest(error=error),
                mock.patch(
                    "scripts.deploy.release_cohort.shutil.which", return_value="/fixture/gh"
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    return_value={"artifacts": [{"name": "release-outcome-1-1", "expired": False}]},
                ),
                mock.patch("scripts.deploy.release_cohort.subprocess.run", side_effect=error),
            ):
                self.assertEqual(cohort.observation("fixture/repo", self.workflow_run), {})

    def test_record_requires_matching_ordered_health_and_source_ancestry(self) -> None:
        pr = {
            "state": "closed",
            "merge_commit_sha": SHA,
            "merged_at": START,
            "base": {"ref": "main"},
        }
        jobs = [
            {
                "name": "Deploy verified release",
                "started_at": START,
                "completed_at": END,
                "conclusion": "success",
            },
            {"name": "not-started", "started_at": None},
        ]
        for comparison, phase in (
            ("ahead", "optimized"),
            ("identical", "optimized"),
            ("behind", "baseline"),
            ("diverged", "unclassified"),
        ):
            with (
                self.subTest(comparison=comparison),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    side_effect=[{"items": [pr]}, {"jobs": jobs}, {"status": comparison}],
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.observation",
                    return_value=self.report,
                ),
            ):
                result = cohort.collect_record("fixture/repo", self.workflow_run, SHA)
            self.assertEqual(result["phase"], phase)
            self.assertEqual(result["merge_to_healthy_seconds"], 60)
            self.assertEqual(result["cache_state"], "warm")
        for observed in (
            {"release_sha": "b" * 40, "healthy_at": END, "activated_at": END},
            {"release_sha": SHA, "healthy_at": END, "activated_at": START},
        ):
            with (
                self.subTest(observed=observed),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    side_effect=[{"items": [pr]}, {"jobs": jobs}],
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.observation",
                    return_value={**self.report, "observation": observed},
                ),
            ):
                result = cohort.collect_record("fixture/repo", self.workflow_run, None)
            self.assertIsNone(result["merge_to_healthy_seconds"])
        with (
            mock.patch("scripts.deploy.release_cohort.read_api", side_effect=[{}, {}]),
            mock.patch(
                "scripts.deploy.release_cohort.observation",
                return_value={
                    **self.report,
                    "verified": False,
                    "outcome": "unknown",
                    "cache_state": "invented",
                },
            ),
        ):
            result = cohort.collect_record("fixture/repo", self.workflow_run, None)
        self.assertEqual(result["outcome"], "deployment_unconfirmed")
        self.assertEqual(result["cache_state"], "unknown")
        self.assertIsNone(result["merge_to_healthy_seconds"])
        self.assertIsNone(result["initial_queue_seconds"])

    def test_summary_retains_failed_or_missing_job_timings_without_counting_them(self) -> None:
        result = cohort.summarize(
            [
                row(1),
                {
                    **row(2),
                    "deploy_job_result": "failure",
                    "merge_to_deploy_job_end_seconds": None,
                    "merge_to_healthy_seconds": None,
                    "outcome": "failed",
                },
            ],
            SHA,
        )
        optimized = result["cohorts"]["optimized"]
        self.assertEqual(optimized["ordinary_runs"], 2)
        self.assertEqual(optimized["merge_to_deploy_job_end"]["samples"], 1)
        self.assertEqual(optimized["merge_to_healthy"]["samples"], 1)
        self.assertEqual(optimized["outcomes"]["failed"], 1)
        self.assertIn("insufficient_observations", cohort.render(result))

    def test_saved_evidence_requires_schema_valid_cutoff_and_stable_classification(self) -> None:
        path = self.root / "saved.json"
        cases: tuple[object, ...] = (
            [],
            {},
            {"summary": {"schema": "old"}},
            {"summary": {"schema": "wef-release-cohort/v1", "optimized_from": True}},
            {"summary": {"schema": "wef-release-cohort/v1", "optimized_from": "bad"}},
        )
        for payload in cases:
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                cohort.load_saved(path, None)
        path.write_text(
            json.dumps(
                {
                    "summary": {"schema": "wef-release-cohort/v1", "optimized_from": SHA},
                    "records": [row(1)],
                }
            ),
            encoding="utf-8",
        )
        records, cutoff = cohort.load_saved(path, SHA)
        self.assertEqual(cutoff, SHA)
        self.assertEqual(records[0]["phase"], "optimized")
        with self.assertRaisesRegex(ValueError, "recollect source ancestry"):
            cohort.load_saved(path, "b" * 40)

    def test_cli_refuses_invalid_options_and_unavailable_metadata_before_writing(self) -> None:
        output = self.root / "output.json"
        for options in (
            ["--limit", "0"],
            ["--limit", "101"],
            ["--repo", "invalid-repo"],
            ["--optimized-from", "bad"],
        ):
            with (
                self.subTest(options=options),
                mock.patch.object(sys, "argv", ["cohort", "--output", str(output), *options]),
                mock.patch("sys.stderr", new_callable=StringIO),
                self.assertRaises(SystemExit) as error,
            ):
                cohort.main()
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())
        with (
            mock.patch.object(sys, "argv", ["cohort", "--output", str(output)]),
            mock.patch("scripts.deploy.release_cohort.read_api", return_value={}),
            mock.patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            cohort.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(output.exists())

    def test_cli_collects_only_matching_main_runs_and_distinguishes_insufficient_budget(
        self,
    ) -> None:
        output = self.root / "output.json"
        runs = [
            self.workflow_run,
            {**self.workflow_run, "head_repository": {"full_name": "foreign/repo"}},
            {**self.workflow_run, "head_sha": "bad"},
            {**self.workflow_run, "head_branch": "other"},
        ]
        for require, expected in ((False, 0), (True, 1)):
            args = [
                "cohort",
                "--repo",
                "fixture/repo",
                "--output",
                str(output),
                "--optimized-from",
                SHA,
            ]
            with (
                self.subTest(require=require),
                mock.patch.object(sys, "argv", [*args, *(["--require-budget"] if require else [])]),
                mock.patch(
                    "scripts.deploy.release_cohort.read_api",
                    return_value={"workflow_runs": runs},
                ),
                mock.patch(
                    "scripts.deploy.release_cohort.collect_record", return_value=row(1)
                ) as collect,
            ):
                self.assertEqual(cohort.main(), expected)
                collect.assert_called_once_with("fixture/repo", self.workflow_run, SHA)
            result = json.loads(output.read_text())
            self.assertEqual(len(result["records"]), 1)
            self.assertEqual(
                result["summary"]["latency_budget"]["status"], "insufficient_observations"
            )
            self.assertIn("Release performance evidence", output.with_suffix(".md").read_text())

    def test_cli_saved_cohort_preserves_budget_and_real_entrypoint_avoids_api(self) -> None:
        saved, output = self.root / "saved.json", self.root / "result.json"
        saved.write_text(
            json.dumps(
                {
                    "summary": {"schema": "wef-release-cohort/v1", "optimized_from": SHA},
                    "records": [row(i) for i in range(1, 21)],
                }
            ),
            encoding="utf-8",
        )
        args = ["--input", str(saved), "--output", str(output), "--require-budget"]
        with (
            mock.patch.object(sys, "argv", ["cohort", *args]),
            mock.patch("scripts.deploy.release_cohort.read_api") as api,
        ):
            self.assertEqual(cohort.main(), 0)
            api.assert_not_called()
        result = subprocess.run(  # noqa: S603 - current Python, fixed module and synthetic arguments
            [sys.executable, "-m", "scripts.deploy.release_cohort", *args],
            cwd=Path(cohort.__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PATH": str(self.root)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(output.read_text())["summary"]["latency_budget"]["status"], "met"
        )
