"""Verify release-budget evidence, sample independence, and explicit unknown observations."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import unittest
from typing import Any
from unittest.mock import patch

from scripts.deploy.release_cache import cache_metrics, collect_cache
from scripts.deploy.release_cohort import (
    clean_records,
    collect_record,
    stats,
    summarize,
    trusted_observation,
)
from scripts.deploy.release_report import build_report, cache_evidence
from scripts.test_release_report import fixture

SHA = "a" * 40


def row(number: int, seconds: float = 200) -> dict[str, Any]:
    """Return a synthetic ordinary observed release; no fixture is production evidence."""
    return {
        "run_id": number,
        "run_attempt": 1,
        "release_sha": f"{number:040x}",
        "event": "push",
        "merged_at": "2026-09-05T10:00:00Z",
        "phase": "optimized",
        "outcome": "deployed",
        "run_conclusion": "success",
        "deploy_job_result": "success",
        "merge_to_healthy_seconds": seconds,
        "merge_to_deploy_job_end_seconds": seconds + 20,
        "initial_queue_seconds": 5,
        "cache_state": "unknown",
    }


class CohortTests(unittest.TestCase):
    def test_budget_requires_twenty_independent_source_observations(self) -> None:
        rows = [row(i) for i in range(1, 20)]
        self.assertEqual(
            summarize(rows, SHA)["latency_budget"]["status"], "insufficient_observations"
        )
        duplicate = {**row(1), "run_id": 21, "run_attempt": 2}
        self.assertEqual(
            summarize([*rows, duplicate], SHA)["latency_budget"]["status"],
            "insufficient_observations",
        )
        result = summarize([*rows, row(20)], SHA)
        self.assertEqual(result["latency_budget"]["status"], "met")
        self.assertIsNone(result["cohorts"]["optimized"]["human_interventions"])

    def test_cutoff_is_required_even_with_enough_saved_observations(self) -> None:
        self.assertEqual(
            summarize([row(i) for i in range(1, 21)], None)["latency_budget"]["status"],
            "awaiting_cutoff",
        )

    def test_saved_records_drop_unknown_fields_and_reject_invalid_identity(self) -> None:
        result = clean_records([{**row(1), "private_input": "discard", "cache_state": "invented"}])
        self.assertNotIn("private_input", result[0])
        self.assertEqual(result[0]["cache_state"], "unknown")
        with self.assertRaises(TypeError):
            clean_records({})
        for invalid in ({**row(1), "run_id": True}, {**row(1), "release_sha": "invalid"}):
            with self.assertRaises(ValueError):
                clean_records([invalid])

    def test_measured_cache_components_and_preparation_failure(self) -> None:
        needs = fixture()
        needs["verify"]["outputs"] = {"backend_cache_hit": "true"}
        for component in ("backend", "web"):
            needs[f"build-{component}"] = {
                "outputs": {
                    "cache_metrics": json.dumps(
                        {
                            "cached_steps": 4,
                            "total_steps": 10,
                        }
                    )
                }
            }
        self.assertEqual(cache_evidence(needs)["state"], "warm")
        needs["verify"]["outputs"]["backend_cache_hit"] = "false"
        self.assertEqual(cache_evidence(needs)["state"], "mixed")
        needs["publish"]["result"] = "failure"
        needs["deploy"]["result"] = "skipped"
        self.assertEqual(build_report(needs, {}, [])["outcome"], "preparation_failed")

    def test_slow_releases_and_runner_incidents_are_not_removed(self) -> None:
        rows = [row(i, 600) for i in range(1, 21)]
        rows.append(
            {
                **row(21),
                "run_conclusion": "failure",
                "outcome": "failed",
                "merge_to_healthy_seconds": None,
            }
        )
        result = summarize(rows, SHA)
        self.assertEqual(result["latency_budget"]["status"], "missed")
        self.assertEqual(result["cohorts"]["optimized"]["ordinary_runs"], 21)
        self.assertEqual(result["cohorts"]["optimized"]["outcomes"]["failed"], 1)

    def test_verified_only_duplicates_manual_and_superseded_do_not_count_as_deployments(
        self,
    ) -> None:
        rows = [row(i) for i in range(1, 19)]
        rows += [
            {**row(20), "outcome": "already_current"},
            {**row(21), "outcome": "superseded"},
            {**row(22), "event": "workflow_dispatch"},
            {**row(23), "outcome": "verified_only"},
            {**row(24), "merged_at": None},
        ]
        result = summarize(rows, SHA)
        self.assertEqual(result["cohorts"]["optimized"]["merge_to_healthy"]["samples"], 18)
        self.assertEqual(result["manual_dispatches"], 1)
        self.assertEqual(result["unmatched_pushes"], 1)

    def test_nearest_rank_missing_and_invalid_numbers(self) -> None:
        self.assertIsNone(stats([])["p95_seconds"])
        self.assertEqual(stats([10, 20, 30])["p95_seconds"], 30)
        rows = [
            {**row(i), "merge_to_healthy_seconds": value}
            for i, value in enumerate((None, -1, True, float("nan"), float("inf")), 1)
        ]
        result = summarize(rows, SHA)
        self.assertEqual(result["cohorts"]["optimized"]["merge_to_healthy"]["samples"], 0)
        self.assertEqual(summarize([], None)["latency_budget"]["status"], "awaiting_cutoff")

    def test_exact_attempt_duplicates_are_visible_without_counting_twice(self) -> None:
        result = summarize([row(1), row(1)], SHA)
        self.assertEqual(result["run_attempts"], 1)
        self.assertEqual(result["duplicate_records_ignored"], 1)

    def test_wrong_sha_attempt_or_schema_is_not_trusted_health(self) -> None:
        run = {"id": 1, "run_attempt": 2, "head_sha": SHA, "event": "push"}
        report = {
            "schema": "wef-release-outcome/v1",
            "run_id": 1,
            "run_attempt": 2,
            "release_sha": SHA,
            "event": "push",
        }
        self.assertTrue(trusted_observation(report, run))
        for key, value in (("run_attempt", 1), ("release_sha", "b" * 40), ("schema", "other")):
            self.assertFalse(trusted_observation({**report, key: value}, run))

    def test_historical_successful_job_is_not_fabricated_health(self) -> None:
        run = {
            "id": 1,
            "run_attempt": 1,
            "head_sha": SHA,
            "event": "push",
            "conclusion": "success",
            "created_at": "2026-09-05T10:00:01Z",
        }
        pr = {
            "state": "closed",
            "merge_commit_sha": SHA,
            "merged_at": "2026-09-05T10:00:00Z",
            "base": {"ref": "main"},
        }
        job = {
            "name": "Deploy verified release",
            "conclusion": "success",
            "started_at": "2026-09-05T10:04:00Z",
            "completed_at": "2026-09-05T10:05:00Z",
        }
        with (
            patch(
                "scripts.deploy.release_cohort.read_api",
                side_effect=[{"items": [pr]}, {"jobs": [job]}],
            ),
            patch("scripts.deploy.release_cohort.observation", return_value={}),
        ):
            record = collect_record("Flippylolz/WEF", run, None)
        self.assertEqual(record["merge_to_deploy_job_end_seconds"], 300)
        self.assertIsNone(record["merge_to_healthy_seconds"])
        self.assertEqual(record["outcome"], "deployment_unconfirmed")

    def test_cache_counters_are_bounded_and_build_record_is_not_exported(self) -> None:
        self.assertEqual(
            cache_metrics({"Status": "completed", "NumTotalSteps": 10, "NumCachedSteps": 4})[
                "state"
            ],
            "warm",
        )
        self.assertEqual(
            cache_metrics({"Status": "completed", "NumTotalSteps": 10, "NumCachedSteps": 0})[
                "state"
            ],
            "cold",
        )
        for total, cached in ((0, 0), (10, 11), (True, 0), (10, -1), (None, None)):
            self.assertEqual(
                cache_metrics(
                    {"Status": "completed", "NumTotalSteps": total, "NumCachedSteps": cached}
                )["state"],
                "unknown",
            )
        self.assertEqual(
            collect_cache({"buildx.build.ref": "--untrusted-flag"})["state"], "unknown"
        )
        self.assertEqual(cache_evidence({})["state"], "unknown")

    def test_action_build_reference_selects_builder_and_exact_record(self) -> None:
        record = {
            "Ref": "build123",
            "Status": "completed",
            "NumTotalSteps": 14,
            "NumCachedSteps": 8,
        }
        with (
            patch("scripts.deploy.release_cache.shutil.which", return_value="/usr/bin/docker"),
            patch(
                "scripts.deploy.release_cache.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps(record), stderr=""
                ),
            ) as run,
        ):
            self.assertEqual(
                collect_cache({"buildx.build.ref": "builder-a/node-a/build123"}),
                {"state": "warm", "cached_steps": 8, "total_steps": 14},
            )
            self.assertEqual(
                run.call_args.args[0],
                [
                    "/usr/bin/docker",
                    "buildx",
                    "--builder",
                    "builder-a",
                    "history",
                    "inspect",
                    "--format",
                    "json",
                    "build123",
                ],
            )
            run.return_value.stdout = json.dumps({**record, "Ref": "different"})
            self.assertEqual(
                collect_cache({"buildx.build.ref": "builder-a/node-a/build123"})["state"], "unknown"
            )

    def test_invalid_action_reference_never_invokes_docker(self) -> None:
        with patch("scripts.deploy.release_cache.subprocess.run") as run:
            for ref in (
                "build123",
                "builder/id",
                "builder/node/id/extra",
                "--builder/node/id",
                "builder/../id",
                "builder/node/^1",
            ):
                self.assertEqual(collect_cache({"buildx.build.ref": ref})["state"], "unknown")
            run.assert_not_called()

    def test_reused_verification_requires_successful_artifact_validation(self) -> None:
        needs = fixture()
        needs["verify"]["result"] = "skipped"
        needs["publish"].update(result="success")
        needs["publish"]["outputs"]["reused_verified"] = "true"
        self.assertEqual(build_report(needs, {}, [])["outcome"], "deployed")
        needs["publish"]["result"] = "failure"
        self.assertEqual(build_report(needs, {}, [])["outcome"], "verification_failed")


if __name__ == "__main__":
    unittest.main()
