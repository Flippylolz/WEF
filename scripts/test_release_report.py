"""Failure, privacy, and timing coverage for release outcomes."""

# ruff: noqa: D101, D102, PT009, S106

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.deploy.evaluate_deploy_gate import gate_outputs
from scripts.deploy.release_observation import clean_observation, record
from scripts.deploy.release_report import (
    build_report,
    duration,
    interval_gap,
    render_summary,
)

SHA = "a" * 40
OLD = "b" * 40
START = "2026-09-05T10:00:00Z"
END = "2026-09-05T10:01:00Z"


def fixture() -> dict[str, Any]:
    """Return a successful workflow with explicit host health and activation evidence."""
    return {
        "resolve": {
            "outputs": {
                "release_sha": SHA,
                "should_deploy": "true",
                "gate_reason": "merged_pr",
                "merged_at": START,
            }
        },
        "verify": {"result": "success"},
        "publish": {"outputs": {"backend_digest": "sha256:" + "c" * 64}},
        "deploy": {
            "result": "success",
            "outputs": {
                "observation": json.dumps(
                    {
                        "release_sha": SHA,
                        "previous_sha": OLD,
                        "started_at": START,
                        "healthy_at": END,
                        "activated_at": END,
                    }
                )
            },
        },
    }


class ReportTests(unittest.TestCase):
    def test_parallel_intervals_are_not_added_twice(self) -> None:
        children = [{"started_at": START, "completed_at": END}] * 2
        self.assertEqual(interval_gap(START, END, children)["seconds"], 0)
        children[0] = {"started_at": START}
        self.assertIsNone(interval_gap(START, END, children)["seconds"])

    def test_health_evidence_is_required(self) -> None:
        needs = fixture()
        report = build_report(needs, {}, [])
        self.assertEqual(report["outcome"], "deployed")
        self.assertEqual(report["merge_to_healthy"]["seconds"], 60)
        needs["deploy"]["outputs"] = {}
        report = build_report(needs, {}, [])
        self.assertEqual(report["outcome"], "deployment_unconfirmed")
        self.assertIsNone(report["healthy_sha"])
        self.assertIsNone(report["merge_to_healthy"]["seconds"])

    def test_wrong_sha_and_secret_fields_never_become_evidence(self) -> None:
        needs = fixture()
        raw = json.loads(needs["deploy"]["outputs"]["observation"])
        raw.update(config_file="/secret", password="do-not-export", release_sha=OLD)
        needs["deploy"]["outputs"]["observation"] = json.dumps(raw)
        report = build_report(needs, {}, [])
        self.assertEqual(report["outcome"], "deployment_unconfirmed")
        self.assertNotIn("do-not-export", json.dumps(report))
        raw["release_sha"] = SHA
        self.assertNotIn("config_file", clean_observation(raw, SHA))

    def test_verified_only_failed_and_queued_are_distinct(self) -> None:
        for eligible, verified, deploy, expected in (
            ("false", "success", "skipped", "verified_only"),
            ("true", "failure", "skipped", "verification_failed"),
            ("true", "success", "failure", "failed"),
            ("true", "success", "cancelled", "failed"),
            ("true", "success", "", "queued"),
        ):
            with self.subTest(expected=expected):
                needs = fixture()
                needs["resolve"]["outputs"]["should_deploy"] = eligible
                needs["verify"]["result"] = verified
                needs["deploy"] = {"result": deploy}
                self.assertEqual(build_report(needs, {}, [])["outcome"], expected)

    def test_restoration_and_duplicate_never_claim_fresh_deploy(self) -> None:
        for observation, expected, healthy in (
            (
                {"previous_sha": SHA, "healthy_at": END, "activated_at": END},
                "already_current",
                SHA,
            ),
            (
                {"restored_sha": OLD, "rollback_started_at": START, "restored_at": END},
                "failed_restored",
                OLD,
            ),
            ({"superseded_at": END}, "superseded", None),
        ):
            needs = fixture()
            needs["deploy"]["outputs"]["observation"] = json.dumps(
                {"release_sha": SHA, **observation}
            )
            report = build_report(needs, {}, [])
            self.assertEqual(report["outcome"], expected)
            self.assertEqual(report["healthy_sha"], healthy)
            self.assertIsNone(report["merge_to_healthy"]["seconds"])

    def test_missing_and_reversed_timestamps_are_explicit(self) -> None:
        self.assertEqual(duration(None, END)["unavailable_reason"], "missing_timestamp")
        self.assertEqual(duration(END, START)["unavailable_reason"], "reversed_timestamps")
        self.assertIsNone(duration("2026-09-05T10:00:00", END)["seconds"])
        report = build_report(
            fixture(),
            {"created_at": START},
            [{"name": "verify", "started_at": END, "completed_at": None}],
        )
        self.assertEqual(report["event_to_first_job"]["seconds"], 60)
        self.assertIn("unavailable", render_summary(report))

    def test_malformed_observation_is_not_success(self) -> None:
        for value in ("{", "[]", "null", ""):
            needs = copy.deepcopy(fixture())
            needs["deploy"]["outputs"]["observation"] = value
            self.assertEqual(build_report(needs, {}, [])["outcome"], "deployment_unconfirmed")

    def test_gate_reason_and_missing_pr_preserve_authorization(self) -> None:
        kwargs: dict[str, Any] = {
            "event_name": "push",
            "ref": "refs/heads/main",
            "release_sha": SHA,
            "auto_deploy_enabled": True,
            "associated_pull_requests": [],
        }
        self.assertEqual(gate_outputs(**kwargs)["gate_reason"], "missing_merged_pr")
        self.assertEqual(gate_outputs(**kwargs)["should_deploy"], "false")
        kwargs["associated_pull_requests"] = [
            {
                "state": "closed",
                "merge_commit_sha": SHA,
                "merged_at": START,
                "base": {"ref": "main"},
            }
        ]
        self.assertEqual(gate_outputs(**kwargs)["should_deploy"], "true")
        kwargs["auto_deploy_enabled"] = False
        self.assertEqual(gate_outputs(**kwargs)["gate_reason"], "auto_deploy_disabled")
        kwargs["event_name"] = "workflow_dispatch"
        self.assertEqual(gate_outputs(**kwargs)["should_deploy"], "true")

    def test_observation_roundtrip_is_atomic_private_and_run_specific(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            current, path = root / "current.json", root / "report.json"
            current.write_text(json.dumps({"release_sha": OLD, "config_file": "secret"}))
            record(path, "started", SHA, current)
            record(path, "healthy", SHA, current)
            record(path, "activated", SHA, current)
            data = json.loads(path.read_text())
            self.assertEqual(data["previous_sha"], OLD)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("secret", path.read_text())
            record(path, "started", SHA, current)
            self.assertNotIn("healthy_at", json.loads(path.read_text()))
            record(path, "rollback_started", SHA, current)
            record(path, "restored", SHA, current)
            self.assertEqual(json.loads(path.read_text())["restored_sha"], OLD)


if __name__ == "__main__":
    unittest.main()
