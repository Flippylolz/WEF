"""Synthetic regressions for exact, verified Dependabot merge evidence."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest import mock

from scripts import dependabot_merge_controller as controller
from scripts.test_dependabot_merge_controller import OWNERS, REQUIRED, _pr

if TYPE_CHECKING:
    from collections.abc import Sequence


class DependabotEvidenceRegressionTests(unittest.TestCase):
    """Pure snapshots and an injected command runner can never merge a real PR."""

    def test_required_checks_need_success_even_when_optional_checks_may_skip(self) -> None:
        original = _pr()
        for value in ("SKIPPED", "NEUTRAL"):
            checks = tuple(
                {**check, "state": value} if check["name"] == "Backend" else check
                for check in original.checks
            )
            with self.subTest(value=value):
                decision = controller.evaluate_candidate(
                    replace(original, checks=checks),
                    required_checks=REQUIRED,
                    owner_allowlist=OWNERS,
                    repository="fixture/repo",
                )
                self.assertEqual(decision.action, "defer")

    def test_missing_commit_evidence_cannot_authorize_a_merge(self) -> None:
        decision = controller.evaluate_candidate(
            _pr(commits=()),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="fixture/repo",
        )
        self.assertEqual(decision.action, "reject")

    def test_completed_check_without_a_conclusion_is_not_inferred_successful(self) -> None:
        view = {
            "number": 7,
            "title": "Bump fixture from 1.2.3 to 1.2.4",
            "state": "OPEN",
            "baseRefName": "main",
            "headRefName": "dependabot/fixture",
            "headRefOid": "a" * 40,
            "author": {"login": controller.DEPENDABOT_LOGIN},
            "labels": [{"name": "automerge"}],
            "mergeable": "MERGEABLE",
            "statusCheckRollup": [{"name": "Backend", "status": "COMPLETED"}],
        }
        runner = mock.Mock(side_effect=[json.dumps(view), "[]", "[]", "{}"])
        snapshot = controller.fetch_pull_request(7, repository="fixture/repo", runner=runner)
        self.assertNotEqual(snapshot.checks[0]["state"], "SUCCESS")

    def test_commit_display_names_cannot_replace_missing_github_identities(self) -> None:
        view = {"number": 7}
        commits = [
            {
                "sha": "b" * 40,
                "author": None,
                "committer": None,
                "commit": {
                    "author": {"name": "dependabot[bot]"},
                    "committer": {"name": "web-flow"},
                },
            }
        ]
        runner = mock.Mock(side_effect=[json.dumps(view), json.dumps(commits), "[]", "{}"])
        snapshot = controller.fetch_pull_request(7, repository="fixture/repo", runner=runner)
        self.assertEqual(snapshot.commits[0]["author_login"], "")
        self.assertEqual(snapshot.commits[0]["committer_login"], "")

    def test_invalid_check_configuration_and_unclassifiable_versions_fail_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "checks.json"
            payload: object
            for payload in (
                [],
                {"required_check_names": []},
                {"required_check_names": [""]},
                {"required_check_names": [1]},
            ):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    controller.load_required_checks(path)
        for old, new in (("bad", "1.2.3"), ("1.2.3", "bad"), ("1.2.3", "1.2.3")):
            self.assertIsNone(controller.classify_semver_update(old, new))
        self.assertEqual(
            controller.infer_update_metadata("from 1.2.3 to 1.2.3", "", "dependabot/same")[0],
            frozenset(),
        )
        updates, dependencies = controller.infer_update_metadata(
            "indirect update", "", "dependabot/major-group"
        )
        self.assertEqual(updates, frozenset({"version-update:semver-major"}))
        self.assertEqual(dependencies, frozenset({"indirect"}))

    def test_candidate_unknown_identity_checks_and_mergeability_never_authorize(self) -> None:
        cases: tuple[dict[str, object], ...] = (
            {"state": "CLOSED"},
            {"label_events": ()},
            {"update_types": frozenset()},
            {
                "commits": (
                    {"author_login": controller.DEPENDABOT_LOGIN, "committer_login": "human"},
                )
            },
            {"mergeable": None},
            {"mergeable": "UNKNOWN"},
            {"mergeable": "unrecognized"},
            {"checks": (*_pr().checks, {"name": "other", "state": "unexpected"})},
        )
        for values in cases:
            with self.subTest(values=values):
                decision = controller.evaluate_candidate(
                    _pr(**values),
                    required_checks=REQUIRED,
                    owner_allowlist=OWNERS,
                    repository="fixture/repo",
                )
                self.assertNotEqual(decision.action, "merge")
        events = (
            {"event": "commented", "label": {"name": "automerge"}},
            {"event": "labeled", "label": {"name": "unrelated"}},
            {"event": "labeled", "label": None},
            {"event": "labeled", "label": "automerge", "actor_login": "Flippylolz"},
        )
        optional = (*_pr().checks, {"state": "SUCCESS"}, {"name": "optional", "state": "SKIPPED"})
        self.assertEqual(
            controller.evaluate_candidate(
                _pr(label_events=events, checks=optional),
                required_checks=REQUIRED,
                owner_allowlist=OWNERS,
                repository="fixture/repo",
            ).action,
            "merge",
        )

    def test_api_snapshot_normalizes_only_verified_fields_and_retains_incomplete_checks(
        self,
    ) -> None:
        view = {
            "number": 7,
            "title": "fixture",
            "author": None,
            "labels": [None, {}, {"name": "automerge"}],
            "mergeable": None,
            "statusCheckRollup": [
                None,
                {"name": "conclusion", "conclusion": "SUCCESS"},
                {"name": "context", "state": "SUCCESS"},
                {"name": "empty"},
                {"name": "running", "status": "IN_PROGRESS"},
            ],
        }
        commits = [
            None,
            {
                "sha": "a",
                "author": {"login": controller.DEPENDABOT_LOGIN},
                "committer": {"login": "web-flow"},
            },
        ]
        events = [
            None,
            {"event": "labeled", "label": {"name": "automerge"}, "actor": {"login": "Flippylolz"}},
        ]
        runner = mock.Mock(
            side_effect=[json.dumps(view), json.dumps(commits), json.dumps(events), "{}"]
        )
        snapshot = controller.fetch_pull_request(7, repository="fixture/repo", runner=runner)
        self.assertEqual(
            [row["state"] for row in snapshot.checks],
            ["SUCCESS", "SUCCESS", "PENDING", "IN_PROGRESS"],
        )
        self.assertEqual(snapshot.labels, frozenset({"automerge"}))
        self.assertIsNone(snapshot.mergeable)
        self.assertEqual(snapshot.commits[0]["committer_login"], "web-flow")
        self.assertEqual(snapshot.label_events[0]["actor_login"], "Flippylolz")
        runner.side_effect = [json.dumps(view), "{}", "{}", "{}"]
        empty = controller.fetch_pull_request(7, repository="fixture/repo", runner=runner)
        self.assertEqual(empty.commits, ())
        self.assertEqual(empty.label_events, ())

    def test_gh_process_errors_keep_diagnostics_without_a_real_command(self) -> None:
        with mock.patch("scripts.dependabot_merge_controller.subprocess.run") as run:
            for stdout, stderr, detail in (
                ("", "synthetic denial", "synthetic denial"),
                ("synthetic output", "", "synthetic output"),
                ("", "", "exit 1"),
            ):
                run.return_value = subprocess.CompletedProcess([], 1, stdout, stderr)
                with self.subTest(detail=detail), self.assertRaisesRegex(RuntimeError, detail):
                    controller.list_automerge_pull_numbers(repository="fixture/repo")
            run.return_value = subprocess.CompletedProcess([], 0, '[{"number":7},null,{}]', "")
            self.assertEqual(controller.list_automerge_pull_numbers(repository="fixture/repo"), [7])
        commands: list[tuple[str, ...]] = []

        def injected(command: Sequence[str]) -> str:
            commands.append(tuple(command))
            return ""

        controller.merge_pull_request(
            7, head_oid="a" * 40, repository="fixture/repo", runner=injected
        )
        self.assertEqual(commands[0][-2:], ("--match-head-commit", "a" * 40))
        self.assertIn("--squash", commands[0])
        self.assertIn("--delete-branch", commands[0])

    def test_process_refetch_and_merge_failures_are_recorded_without_real_merges(self) -> None:
        valid = _pr()
        for snapshots, expected in (
            ([_pr(labels=frozenset())], "defer"),
            ([valid, _pr(labels=frozenset())], "defer"),
        ):
            with (
                self.subTest(expected=expected),
                mock.patch.object(controller, "list_automerge_pull_numbers", return_value=[7]),
                mock.patch.object(
                    controller,
                    "fetch_pull_request",
                    side_effect=snapshots,
                ),
                mock.patch.object(controller, "merge_pull_request") as merge,
            ):
                result = controller.process_repository(
                    repository="fixture/repo", required_checks=REQUIRED, owner_allowlist=OWNERS
                )
                self.assertEqual(result[0][1].action, expected)
                merge.assert_not_called()
        for error, expected in (
            (None, "merge"),
            (RuntimeError("head mismatch"), "reject"),
            (RuntimeError("synthetic unavailable"), "defer"),
        ):
            with (
                self.subTest(error=error),
                mock.patch.object(controller, "list_automerge_pull_numbers", return_value=[7]),
                mock.patch.object(
                    controller,
                    "fetch_pull_request",
                    side_effect=[valid, valid],
                ),
                mock.patch.object(controller, "merge_pull_request", side_effect=error) as merge,
            ):
                result = controller.process_repository(
                    repository="fixture/repo", required_checks=REQUIRED, owner_allowlist=OWNERS
                )
                self.assertEqual(result[0][1].action, expected)
                merge.assert_called_once_with(
                    7, head_oid=valid.head_oid, repository="fixture/repo", runner=None
                )

    def test_cli_owner_options_summary_and_invalid_repository_entrypoint(self) -> None:
        with (
            mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": ""}),
            mock.patch("sys.stderr", new_callable=StringIO),
        ):
            self.assertEqual(controller.main([]), 2)
        with TemporaryDirectory() as temporary:
            summary = Path(temporary) / "summary.md"
            for owners in ([], ["--owner", "fixture-owner", "--owner", "second-owner"]):
                with (
                    self.subTest(owners=owners),
                    mock.patch.dict(
                        os.environ,
                        {"GITHUB_REPOSITORY": "fixture/repo", "GITHUB_STEP_SUMMARY": str(summary)},
                    ),
                    mock.patch.object(
                        controller,
                        "process_repository",
                        return_value=[(7, controller.Decision("defer", "synthetic reason"))],
                    ) as process,
                    mock.patch("sys.stdout", new_callable=StringIO),
                ):
                    self.assertEqual(controller.main(["--dry-run", *owners]), 0)
                    self.assertTrue(process.call_args.kwargs["dry_run"])
                    self.assertEqual(
                        process.call_args.kwargs["owner_allowlist"],
                        frozenset({"fixture-owner", "second-owner"})
                        if owners
                        else controller.DEFAULT_OWNER_ALLOWLIST,
                    )
            self.assertIn("synthetic reason", summary.read_text())
            with (
                mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                controller.write_step_summary([], None)
                self.assertIn("No open", out.getvalue())
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.dependabot_merge_controller",
                    "--repository",
                    "invalid",
                ],
                cwd=Path(controller.__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("owner/name", result.stderr)
