"""Synthetic artifact integrity, trusted reuse and fallback boundaries."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import create_checksums as checksums
from scripts.deploy import create_release_manifest as manifest
from scripts.deploy import reuse_release as reuse
from scripts.test_release_order import FINGERPRINT, IMAGES, SHA, bundle

REPOSITORY = "Flippylolz/WEF"


def trusted_fixture() -> dict[str, object]:
    """Invent exact-source main-push evidence without an API request."""
    return {
        "id": 7,
        "event": "push",
        "conclusion": "success",
        "status": "completed",
        "head_sha": SHA,
        "head_branch": "main",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "path": ".github/workflows/deploy-production.yml",
    }


def trusted_jobs() -> list[dict[str, str]]:
    """Return one completed successful result for every required job."""
    return [
        {"name": "Verify / " + name, "status": "completed", "conclusion": "success"}
        for name in sorted(reuse.REQUIRED_JOBS)
    ]


def rewrite_checksums(root: Path) -> None:
    """Use the real checksum entrypoint on a temporary synthetic artifact."""
    with mock.patch.object(sys, "argv", ["checksums", str(root)]):
        checksums.main()


class ReleaseArtifactBoundaryTests(unittest.TestCase):
    """No test lists, downloads or changes an actual GitHub artifact."""

    def test_checksums_are_sorted_complete_stable_and_stream_large_files(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested").mkdir()
            payload = b"synthetic-bounded-chunks\n" * 100000
            (root / "nested/z").write_bytes(payload)
            (root / "a").write_bytes(b"")
            rewrite_checksums(root)
            expected = (
                f"{hashlib.sha256(b'').hexdigest()}  a\n"
                f"{hashlib.sha256(payload).hexdigest()}  nested/z\n"
            )
            self.assertEqual((root / "SHA256SUMS").read_text(), expected)
            rewrite_checksums(root)
            self.assertEqual((root / "SHA256SUMS").read_text(), expected)
            completed = subprocess.run(  # noqa: S603 - fixed CLI and synthetic fixture arguments
                [sys.executable, "-m", "scripts.deploy.create_checksums", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((root / "SHA256SUMS").read_text(), expected)

    def test_manifest_identity_digests_timestamp_and_cli_fingerprint(self) -> None:
        timestamp = "2026-10-19T00:00:00+00:00"
        for sha, time, backend, web in (
            ("bad", timestamp, IMAGES["backend"], IMAGES["web"]),
            (SHA, timestamp, "backend:mutable", IMAGES["web"]),
            (SHA, timestamp, IMAGES["backend"], "web:mutable"),
            (SHA, "invalid-time", IMAGES["backend"], IMAGES["web"]),
        ):
            with (
                self.subTest(sha=sha, time=time, backend=backend, web=web),
                self.assertRaises(ValueError),
            ):
                manifest.create_manifest(sha, time, "migration-fixture", backend, web)
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "manifest.json"
            args = [
                str(output),
                SHA,
                timestamp,
                "migration-fixture",
                IMAGES["backend"],
                IMAGES["web"],
            ]
            for fingerprint in (None, FINGERPRINT):
                with mock.patch.object(
                    sys,
                    "argv",
                    [
                        "manifest",
                        *args,
                        *(
                            []
                            if fingerprint is None
                            else ["--verification-fingerprint", fingerprint]
                        ),
                    ],
                ):
                    self.assertEqual(manifest.main(), 0)
                result = json.loads(output.read_text())
                self.assertEqual(result["source_sha"], SHA)
                self.assertEqual(result["images"], IMAGES)
                self.assertEqual(result.get("verification_fingerprint"), fingerprint)
                self.assertTrue(output.read_text().endswith("\n"))
            for invalid_args, diagnostic in (
                ([*args, "--verification-fingerprint", "bad"], "fingerprint must be SHA-256"),
                ([str(output), "bad", *args[2:]], "40 lowercase"),
            ):
                with (
                    mock.patch.object(sys, "argv", ["manifest", *invalid_args]),
                    mock.patch("sys.stderr", new_callable=StringIO) as err,
                    self.assertRaises(SystemExit) as error,
                ):
                    manifest.main()
                self.assertEqual(error.exception.code, 2)
                self.assertIn(diagnostic, err.getvalue())

    def test_bundle_refuses_malformed_shapes_without_uncaught_attribute_errors(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle(root)
            path = root / "release-manifest.json"
            original = json.loads(path.read_text())
            payload: object
            for payload in ([], None, {**original, "images": []}, {**original, "images": None}):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(TypeError):
                    reuse.validate_bundle(root, SHA, FINGERPRINT)

    def test_bundle_rejects_corrupt_duplicate_foreign_and_incomplete_inventory(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for change in (
                "bad-digest",
                "symlink",
                "bad-checksum",
                "duplicate",
                "outside",
                "corrupt-file",
                "missing-file",
                "missing-required",
            ):
                bundle(root)
                checksum_file = root / "SHA256SUMS"
                original = checksum_file.read_text()
                if change == "bad-digest":
                    path = root / "release-manifest.json"
                    value = json.loads(path.read_text())
                    value["images"]["backend"] = 123
                    path.write_text(json.dumps(value))
                elif change == "symlink":
                    (root / "linked").symlink_to("release-manifest.json")
                elif change == "bad-checksum":
                    checksum_file.write_text("invalid  release-manifest.json\n")
                elif change == "duplicate":
                    checksum_file.write_text(original + original.splitlines()[0] + "\n")
                elif change == "outside":
                    checksum_file.write_text("0" * 64 + "  ../outside\n")
                elif change == "corrupt-file":
                    (root / "compose.production.yaml").write_text("corrupt")
                elif change == "missing-file":
                    (root / "compose.production.yaml").unlink()
                else:
                    (root / "compose.production.yaml").unlink()
                    rewrite_checksums(root)
                with (
                    self.subTest(change=change),
                    self.assertRaisesRegex(
                        ValueError, "digest evidence|symlinks|checksum|inventory"
                    ),
                ):
                    reuse.validate_bundle(root, SHA, FINGERPRINT)
                (root / "linked").unlink(missing_ok=True)

    def test_fingerprint_requires_trusted_revision_and_hashes_all_definition_paths(self) -> None:
        self.assertEqual(
            reuse.FINGERPRINT_PATHS,
            (
                ".github/workflows/verify.yml",
                ".github/workflows/deploy-production.yml",
                ".github/actions/runtime-image/action.yml",
                "Makefile",
                ".tool-versions",
                "scripts/prove_release_workflow.py",
                "apps/backend/uv.lock",
                "pnpm-lock.yaml",
            ),
        )
        for executable, revision in ((None, SHA), ("/fixture/git", "bad")):
            with (
                mock.patch("scripts.deploy.reuse_release.shutil.which", return_value=executable),
                mock.patch("scripts.deploy.reuse_release.subprocess.check_output") as show,
                self.assertRaisesRegex(ValueError, "trusted workflow revision"),
            ):
                reuse.fingerprint(revision)
            show.assert_not_called()
        with (
            mock.patch("scripts.deploy.reuse_release.shutil.which", return_value="/fixture/git"),
            mock.patch(
                "scripts.deploy.reuse_release.subprocess.check_output",
                return_value=b"synthetic-content",
            ) as show,
        ):
            first = reuse.fingerprint(SHA)
            self.assertEqual(len(first), 64)
            self.assertEqual(
                show.call_args_list,
                [
                    mock.call(["/fixture/git", "show", f"{SHA}:{path}"])
                    for path in reuse.FINGERPRINT_PATHS
                ],
            )
        with (
            mock.patch("scripts.deploy.reuse_release.shutil.which", return_value="/fixture/git"),
            mock.patch(
                "scripts.deploy.reuse_release.subprocess.check_output",
                return_value=b"changed-content",
            ),
        ):
            self.assertNotEqual(reuse.fingerprint(SHA), first)

    def test_run_trust_rejects_non_main_wrong_workflow_and_incomplete_jobs(self) -> None:
        for extra in (
            {"status": "queued"},
            {"head_branch": "other"},
            {"repository": {"full_name": "other/repo"}},
            {"path": "other.yml"},
        ):
            self.assertFalse(
                reuse.trusted_run({**trusted_fixture(), **extra}, trusted_jobs(), SHA, REPOSITORY)
            )
        self.assertFalse(
            reuse.trusted_run(
                trusted_fixture(),
                [{**job, "status": "queued"} for job in trusted_jobs()],
                SHA,
                REPOSITORY,
            )
        )

    def test_find_falls_back_for_untrusted_missing_failed_and_invalid_downloads(self) -> None:
        with (
            mock.patch("scripts.deploy.reuse_release.shutil.which", return_value=None),
            mock.patch.object(reuse, "read_api") as api,
        ):
            self.assertEqual(reuse.find_reusable(REPOSITORY, SHA, FINGERPRINT), "")
            api.assert_not_called()
        for scenario in (
            "no-id",
            "untrusted",
            "download-fails",
            "invalid-bundle",
            "malformed-bundle",
            "success",
        ):
            run = {} if scenario == "no-id" else trusted_fixture()
            if scenario == "untrusted":
                run = {**run, "event": "workflow_dispatch"}
            responses = [
                {"workflow_runs": [run]},
                {"jobs": trusted_jobs()},
                {"artifacts": [{"name": f"release-{SHA}", "expired": False}]},
            ]

            def download(
                command: list[str], *, scenario: str = scenario, **_options: object
            ) -> subprocess.CompletedProcess[bytes]:
                destination = Path(command[command.index("--dir") + 1])
                self.assertEqual(command[:3], ["/fixture/gh", "run", "download"])
                self.assertIn(REPOSITORY, command)
                if scenario in {"success", "malformed-bundle"}:
                    bundle(destination)
                    if scenario == "malformed-bundle":
                        (destination / "release-manifest.json").write_text("[]", encoding="utf-8")
                return subprocess.CompletedProcess(
                    command, 1 if scenario == "download-fails" else 0, b"", b""
                )

            with (
                self.subTest(scenario=scenario),
                mock.patch("scripts.deploy.reuse_release.shutil.which", return_value="/fixture/gh"),
                mock.patch.object(reuse, "read_api", side_effect=responses),
                mock.patch(
                    "scripts.deploy.reuse_release.subprocess.run", side_effect=download
                ) as mocked_download,
            ):
                self.assertEqual(
                    reuse.find_reusable(REPOSITORY, SHA, FINGERPRINT),
                    "7" if scenario == "success" else "",
                )
                if scenario in {"no-id", "untrusted"}:
                    mocked_download.assert_not_called()
                else:
                    self.assertEqual(mocked_download.call_args.kwargs["timeout"], 60)

    def test_cli_find_failure_fallback_and_validate_outputs_never_use_network(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "bundle"
            root.mkdir()
            bundle(root)
            output = Path(temporary) / "github-output"
            env = {
                "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_OUTPUT": str(output),
                "VERIFICATION_FINGERPRINT": FINGERPRINT,
            }
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(sys, "argv", ["reuse", "find", SHA]),
                mock.patch.object(reuse, "find_reusable") as find,
            ):
                self.assertEqual(reuse.main(), 0)
                find.assert_not_called()
            self.assertIn("reuse_run_id=\n", output.read_text())
            for error in (
                None,
                OSError("synthetic"),
                ValueError("synthetic"),
                TypeError("synthetic"),
                subprocess.TimeoutExpired("fixture", 60),
            ):
                output.write_text("")
                with (
                    mock.patch.dict(os.environ, {**env, "ALLOW_REUSE": "true"}, clear=True),
                    mock.patch.object(sys, "argv", ["reuse", "find", SHA]),
                    mock.patch.object(reuse, "find_reusable", return_value="7", side_effect=error),
                ):
                    self.assertEqual(reuse.main(), 0)
                self.assertIn(
                    "reuse_run_id=" + ("7" if error is None else "") + "\n", output.read_text()
                )
            for reused in ("", "7"):
                output.write_text("")
                with (
                    mock.patch.dict(os.environ, {**env, "REUSE_RUN_ID": reused}, clear=True),
                    mock.patch.object(sys, "argv", ["reuse", "validate", SHA, "--root", str(root)]),
                ):
                    self.assertEqual(reuse.main(), 0)
                text = output.read_text()
                self.assertIn("backend_digest=" + IMAGES["backend"] + "\n", text)
                self.assertIn("web_image=ghcr.io/flippylolz/wef-web\n", text)
                self.assertIn("reused_verified=" + str(bool(reused)).lower() + "\n", text)
                output.unlink()
            with (
                mock.patch.dict(
                    os.environ,
                    {**env, "VERIFICATION_FINGERPRINT": "", "GITHUB_WORKFLOW_SHA": SHA},
                    clear=True,
                ),
                mock.patch.object(sys, "argv", ["reuse", "find", SHA]),
                mock.patch.object(reuse, "fingerprint", return_value=FINGERPRINT) as fingerprint,
            ):
                self.assertEqual(reuse.main(), 0)
                fingerprint.assert_called_once_with(SHA)
            for args, diagnostic in (
                (["find", "bad"], "full hexadecimal"),
                (["validate", SHA], "artifact root"),
            ):
                with (
                    mock.patch.dict(os.environ, env, clear=True),
                    mock.patch.object(sys, "argv", ["reuse", *args]),
                    mock.patch("sys.stderr", new_callable=StringIO) as err,
                    self.assertRaises(SystemExit) as caught,
                ):
                    reuse.main()
                self.assertEqual(caught.exception.code, 2)
                self.assertIn(diagnostic, err.getvalue())
        for module in ("reuse_release", "create_release_manifest"):
            completed = subprocess.run(  # noqa: S603 - fixed CLI and synthetic fixture arguments
                [sys.executable, "-m", f"scripts.deploy.{module}", "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("usage:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
