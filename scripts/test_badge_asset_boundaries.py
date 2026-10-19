"""Coverage report refusal, badge colors and safe MapLibre asset CLI paths."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import render_coverage_badge as badge
from scripts.deploy import maplibre_assets as assets


class BadgeAssetBoundaryTests(unittest.TestCase):
    """Temporary reports/assets are invented and no JavaScript is executed."""

    def test_badge_report_object_counter_types_and_colors(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            payload: object
            for payload in (
                [],
                {},
                {"totals": []},
                {"totals": {"covered_lines": True}},
                {"totals": {"covered_lines": "1"}},
            ):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(badge.CoverageDataError):
                    badge.backend_counts(path)
            path.write_text('{"total":{"lines":[]}}', encoding="utf-8")
            with self.assertRaises(badge.CoverageDataError):
                badge.frontend_counts(path)
        for covered, total in ((-1, 1), (0, 0)):
            with (
                self.subTest(covered=covered, total=total),
                self.assertRaises(badge.CoverageDataError),
            ):
                badge.CoverageCounts(covered, total)
        for percentage, color in ((100, "#4c1"), (85, "#dfb317"), (50, "#e05d44")):
            self.assertIn(f'fill="{color}"', badge.render_badge(percentage))

    def test_badge_real_cli_and_asset_argument_count_and_real_cli(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            backend, frontend, output = (
                root / "backend.json",
                root / "frontend.json",
                root / "output/coverage.svg",
            )
            backend.write_text(
                '{"totals":{"covered_lines":1,"num_statements":1,"covered_branches":1,"num_branches":1}}',
                encoding="utf-8",
            )
            frontend.write_text(
                '{"total":{"lines":{"covered":1,"total":1},"branches":{"covered":0,"total":0}}}',
                encoding="utf-8",
            )
            child = subprocess.run(  # noqa: S603 - fixed badge CLI and invented report paths
                [
                    sys.executable,
                    "-m",
                    "scripts.render_coverage_badge",
                    "--backend",
                    str(backend),
                    "--frontend",
                    str(frontend),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertIn("Repository branch-aware coverage: 100.0%", output.read_text())
            headers, worker, shared = root / "headers.txt", root / "worker.mjs", root / "shared.mjs"
            headers.write_text("Content-Type: text/javascript\n", encoding="utf-8")
            worker.write_text(
                "self.addEventListener('message', () => self.postMessage('fixture'));",
                encoding="utf-8",
            )
            shared.write_text("", encoding="utf-8")
            paths = [str(headers), str(worker), str(shared)]
            with mock.patch.object(sys, "argv", ["assets", *paths]):
                self.assertEqual(assets.main(), 0)
            with (
                mock.patch.object(sys, "argv", ["assets"]),
                self.assertRaisesRegex(SystemExit, "usage:"),
            ):
                assets.main()
            child = subprocess.run(  # noqa: S603 - fixed asset CLI and invented text files
                [sys.executable, "-m", "scripts.deploy.maplibre_assets", *paths],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
