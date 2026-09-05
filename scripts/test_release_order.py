"""Prove stale-candidate, duplicate, artifact, and interrupted-release failure boundaries."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import fcntl
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.deploy.release_order import decide, guard, mark_pending, snapshot
from scripts.deploy.reuse_release import (
    REQUIRED_FILES,
    REQUIRED_JOBS,
    find_reusable,
    trusted_run,
    validate_bundle,
)

SHA = "a" * 40
OLD = "b" * 40
FINGERPRINT = "f" * 64
IMAGES = {"backend": "sha256:" + "c" * 64, "web": "sha256:" + "d" * 64}


def bundle(root: Path) -> None:
    """Create a minimal sanitized release artifact with a complete checksum inventory."""
    manifest = {
        "schema": "wef-release@1",
        "source_sha": SHA,
        "verification_fingerprint": FINGERPRINT,
        "images": IMAGES,
    }
    path = root / "release-manifest.json"
    path.write_text(json.dumps(manifest))
    for relative in REQUIRED_FILES - {"release-manifest.json"}:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture")
    (root / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}\n"
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )


class ReleaseOrderTests(unittest.TestCase):
    def test_snapshot_cannot_enter_while_remote_activation_holds_lock(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            with (root / "state/deploy.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                script = Path(__file__).parent / "deploy/release_order.py"
                result = subprocess.run(  # noqa: S603 - fixed local proof command
                    [sys.executable, str(script), "snapshot", str(root)],
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_ancestry_not_time_determines_order(self) -> None:
        for relationships, expected in (([True], "superseded"), ([False, True], "activate")):
            with patch("scripts.deploy.release_order.ancestor", side_effect=relationships):
                self.assertEqual(decide({"release_sha": OLD}, {"source_sha": SHA}), expected)
        with (
            patch("scripts.deploy.release_order.ancestor", return_value=False),
            self.assertRaises(ValueError),
        ):
            decide({"release_sha": OLD}, {"source_sha": SHA})

    def test_same_sha_requires_matching_digests(self) -> None:
        current = {"release_sha": SHA, "images": IMAGES}
        self.assertEqual(decide(current, {"source_sha": SHA, "images": IMAGES}), "same")
        with self.assertRaises(ValueError):
            decide(current, {"source_sha": SHA, "images": {}})
        self.assertEqual(decide({"release_sha": None}, {"source_sha": SHA}), "activate")

    def test_interrupted_mutation_is_not_retried_blindly(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            guard(root, "none")
            mark_pending(root, SHA)
            self.assertEqual((root / "state/activation-pending.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                guard(root, "none")
            with self.assertRaises(FileExistsError):
                mark_pending(root, SHA)

    def test_changed_or_inconsistent_state_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            release = root / "releases" / SHA
            release.mkdir(parents=True)
            bundle(release)
            secret = root / "secrets/releases" / SHA
            secret.mkdir(parents=True)
            (root / "secrets/current").symlink_to(secret, target_is_directory=True)
            (root / "state/current.json").write_text(
                json.dumps(
                    {
                        "release_sha": SHA,
                        "release_dir": str(release),
                        "config_file": str(secret / "production.env"),
                    }
                )
            )
            with self.assertRaises(ValueError):
                snapshot(root)
            (root / "releases/current").symlink_to(release, target_is_directory=True)
            self.assertEqual(snapshot(root), {"release_sha": SHA, "images": IMAGES})
            with self.assertRaises(ValueError):
                guard(root, OLD)
            guard(root, SHA)

    def test_artifact_source_digest_definition_and_inventory_are_required(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bundle(root)
            self.assertEqual(validate_bundle(root, SHA, FINGERPRINT)["images"], IMAGES)
            for sha, fp in ((OLD, FINGERPRINT), (SHA, "0" * 64)):
                with self.assertRaises(ValueError):
                    validate_bundle(root, sha, fp)
            extra = root / "extra.sh"
            extra.write_text("unexpected")
            with self.assertRaises(ValueError):
                validate_bundle(root, SHA, FINGERPRINT)
            extra.unlink()
            (root / "release-manifest.json").write_text("{}")
            with self.assertRaises(ValueError):
                validate_bundle(root, SHA, FINGERPRINT)

    def test_missing_or_expired_artifacts_fall_back_without_downloading(self) -> None:
        for artifacts in ([], [{"name": f"release-{SHA}", "expired": True}]):
            with (
                patch("scripts.deploy.reuse_release.shutil.which", return_value="/usr/bin/gh"),
                patch(
                    "scripts.deploy.reuse_release.read_api",
                    side_effect=[
                        {"workflow_runs": [{"id": 1}]},
                        {"jobs": []},
                        {"artifacts": artifacts},
                    ],
                ),
                patch("scripts.deploy.reuse_release.trusted_run", return_value=True),
                patch("scripts.deploy.reuse_release.subprocess.run") as download,
            ):
                self.assertEqual(find_reusable("Flippylolz/WEF", SHA, FINGERPRINT), "")
                download.assert_not_called()

    def test_foreign_manual_failed_and_missing_job_evidence_cannot_be_reused(self) -> None:
        repo = "Flippylolz/WEF"
        run = {
            "event": "push",
            "conclusion": "success",
            "status": "completed",
            "head_sha": SHA,
            "head_branch": "main",
            "repository": {"full_name": repo},
            "head_repository": {"full_name": repo},
            "path": ".github/workflows/deploy-production.yml",
        }
        jobs = [
            {"name": "Verify / " + name, "status": "completed", "conclusion": "success"}
            for name in REQUIRED_JOBS
        ]
        self.assertTrue(trusted_run(run, jobs, SHA, repo))
        self.assertFalse(trusted_run(run, jobs[:-1], SHA, repo))
        for field, value in (
            ("event", "workflow_dispatch"),
            ("conclusion", "cancelled"),
            ("head_sha", OLD),
            ("head_repository", {"full_name": "foreign/repo"}),
        ):
            self.assertFalse(trusted_run({**run, field: value}, jobs, SHA, repo))
        self.assertFalse(
            trusted_run(
                run,
                [*jobs, {"name": "other", "status": "completed", "conclusion": "failure"}],
                SHA,
                repo,
            )
        )


if __name__ == "__main__":
    unittest.main()
