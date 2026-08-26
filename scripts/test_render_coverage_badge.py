"""Tests for the deterministic repository coverage badge."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.render_coverage_badge import (
    CoverageCounts,
    CoverageDataError,
    backend_counts,
    coverage_shortfalls,
    frontend_counts,
    main,
    render_badge,
)


class CoverageBadgeTests(unittest.TestCase):
    """Verify report parsing, aggregation, and SVG rendering."""

    def test_combines_coverage_counts(self) -> None:
        self.assertEqual(
            CoverageCounts(80, 100) + CoverageCounts(45, 50),
            CoverageCounts(125, 150),
        )

    def test_rejects_impossible_counts(self) -> None:
        with self.assertRaises(CoverageDataError):
            CoverageCounts(2, 1)

    def test_reads_backend_and_frontend_formats(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            backend = root / "backend.json"
            frontend = root / "frontend.json"
            backend.write_text(
                '{"totals":{"covered_lines":90,"num_statements":100,'
                '"covered_branches":8,"num_branches":10}}',
                encoding="utf-8",
            )
            frontend.write_text(
                '{"total":{"lines":{"covered":45,"total":50},"branches":{"covered":4,"total":5}}}',
                encoding="utf-8",
            )

            self.assertEqual(backend_counts(backend), CoverageCounts(98, 110))
            self.assertEqual(frontend_counts(frontend), CoverageCounts(49, 55))

    def test_renders_accessible_badge(self) -> None:
        badge = render_badge(93.14)

        self.assertIn("Repository branch-aware coverage: 93.1%", badge)
        self.assertIn('fill="#4c1"', badge)

    def test_shortfalls_ignore_totals_at_the_floor(self) -> None:
        self.assertEqual(
            coverage_shortfalls({"backend": CoverageCounts(90, 100)}, 90),
            (),
        )

    def test_shortfalls_include_totals_below_the_floor(self) -> None:
        self.assertEqual(
            coverage_shortfalls(
                {
                    "backend": CoverageCounts(91, 100),
                    "frontend": CoverageCounts(80, 100),
                },
                90,
            ),
            ("frontend 80.0%",),
        )

    def test_main_fails_when_coverage_is_below_the_floor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            backend, frontend, output = self._write_reports(root, backend=89, frontend=95)
            with (
                patch(
                    "sys.argv",
                    [
                        "render_coverage_badge.py",
                        "--backend",
                        str(backend),
                        "--frontend",
                        str(frontend),
                        "--output",
                        str(output),
                    ],
                ),
                patch("sys.stdout", StringIO()),
                patch("sys.stderr", StringIO()),
            ):
                self.assertEqual(main(), 1)
            self.assertTrue(output.is_file())

    def test_main_passes_when_every_total_meets_the_floor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            backend, frontend, output = self._write_reports(root, backend=91, frontend=90)
            with (
                patch(
                    "sys.argv",
                    [
                        "render_coverage_badge.py",
                        "--backend",
                        str(backend),
                        "--frontend",
                        str(frontend),
                        "--output",
                        str(output),
                        "--fail-under",
                        "90",
                    ],
                ),
                patch("sys.stdout", StringIO()),
                patch("sys.stderr", StringIO()),
            ):
                self.assertEqual(main(), 0)

    def test_github_actions_enforces_the_coverage_floor(self) -> None:
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        makefile = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("--cov-fail-under=90", workflow)
        self.assertIn("--fail-under 90", workflow)
        self.assertIn("--fail-under 90", makefile)
        self.assertIn("test-backend:", makefile)
        self.assertIn("test-frontend:", makefile)
        self.assertIn("coverage-backend:", makefile)
        self.assertIn("coverage-frontend:", makefile)
        compose = Path("infra/compose.yaml").read_text(encoding="utf-8")
        vitest = Path("apps/web/vitest.config.mts").read_text(encoding="utf-8")
        self.assertIn("--cov-fail-under=90", compose)
        self.assertIn("lines: 90", vitest)
        self.assertIn("branches: 90", vitest)

    def _write_reports(
        self,
        root: Path,
        *,
        backend: int,
        frontend: int,
    ) -> tuple[Path, Path, Path]:
        backend_path = root / "backend.json"
        frontend_path = root / "frontend.json"
        output = root / "coverage.svg"
        backend_path.write_text(
            '{"totals":{"covered_lines":'
            + str(backend)
            + ',"num_statements":100,"covered_branches":0,"num_branches":0}}',
            encoding="utf-8",
        )
        frontend_path.write_text(
            '{"total":{"lines":{"covered":'
            + str(frontend)
            + ',"total":100},"branches":{"covered":0,"total":0}}}',
            encoding="utf-8",
        )
        return backend_path, frontend_path, output


if __name__ == "__main__":
    unittest.main()
