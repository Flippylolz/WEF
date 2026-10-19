"""Coverage command reports must fail closed for every independently selected suite."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest import mock

from scripts import check_critical_coverage as coverage


class CriticalCoverageCliTests(unittest.TestCase):
    """Verify command routing, malformed evidence and an actual module invocation."""

    def test_each_suite_requires_its_own_policy_and_exact_counters(self) -> None:
        python_row = {
            "summary": {
                "covered_lines": 2,
                "num_statements": 2,
                "covered_branches": 2,
                "num_branches": 2,
            }
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github").mkdir()
            policy = {
                "backend": {"core.py": {"combined": 100}},
                "operations": {"tool.py": {"combined": 100}},
                "frontend": {"core.ts": {"lines": 100, "branches": 100}},
            }
            (root / ".github/critical-coverage.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )
            path = root / "report.json"
            for side, report in (
                ("backend", {"files": {"core.py": python_row}}),
                ("operations", {"files": {"tool.py": python_row}}),
                (
                    "frontend",
                    {
                        "core.ts": {
                            "lines": {"covered": 2, "total": 2},
                            "branches": {"covered": 2, "total": 2},
                        }
                    },
                ),
            ):
                path.write_text(json.dumps(report), encoding="utf-8")
                with (
                    self.subTest(side=side),
                    mock.patch.object(coverage, "ROOT", root),
                    mock.patch.object(
                        sys,
                        "argv",
                        ["critical-coverage", f"--{side}", str(path)],
                    ),
                    mock.patch("sys.stderr", new_callable=StringIO) as err,
                ):
                    self.assertEqual(coverage.main(), 0, err.getvalue())
                    self.assertEqual(err.getvalue(), "")
                    path.write_text("{}", encoding="utf-8")
                    self.assertEqual(coverage.main(), 1)
                    self.assertTrue(err.getvalue())
                    path.write_text("[]", encoding="utf-8")
                    self.assertEqual(coverage.main(), 1)
                    self.assertIn("Invalid critical coverage evidence", err.getvalue())

    def test_invalid_policy_rows_metrics_and_noninteger_counters_are_rejected(self) -> None:
        invalid_reports: tuple[object, ...] = ([], {"files": []}, {"files": {"core.py": []}})
        for report in invalid_reports:
            with self.subTest(report=report), self.assertRaises(TypeError):
                coverage.check(
                    cast("dict[str, object]", report), {"core.py": {"combined": 100}}, backend=True
                )
        row = {
            "summary": {
                "covered_lines": 1,
                "num_statements": 1,
                "covered_branches": 0,
                "num_branches": 0,
            }
        }
        report = {"files": {"core.py": row}}
        for floors in ({"lines": 100}, {"combined": 100, "extra": 100}):
            with (
                self.subTest(floors=floors),
                self.assertRaisesRegex(ValueError, "every required metric"),
            ):
                coverage.check(report, {"core.py": floors}, backend=True)
        for value in (1.5, "1", None):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "nonnegative integers"),
            ):
                coverage.check(
                    {"core.ts": {"lines": {"covered": value, "total": 1}}},
                    {"core.ts": {"lines": 100, "branches": 100}},
                    backend=False,
                )

    def test_real_module_entrypoint_rejects_an_empty_measured_inventory(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text('{"files":{}}', encoding="utf-8")
            result = subprocess.run(  # noqa: S603 - current Python and fixed repository module
                [
                    sys.executable,
                    "-m",
                    "scripts.check_critical_coverage",
                    "--operations",
                    str(path),
                ],
                cwd=Path(coverage.__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected exactly one measured file", result.stderr)
