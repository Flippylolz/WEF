"""Deliberate configuration faults must make the quality mapping fail closed."""

# ruff: noqa: D101, D102, PT009
from __future__ import annotations

import unittest

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
            (FILES[4], "fail_under = 90", "fail_under = 80"),
            (FILES[4], '"error",', ""),
            (FILES[4], '"error",', '"error", "ignore",'),
            (FILES[6], "lines: 90", "lines: 80"),
            (FILES[6], "branches: 90", "removed: 90"),
            (FILES[5], "--max-warnings 0", ""),
            (FILES[1], "contract:check", "contract:generate"),
            (FILES[1], "breaking --fail-on ERR", "breaking"),
            (FILES[1], "prove_architecture_violation.py", "removed.py"),
            (FILES[1], "lint-imports --config", "echo removed"),
            (FILES[1], "--cov-fail-under=90", "--cov-fail-under=80"),
            (FILES[7], "verify:", "removed:"),
        ]
        for path, before, after in faults:
            with self.subTest(path=path, fault=before):
                files = {p: (ROOT / p).read_text() for p in FILES}
                self.assertIn(before, files[path])
                files[path] = files[path].replace(before, after)
                self.assertTrue(validate(files))
