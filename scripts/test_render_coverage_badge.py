"""Tests for the deterministic repository coverage badge."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.render_coverage_badge import (
    CoverageCounts,
    CoverageDataError,
    backend_counts,
    frontend_counts,
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


if __name__ == "__main__":
    unittest.main()
