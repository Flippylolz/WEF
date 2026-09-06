"""Fail-closed privacy checks for selected browser failure artifacts."""

from __future__ import annotations

# ruff: noqa: PT009 - stdlib unittest runner
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.run_full_stack_e2e import safe_artifacts


class BrowserArtifactSafetyTests(unittest.TestCase):
    """Synthetic fixtures exercise artifact rejection before publication."""

    def test_scans_zip_contents_and_does_not_publish_private_trace(self) -> None:
        """A secret inside a compressed trace is not hidden from the scanner."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            results.mkdir()
            with zipfile.ZipFile(results / "trace.zip", "w") as archive:
                archive.writestr("trace.network", "wef_session=synthetic-private-token")
            with self.assertRaises(ValueError):  # noqa: PT027 - stdlib runner
                safe_artifacts(results, root / "safe", ("wef_session",))
            self.assertFalse((root / "safe" / "trace.zip").exists())

    def test_scans_screenshots_and_skips_raw_text_diagnostics(self) -> None:
        """Only an explicitly allowed clean image/trace is selected."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            results.mkdir()
            (results / "masked.png").write_bytes(b"synthetic-masked-image")
            (results / "private.log").write_text("private-token")
            self.assertEqual(safe_artifacts(results, root / "safe", ("private-token",)), 1)
            self.assertFalse((root / "safe" / "private.log").exists())
            (results / "masked.png").write_bytes(b"private-token")
            with self.assertRaises(ValueError):  # noqa: PT027 - stdlib runner
                safe_artifacts(results, root / "rejected", ("private-token",))
