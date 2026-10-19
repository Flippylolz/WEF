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
        errors = check(report, {"src/critical.py": {"combined": 95}}, backend=True)
        self.assertIn("50.00% < 95%", errors[0])

    def test_missing_or_ambiguous_measured_module_fails(self) -> None:
        cases: tuple[dict[str, object], ...] = ({}, {"a/src/core.py": {}, "b/src/core.py": {}})
        for files in cases:
            self.assertTrue(
                check({"files": files}, {"src/core.py": {"combined": 95}}, backend=True)
            )

    def test_frontend_checks_branches_independently_of_lines(self) -> None:
        report = {
            "/runner/src/core.ts": {
                "lines": {"covered": 100, "total": 100},
                "branches": {"covered": 90, "total": 100},
            }
        }
        errors = check(report, {"src/core.ts": {"lines": 98, "branches": 95}}, backend=False)
        self.assertEqual(len(errors), 1)
        self.assertIn("branches", errors[0])

    def test_zero_negative_boolean_counters_and_weak_policy_are_rejected(self) -> None:
        for covered, total, floor in (
            (0, 0, 95),
            (-1, 100, 95),
            (True, 100, 95),
            (101, 100, 95),
            (100, 100, 90),
        ):
            report = {
                "src/core.ts": {
                    "lines": {"covered": covered, "total": total},
                    "branches": {"covered": 100, "total": 100},
                }
            }
            with self.assertRaises(ValueError):
                check(report, {"src/core.ts": {"lines": floor, "branches": 95}}, backend=False)
        with self.assertRaises(ValueError):
            check({}, {}, backend=False)

    def test_exact_floor_and_absolute_paths_pass(self) -> None:
        report = {
            "/runner/src/core.ts": {
                "lines": {"covered": 95, "total": 100},
                "branches": {"covered": 95, "total": 100},
            }
        }
        self.assertEqual(
            check(report, {"src/core.ts": {"lines": 95, "branches": 95}}, backend=False), []
        )
