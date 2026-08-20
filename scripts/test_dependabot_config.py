"""Structural checks for committed Dependabot configuration."""

# ruff: noqa: D101, D102, PT009

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = REPOSITORY_ROOT / ".github" / "dependabot.yml"


class DependabotConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = DEPENDABOT.read_text(encoding="utf-8")

    def test_version_and_required_ecosystems(self) -> None:
        self.assertRegex(self.raw, r"(?m)^version:\s*2\s*$")
        required = (
            ("package-ecosystem: npm", "directory: /"),
            ("package-ecosystem: pip", "directory: /apps/backend"),
            ("package-ecosystem: docker", "directory: /apps/backend"),
            ("package-ecosystem: docker", "directory: /apps/web"),
            ("package-ecosystem: github-actions", "directory: /"),
        )
        for ecosystem, directory in required:
            pattern = rf"{re.escape(ecosystem)}\n\s+{re.escape(directory)}"
            self.assertRegex(self.raw, pattern, msg=f"missing {ecosystem} @ {directory}")

    def test_weekly_schedule_and_bounded_open_prs(self) -> None:
        self.assertEqual(self.raw.count("interval: weekly"), 5)
        self.assertEqual(self.raw.count("open-pull-requests-limit: 5"), 5)

    def test_patch_minor_groups_exclude_major(self) -> None:
        self.assertGreaterEqual(self.raw.count("applies-to: version-updates"), 5)
        self.assertGreaterEqual(self.raw.count("- minor"), 5)
        self.assertGreaterEqual(self.raw.count("- patch"), 5)
        self.assertNotRegex(self.raw, r"(?m)^\s*- major\s*$")

    def test_merge_controller_workflow_present_with_no_pr_checkout_of_head(self) -> None:
        workflow = REPOSITORY_ROOT / ".github" / "workflows" / "dependabot-merge.yml"
        self.assertTrue(workflow.is_file())
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", text)
        self.assertNotIn("pull_request_target", text)
        self.assertIn("cancel-in-progress: false", text)


if __name__ == "__main__":
    unittest.main()
