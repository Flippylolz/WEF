"""Unit tests for production runtime directory preparation after activation."""

# ruff: noqa: D101, D102, PT009, S603, S607

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deploy" / "production-common.sh"


class PrepareRuntimeDirectoriesTests(unittest.TestCase):
    def _run(self, root: Path) -> subprocess.CompletedProcess[str]:
        command = f"""
set -eu
WEF_ROOT='{root}'
. '{SCRIPT}'
prepare_runtime_directories
"""
        return subprocess.run(
            ["sh", "-c", command],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_creates_plain_media_trees(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._run(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "media" / "public").is_dir())
            self.assertTrue((root / "media" / "originals").is_dir())
            self.assertFalse((root / "media" / "public").is_symlink())

    def test_allows_candidate_media_symlinks(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            checksum = "a" * 64
            public_target = root / "candidates" / checksum / "media" / "public"
            originals_target = root / "candidates" / checksum / "media" / "originals"
            public_target.mkdir(parents=True)
            originals_target.mkdir(parents=True)
            media = root / "media"
            media.mkdir()
            (media / "public").symlink_to(public_target)
            (media / "originals").symlink_to(originals_target)
            result = self._run(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((media / "public").is_symlink())
            self.assertTrue((media / "reports").is_dir())

    def test_rejects_media_symlink_outside_candidates(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            outside = Path(directory) / "outside-public"
            outside.mkdir()
            media = root / "media"
            media.mkdir()
            (media / "public").symlink_to(outside)
            (media / "originals").mkdir()
            result = self._run(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("media symlink must resolve under candidates", result.stderr)


if __name__ == "__main__":
    unittest.main()
