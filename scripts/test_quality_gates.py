"""Deliberate configuration faults must make the quality mapping fail closed."""

# ruff: noqa: D101, D102, PT009
from __future__ import annotations

import subprocess
import sys
import unittest
from io import StringIO
from unittest import mock

from scripts import check_quality_gates as quality
from scripts.check_quality_gates import FILES, ROOT, validate


class QualityGateTests(unittest.TestCase):
    def test_current_mapping(self) -> None:
        self.assertEqual(validate({p: (ROOT / p).read_text() for p in FILES}), [])

    def test_deliberate_gate_removal_is_rejected(self) -> None:
        faults = [
            (FILES[0], "Runtime images", "Renamed images"),
            (FILES[0], 'run: test "$RESULT" = success', "run: true"),
            (FILES[2], "uses: ./.github/workflows/verify.yml", "run: true"),
            (FILES[3], "Backend", "Renamed backend"),
            (FILES[4], "fail_under = 100", "fail_under = 80"),
            (FILES[4], "branch = true", "branch = false"),
            (FILES[4], 'source = ["wef_backend", "migrations"]', 'source = ["wef_backend"]'),
            (FILES[4], 'source = ["wef_backend", "migrations"]', 'source = ["migrations"]'),
            (FILES[4], '"error",', ""),
            (FILES[4], '"error",', '"error", "ignore",'),
            (FILES[6], "lines: 100", "lines: 99"),
            (FILES[6], "branches: 100", "removed: 100"),
            (FILES[6], "functions: 100", "functions: 99"),
            (FILES[6], "statements: 100", "statements: 99"),
            (FILES[6], "perFile: true", "perFile: false"),
            (FILES[6], '"src/**/*.{ts,tsx}",', '"src/lib/*.ts",'),
            (FILES[6], '"next.config.ts",', ""),
            (FILES[6], '"scripts/*.mjs",', ""),
            (
                FILES[6],
                '"../backend/src/wef_backend/features/admin/interface/statics/place_picker.js",',
                "",
            ),
            (FILES[6], "allowExternal: true", "allowExternal: false"),
            (
                FILES[6],
                '"src/generated/**",',
                '"src/generated/**", "src/components/**",',
            ),
            (FILES[6], '"src/test/**",', ""),
            (FILES[5], "--max-warnings 0", ""),
            (FILES[1], "contract:check", "contract:generate"),
            (FILES[1], "breaking --fail-on ERR", "breaking"),
            (
                FILES[1],
                "run: make quality-gates",
                "continue-on-error: true\n        run: make quality-gates",
            ),
            (FILES[1], "prove_architecture_violation.py", "removed.py"),
            (FILES[1], "lint-imports --config", "echo removed"),
            (FILES[1], "--cov-fail-under=100", "--cov-fail-under=80"),
            (FILES[1], "--cov-branch", ""),
            (FILES[1], "--cov=migrations", ""),
            (FILES[7], "--cov=migrations", ""),
            (FILES[1], "--fail-under 100", "--fail-under 99"),
            (FILES[7], "--cov-fail-under=100", "--cov-fail-under=99"),
            (FILES[7], "--fail-under 100", "--fail-under 99"),
            (FILES[7], "verify:", "removed:"),
            (FILES[7], "$(MAKE) coverage-operations", ""),
            (FILES[7], "--operations tmp/coverage/operations/coverage.json", ""),
            (FILES[9], 'source = ["scripts"]', 'source = ["scripts/transfer"]'),
            (FILES[9], "branch = true", "branch = false"),
            (FILES[9], 'patch = ["subprocess"]', "patch = []"),
            (FILES[9], '"scripts/prove_*.py",', '"scripts/prove_*.py", "scripts/deploy/*",'),
            (FILES[10], '"scripts/transfer/bundle.py"', '"scripts/missing-transfer.py"'),
            (
                FILES[10],
                '"scripts/deploy/activate_historical_candidate.py"',
                '"scripts/missing-activation.py"',
            ),
            (
                FILES[10],
                '"scripts/deploy/shared_edge_preflight.py"',
                '"scripts/missing-preflight.py"',
            ),
            (
                FILES[10],
                '"scripts/transfer/bundle.py": {"combined": 100}',
                '"scripts/transfer/bundle.py": {"combined": 99}',
            ),
        ]
        faults.extend(
            (
                FILES[10],
                f'"scripts/deploy/release_{name}.py"',
                f'"scripts/missing-release-{name}.py"',
            )
            for name in ("cache", "cohort", "observation", "order", "report", "state")
        )
        for path, before, after in faults:
            with self.subTest(path=path, fault=before):
                files = {p: (ROOT / p).read_text() for p in FILES}
                self.assertIn(before, files[path])
                files[path] = files[path].replace(before, after)
                self.assertTrue(validate(files))

    def test_command_prints_every_policy_error_and_returns_failure(self) -> None:
        with (
            mock.patch.object(quality, "validate", return_value=["synthetic policy failure"]),
            mock.patch("sys.stderr", new_callable=StringIO) as error,
        ):
            self.assertEqual(quality.main(), 1)
        self.assertEqual(error.getvalue(), "synthetic policy failure\n")
        result = subprocess.run(
            [sys.executable, "-m", "scripts.check_quality_gates"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
