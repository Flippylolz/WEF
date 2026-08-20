"""Unit tests for the Dependabot merge controller gates."""

# ruff: noqa: D101, D102, EM101, EM102, PT009, PT027, TC003, TRY003

from __future__ import annotations

import json
import unittest
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dependabot_merge_controller import (
    AUTOMERGE_LABEL,
    DEPENDABOT_LOGIN,
    Decision,
    PullRequestSnapshot,
    classify_semver_update,
    evaluate_candidate,
    infer_update_metadata,
    load_required_checks,
    process_repository,
)

REQUIRED = ("Backend", "Frontend and contract", "Repository safety", "Runtime images")
OWNERS = frozenset({"Flippylolz"})


def _pr(**overrides: object) -> PullRequestSnapshot:
    values: dict[str, object] = {
        "number": 42,
        "title": "Bump left-pad from 1.2.3 to 1.2.4",
        "state": "OPEN",
        "is_draft": False,
        "base_ref": "main",
        "head_ref": "dependabot/npm_and_yarn/left-pad-1.2.4",
        "head_oid": "abc123",
        "author_login": DEPENDABOT_LOGIN,
        "labels": frozenset({AUTOMERGE_LABEL}),
        "mergeable": "MERGEABLE",
        "body": "Updates `left-pad` from 1.2.3 to 1.2.4",
        "commits": ({"author_login": DEPENDABOT_LOGIN, "committer_login": DEPENDABOT_LOGIN},),
        "checks": tuple({"name": name, "state": "SUCCESS"} for name in REQUIRED),
        "label_events": (
            {
                "event": "labeled",
                "actor_login": "Flippylolz",
                "label": {"name": AUTOMERGE_LABEL},
            },
        ),
        "behind_by": 0,
        "update_types": frozenset({"version-update:semver-patch"}),
        "dependency_types": frozenset({"direct"}),
    }
    values.update(overrides)
    return PullRequestSnapshot(**values)  # type: ignore[arg-type]


