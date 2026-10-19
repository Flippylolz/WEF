"""Synthetic Markdown target validation and existing deployment gate outputs."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import runpy
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import check_markdown_links as links
from scripts.deploy import evaluate_deploy_gate as gate

SHA = "a" * 40


class MarkdownBoundaryTests(unittest.TestCase):
    """Git enumeration is replaced; only invented temporary files are read."""

    def test_local_url_and_anchor_target_resolution(self) -> None:
        root = Path("/fixture/repository")
        source = root / "AI/nested/source.md"
        with mock.patch.object(links, "REPOSITORY_ROOT", root):
            for raw in (
                "",
                "   ",
                "#anchor",
                "https://example.invalid/path",
                "http://example.invalid/path",
                "mailto:fixture@example.invalid",
                "tel:+48123456789",
                "data:text/plain,fixture",
                "?query",
            ):
                with self.subTest(raw=raw):
                    self.assertIsNone(links.target_path(source, raw))
            self.assertEqual(
                links.target_path(source, " <../target%20file.md?view=1#anchor> "),
                source.parent / "../target file.md",
            )
            self.assertEqual(links.target_path(source, "/README.md#anchor"), root / "README.md")

    def test_git_enumeration_rejects_missing_tool_and_skips_deleted_files(self) -> None:
        with (
            mock.patch.object(links, "GIT", None),
            self.assertRaisesRegex(RuntimeError, "git is required"),
        ):
            links.repository_markdown_files()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / "source.md"
            existing.write_text("fixture", encoding="utf-8")
            with (
                mock.patch.object(links, "REPOSITORY_ROOT", root),
                mock.patch.object(links, "GIT", "/fixture/git"),
                mock.patch(
                    "scripts.check_markdown_links.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        [], 0, "source.md\n\nmissing.md\n", ""
                    ),
                ) as run,
            ):
                self.assertEqual(links.repository_markdown_files(), (existing,))
            run.assert_called_once_with(
                [
                    "/fixture/git",
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "*.md",
                ],
                check=True,
                cwd=root,
                capture_output=True,
                text=True,
            )

    def test_main_reports_missing_targets_and_module_exit_without_a_real_git_call(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.md"
            target = root / "target file.md"
            target.write_text("fixture", encoding="utf-8")
            source.write_text(
                "[target](target%20file.md) [external](https://example.invalid) [anchor](#local)\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(links, "REPOSITORY_ROOT", root),
                mock.patch.object(links, "repository_markdown_files", return_value=(source,)),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(links.main(), 0)
                self.assertIn("targets exist", out.getvalue())
                target.unlink()
                self.assertEqual(links.main(), 1)
                self.assertIn("source.md: target%20file.md", out.getvalue())
            with (
                mock.patch("shutil.which", return_value="/fixture/git"),
                mock.patch(
                    "subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")
                ),
                mock.patch("sys.stdout", new_callable=StringIO),
                self.assertRaises(SystemExit) as error,
            ):
                runpy.run_path(str(Path(links.__file__).resolve()), run_name="__main__")
            self.assertEqual(error.exception.code, 0)


class DeploymentGateBoundaryTests(unittest.TestCase):
    """API response fixtures cannot authorize a real release or deployment."""

    def test_gate_reasons_and_unavailable_or_malformed_merge_timestamps(self) -> None:
        good = {
            "state": "closed",
            "merged_at": "2026-10-19T00:00:00+00:00",
            "merge_commit_sha": SHA,
            "base": {"ref": "main"},
        }
        for event, ref, enabled, prs, expected, reason in (
            ("workflow_dispatch", "refs/heads/other", False, [], "true", "manual_dispatch"),
            ("push", "refs/heads/other", True, [], "false", "not_main_push"),
            ("other", "refs/heads/main", True, [], "false", "not_main_push"),
            ("push", "refs/heads/main", False, [], "false", "auto_deploy_disabled"),
            ("push", "refs/heads/main", True, [], "false", "missing_merged_pr"),
            ("push", "refs/heads/main", True, [good], "true", "merged_pr"),
        ):
            with self.subTest(event=event, ref=ref, enabled=enabled, reason=reason):
                report = gate.gate_outputs(
                    event_name=event,
                    ref=ref,
                    release_sha=SHA,
                    auto_deploy_enabled=enabled,
                    associated_pull_requests=prs,
                )
                self.assertEqual(report["should_deploy"], expected)
                self.assertEqual(report["gate_reason"], reason)
        for extra in (
            {"state": "open"},
            {"merge_commit_sha": "b" * 40},
            {"base": None},
            {"base": {"ref": "other"}},
            {"merged_at": 17},
            {"merged_at": "invalid"},
            {"merged_at": "2026-10-19T00:00:00"},
        ):
            report = gate.gate_outputs(
                event_name="push",
                ref="refs/heads/main",
                release_sha=SHA,
                auto_deploy_enabled=True,
                associated_pull_requests=[{**good, **extra}],
            )
            self.assertEqual(report["merged_at"], "")

    def test_response_shapes_and_both_cli_output_formats(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "pull-requests.json"
            for raw in ("{}", "[1]", "{"):
                path.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), self.assertRaises((TypeError, json.JSONDecodeError)):
                    gate.load_pull_requests(path)
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(gate.load_pull_requests(path), [])
            args = ["push", "refs/heads/main", SHA, "true", str(path)]
            for outputs in (False, True):
                with (
                    mock.patch.object(
                        sys, "argv", ["gate", *args, *(["--outputs"] if outputs else [])]
                    ),
                    mock.patch("sys.stdout", new_callable=StringIO) as out,
                ):
                    self.assertEqual(gate.main(), 0)
                self.assertEqual(
                    out.getvalue(),
                    "should_deploy=false\ngate_reason=missing_merged_pr\nmerged_at=\n"
                    if outputs
                    else "false\n",
                )
            child = subprocess.run(  # noqa: S603 - fixed gate CLI and synthetic API-response file
                [sys.executable, "-m", "scripts.deploy.evaluate_deploy_gate", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout, "false\n")


if __name__ == "__main__":
    unittest.main()
