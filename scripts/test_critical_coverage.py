"""Reject missing and deceptively high aggregate critical-path coverage."""

# ruff: noqa: D101, D102, PT009, PT027
from __future__ import annotations

import unittest

from scripts.check_critical_coverage import check


class CriticalCoverageTests(unittest.TestCase):
    def test_high_global_total_cannot_hide_low_critical_module(self) -> None:
        report = {
            "totals": {"percent_covered": 100},
            "files": {
                "src/critical.py": {
                    "summary": {
                        "covered_lines": 100,
                        "num_statements": 100,
                        "covered_branches": 0,
                        "num_branches": 100,
                    }
                }
            },
        }
        errors = check(report, {"src/critical.py": {"combined": 100}}, backend=True)
        self.assertIn("50.00% < 100%", errors[0])

    def test_missing_or_ambiguous_measured_module_fails(self) -> None:
        cases: tuple[dict[str, object], ...] = (
            {},
            {"a/src/core.py": {}, "b/src/core.py": {}},
        )
        for files in cases:
            self.assertTrue(
                check({"files": files}, {"src/core.py": {"combined": 100}}, backend=True)
            )

    def test_frontend_checks_branches_independently_of_lines(self) -> None:
        report = {
            "/runner/src/core.ts": {
                "lines": {"covered": 100, "total": 100},
                "branches": {"covered": 90, "total": 100},
            }
        }
        errors = check(report, {"src/core.ts": {"lines": 100, "branches": 100}}, backend=False)
        self.assertEqual(len(errors), 1)
        self.assertIn("branches", errors[0])

    def test_zero_negative_boolean_counters_and_weak_policy_are_rejected(self) -> None:
        for covered, total, floor in (
            (0, 0, 100),
            (-1, 100, 100),
            (True, 100, 100),
            (101, 100, 100),
            (100, 100, 99),
        ):
            report = {
                "src/core.ts": {
                    "lines": {"covered": covered, "total": total},
                    "branches": {"covered": 100, "total": 100},
                }
            }
            with self.assertRaises(ValueError):
                check(
                    report,
                    {"src/core.ts": {"lines": floor, "branches": 100}},
                    backend=False,
                )
        with self.assertRaises(ValueError):
            check({}, {}, backend=False)

    def test_exact_floor_and_absolute_paths_pass(self) -> None:
        report = {
            "/runner/src/core.ts": {
                "lines": {"covered": 100, "total": 100},
                "branches": {"covered": 100, "total": 100},
            }
        }
        self.assertEqual(
            check(report, {"src/core.ts": {"lines": 100, "branches": 100}}, backend=False),
            [],
        )

    def test_source_without_conditions_has_no_branch_shortfall(self) -> None:
        report = {
            "next.config.ts": {
                "lines": {"covered": 11, "total": 11},
                "branches": {"covered": 0, "total": 0},
            }
        }
        policy = {"next.config.ts": {"lines": 100, "branches": 100}}
        self.assertEqual(check(report, policy, backend=False), [])
        report["next.config.ts"]["lines"] = {"covered": 10, "total": 11}
        self.assertTrue(check(report, policy, backend=False))
        report["next.config.ts"]["lines"] = {"covered": 0, "total": 0}
        with self.assertRaises(ValueError):
            check(report, policy, backend=False)
