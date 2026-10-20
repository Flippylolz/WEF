"""Reject incomplete, ambiguous and forged runtime shell coverage reports."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import check_critical_coverage as critical

SOURCE = "scripts/deploy/deploy.sh"
POLICY = {SOURCE: {"lines": 100}}


def report(*paths: str, covered: object = "100", total: object = "100") -> dict[str, object]:
    """Create invented Kcov counters; percentage labels intentionally carry no authority."""
    return {
        "files": [
            {"file": path, "covered_lines": covered, "total_lines": total, "percent_covered": "100"}
            for path in paths
        ],
        "covered_lines": len(paths) * int(str(covered)),
        "total_lines": len(paths) * int(str(total)),
        "percent_covered": "100",
    }


class ShellCoverageTests(unittest.TestCase):
    """The gate evaluates executable counters and the complete reviewed inventory."""

    def test_exact_absolute_paths_and_integer_or_string_file_counters(self) -> None:
        for path in (SOURCE, "/workspace/" + SOURCE):
            for value in (100, "100"):
                self.assertEqual(critical.check_shell(report(path, covered=value), POLICY), [])

    def test_rounded_percentage_cannot_hide_a_missing_line(self) -> None:
        errors = critical.check_shell(report(SOURCE, covered="9999", total="10000"), POLICY)
        self.assertEqual(len(errors), 1)
        self.assertIn("99.99% < 100%", errors[0])

    def test_missing_duplicate_ambiguous_and_unexpected_sources_are_refused(self) -> None:
        for paths, expected in (
            ((), "expected exactly one measured shell file"),
            ((SOURCE, SOURCE), "expected exactly one measured shell file"),
            (("/a/" + SOURCE, "/b/" + SOURCE), "expected exactly one measured shell file"),
            ((SOURCE, "invented-fixture.sh"), "unexpected measured shell file"),
        ):
            with self.subTest(paths=paths):
                self.assertTrue(
                    any(expected in error for error in critical.check_shell(report(*paths), POLICY))
                )

    def test_invalid_file_shapes_and_paths_are_refused(self) -> None:
        invalid_files: tuple[object, ...] = ({}, None, "files")
        for value in invalid_files:
            with self.subTest(value=value), self.assertRaises(TypeError):
                critical.check_shell({"files": value}, POLICY)
        for path in (None, 1, ""):
            evidence = report(SOURCE)
            evidence["files"] = [{"file": path}]
            with self.subTest(path=path), self.assertRaises(ValueError):
                critical.check_shell(evidence, POLICY)

    def test_invalid_unsigned_decimal_and_executable_counters_are_refused(self) -> None:
        for covered, total in (
            (True, "100"),
            (1.5, "100"),
            (-1, "100"),
            ("-1", "100"),
            (" 100", "100"),
            ("100.0", "100"),
            ("", "100"),
            ("\uff11\uff10\uff10", "100"),
            ("101", "100"),
            ("0", "0"),
        ):
            evidence = report(SOURCE)
            evidence["files"] = [{"file": SOURCE, "covered_lines": covered, "total_lines": total}]
            with self.subTest(covered=covered, total=total), self.assertRaises(ValueError):
                critical.check_shell(evidence, POLICY)

    def test_weak_missing_extra_and_noninteger_policy_metrics_are_refused(self) -> None:
        policies: tuple[dict[str, object], ...] = (
            {},
            {SOURCE: {}},
            {SOURCE: {"branches": 100}},
            {SOURCE: {"lines": 99}},
            {SOURCE: {"lines": True}},
            {SOURCE: {"lines": 100.0}},
            {SOURCE: {"lines": 100, "branches": 100}},
        )
        for policy in policies:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                critical.check_shell(report(SOURCE), policy)

    def test_inconsistent_and_boolean_global_counters_are_refused(self) -> None:
        good = report(SOURCE)
        for patch in (
            {"covered_lines": 99},
            {"total_lines": 101},
            {"covered_lines": True},
            {"total_lines": "100"},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                critical.check_shell({**good, **patch}, POLICY)

    def test_cli_reports_bounded_policy_errors_and_real_entrypoint_success(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github").mkdir()
            (root / ".github/critical-coverage.json").write_text(json.dumps({"shell": POLICY}))
            path = root / "coverage.json"
            for evidence, expected, message in (
                (report(SOURCE), 0, ""),
                (report(SOURCE, covered="99"), 1, "lines 99.00%"),
                ({"files": {}}, 1, "Invalid critical coverage evidence"),
                ({}, 1, "Invalid critical coverage evidence"),
            ):
                path.write_text(json.dumps(evidence))
                with (
                    self.subTest(evidence=evidence),
                    mock.patch.object(critical, "ROOT", root),
                    mock.patch.object(sys, "argv", ["critical", "--shell", str(path)]),
                    mock.patch("sys.stderr", new_callable=StringIO) as error,
                ):
                    self.assertEqual(critical.main(), expected)
                    self.assertIn(message, error.getvalue())
            policy = json.loads((critical.ROOT / ".github/critical-coverage.json").read_text())[
                "shell"
            ]
            complete = report(*policy)
            path.write_text(json.dumps(complete))
            result = subprocess.run(  # noqa: S603 - trusted Python and temporary synthetic report
                [sys.executable, "-m", "scripts.check_critical_coverage", "--shell", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