class DependabotMergeControllerTests(unittest.TestCase):
    def test_load_required_checks(self) -> None:
        path = Path(".github/dependabot-required-checks.json")
        self.assertEqual(
            load_required_checks(path),
            (
                "Backend",
                "Frontend and contract",
                "Repository safety",
                "Runtime images",
            ),
        )

    def test_semver_classification(self) -> None:
        self.assertEqual(classify_semver_update("1.2.3", "1.2.4"), "version-update:semver-patch")
        self.assertEqual(classify_semver_update("1.2.3", "1.3.0"), "version-update:semver-minor")
        self.assertEqual(classify_semver_update("1.2.3", "2.0.0"), "version-update:semver-major")

    def test_infer_group_patch_minor_branch(self) -> None:
        updates, deps = infer_update_metadata(
            "Bump the npm-patch-minor group with 2 updates",
            "",
            "dependabot/npm_and_yarn/npm-patch-minor-deadbeef",
        )
        self.assertEqual(updates, frozenset({"version-update:semver-patch"}))
        self.assertEqual(deps, frozenset({"direct"}))

    def test_allow_eligible_patch(self) -> None:
        decision = evaluate_candidate(
            _pr(),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "merge")

    def test_reject_non_dependabot_author(self) -> None:
        decision = evaluate_candidate(
            _pr(author_login="human"),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision, Decision("reject", "author is not dependabot[bot]"))

    def test_reject_wrong_head_prefix(self) -> None:
        decision = evaluate_candidate(
            _pr(head_ref="feat/something"),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "reject")

    def test_defer_missing_automerge_label(self) -> None:
        decision = evaluate_candidate(
            _pr(labels=frozenset()),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")

    def test_reject_non_owner_label_actor(self) -> None:
        decision = evaluate_candidate(
            _pr(
                label_events=(
                    {
                        "event": "labeled",
                        "actor_login": "random-collaborator",
                        "label": {"name": AUTOMERGE_LABEL},
                    },
                )
            ),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "reject")
        self.assertIn("not allowlisted", decision.reason)

    def test_reject_major_update(self) -> None:
        decision = evaluate_candidate(
            _pr(update_types=frozenset({"version-update:semver-major"})),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "reject")
        self.assertIn("patch/minor", decision.reason)

    def test_reject_indirect_update(self) -> None:
        decision = evaluate_candidate(
            _pr(dependency_types=frozenset({"indirect"})),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "reject")

    def test_reject_human_commit(self) -> None:
        decision = evaluate_candidate(
            _pr(commits=({"author_login": "human", "committer_login": "web-flow"},)),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "reject")

    def test_defer_stale_base(self) -> None:
        decision = evaluate_candidate(
            _pr(behind_by=2),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")
        self.assertIn("rebase", decision.reason)

    def test_defer_missing_required_check(self) -> None:
        decision = evaluate_candidate(
            _pr(checks=tuple({"name": name, "state": "SUCCESS"} for name in REQUIRED[:3])),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")
        self.assertIn("Runtime images", decision.reason)

    def test_defer_failing_unrelated_check(self) -> None:
        checks = [{"name": name, "state": "SUCCESS"} for name in REQUIRED]
        checks.append({"name": "Coverage badge", "state": "FAILURE"})
        decision = evaluate_candidate(
            _pr(checks=tuple(checks)),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")
        self.assertIn("Coverage badge", decision.reason)

    def test_defer_pending_required_check(self) -> None:
        checks = [{"name": name, "state": "SUCCESS"} for name in REQUIRED]
        checks[0] = {"name": "Backend", "state": "PENDING"}
        decision = evaluate_candidate(
            _pr(checks=tuple(checks)),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")

    def test_defer_conflicts(self) -> None:
        decision = evaluate_candidate(
            _pr(mergeable="CONFLICTING"),
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            repository="Flippylolz/WEF",
        )
        self.assertEqual(decision.action, "defer")

    def test_reject_draft_and_wrong_base(self) -> None:
        self.assertEqual(
            evaluate_candidate(
                _pr(is_draft=True),
                required_checks=REQUIRED,
                owner_allowlist=OWNERS,
                repository="Flippylolz/WEF",
            ).action,
            "reject",
        )
        self.assertEqual(
            evaluate_candidate(
                _pr(base_ref="develop"),
                required_checks=REQUIRED,
                owner_allowlist=OWNERS,
                repository="Flippylolz/WEF",
            ).action,
            "reject",
        )

    def test_head_change_race_rejects_before_merge(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(command: Sequence[str]) -> str:
            args = tuple(command)
            calls.append(args)
            if args[:3] == ("gh", "pr", "list"):
                return json.dumps([{"number": 7}])
            if args[:3] == ("gh", "pr", "view"):
                # First evaluation uses abc, refetch uses def.
                head = (
                    "abc123"
                    if sum(1 for c in calls if c[:3] == ("gh", "pr", "view")) == 1
                    else "def456"
                )
                return json.dumps(
                    {
                        "number": 7,
                        "title": "Bump left-pad from 1.2.3 to 1.2.4",
                        "state": "OPEN",
                        "isDraft": False,
                        "baseRefName": "main",
                        "headRefName": "dependabot/npm_and_yarn/left-pad-1.2.4",
                        "headRefOid": head,
                        "author": {"login": DEPENDABOT_LOGIN},
                        "labels": [{"name": AUTOMERGE_LABEL}],
                        "mergeable": "MERGEABLE",
                        "body": "Updates left-pad from 1.2.3 to 1.2.4",
                        "commits": [],
                        "statusCheckRollup": [
                            {"name": name, "state": "SUCCESS", "conclusion": "SUCCESS"}
                            for name in REQUIRED
                        ],
                    }
                )
            if "pulls/7/commits" in " ".join(args):
                return json.dumps(
                    [
                        {
                            "sha": "1",
                            "author": {"login": DEPENDABOT_LOGIN},
                            "committer": {"login": DEPENDABOT_LOGIN},
                            "commit": {},
                        }
                    ]
                )
            if "issues/7/events" in " ".join(args):
                return json.dumps(
                    [
                        {
                            "event": "labeled",
                            "actor": {"login": "Flippylolz"},
                            "label": {"name": AUTOMERGE_LABEL},
                        }
                    ]
                )
            if "compare/main..." in " ".join(args):
                return json.dumps({"behind_by": 0, "ahead_by": 1})
            if args[:3] == ("gh", "pr", "merge"):
                raise AssertionError("merge must not run when head changes")
            raise AssertionError(f"unexpected command: {args}")

        results = process_repository(
            repository="Flippylolz/WEF",
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            runner=runner,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 7)
        self.assertEqual(results[0][1].action, "reject")
        self.assertIn("head SHA changed", results[0][1].reason)

    def test_process_dry_run_merge_path(self) -> None:
        def runner(command: Sequence[str]) -> str:
            args = tuple(command)
            if args[:3] == ("gh", "pr", "list"):
                return json.dumps([{"number": 9}])
            if args[:3] == ("gh", "pr", "view"):
                return json.dumps(
                    {
                        "number": 9,
                        "title": "Bump left-pad from 1.2.3 to 1.2.4",
                        "state": "OPEN",
                        "isDraft": False,
                        "baseRefName": "main",
                        "headRefName": "dependabot/npm_and_yarn/left-pad-1.2.4",
                        "headRefOid": "abc123",
                        "author": {"login": DEPENDABOT_LOGIN},
                        "labels": [{"name": AUTOMERGE_LABEL}],
                        "mergeable": "MERGEABLE",
                        "body": "Updates left-pad from 1.2.3 to 1.2.4",
                        "commits": [],
                        "statusCheckRollup": [
                            {"name": name, "state": "SUCCESS", "conclusion": "SUCCESS"}
                            for name in REQUIRED
                        ],
                    }
                )
            if "pulls/9/commits" in " ".join(args):
                return json.dumps(
                    [
                        {
                            "sha": "1",
                            "author": {"login": DEPENDABOT_LOGIN},
                            "committer": {"login": "web-flow"},
                            "commit": {},
                        }
                    ]
                )
            if "issues/9/events" in " ".join(args):
                return json.dumps(
                    [
                        {
                            "event": "labeled",
                            "actor": {"login": "Flippylolz"},
                            "label": {"name": AUTOMERGE_LABEL},
                        }
                    ]
                )
            if "compare/main..." in " ".join(args):
                return json.dumps({"behind_by": 0})
            if args[:3] == ("gh", "pr", "merge"):
                raise AssertionError("dry-run must not merge")
            raise AssertionError(f"unexpected command: {args}")

        results = process_repository(
            repository="Flippylolz/WEF",
            required_checks=REQUIRED,
            owner_allowlist=OWNERS,
            runner=runner,
            dry_run=True,
        )
        self.assertEqual(results[0][1].action, "merge")
        self.assertIn("dry-run", results[0][1].reason)

    def test_required_checks_file_rejects_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "checks.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_required_checks(path)


if __name__ == "__main__":
    unittest.main()
