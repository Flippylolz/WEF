"""Integration tests for historical transfer bundle packaging."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import contextlib
import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.transfer.bundle import (
    BUNDLE_MANIFEST_NAME,
    BundleExistsError,
    BundleRefusalError,
    dry_run_source,
    pack_bundle,
    verify_bundle,
)
from scripts.transfer.terminal_state import TerminalState
from scripts.transfer_bundle import main as transfer_bundle_main


def write_fixture_source(root: Path) -> None:
    """Create one minimal bundle source tree for tests."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "database.sql").write_text("-- synthetic dump\n", encoding="utf-8")
    (root / "table_counts.json").write_text(
        json.dumps({"locations": 1, "offers": 2}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    original = root / "media" / "originals" / "ab"
    public = root / "media" / "public" / "ab"
    original.mkdir(parents=True)
    public.mkdir(parents=True)
    (original / "photo.jpg").write_bytes(b"original")
    (public / "thumb.jpg").write_bytes(b"derivative")


class TransferBundleTests(unittest.TestCase):
    """Verify dry-run, pack, verify, and CLI flows."""

    def test_dry_run_reports_counts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            write_fixture_source(source)
            _, summary = dry_run_source(source)
            self.assertEqual(summary.table_row_counts, {"locations": 1, "offers": 2})
            self.assertEqual(summary.media_object_count, 2)
            self.assertEqual(summary.media_bytes, 18)
            self.assertEqual(summary.expected_bundle_bytes, 36)

    def test_pack_and_verify_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            write_fixture_source(source)

            result = pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum="a" * 64,
                release_sha="b" * 64,
            )
            self.assertTrue(result.manifest_path.is_file())
            verify_bundle(bundle)
            manifest = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
            self.assertEqual(manifest["table_row_counts"]["locations"], 1)
            self.assertEqual(manifest["media_summary"]["restricted_original_count"], 1)

    def test_pack_refuses_active_terminal_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            write_fixture_source(source)
            with self.assertRaises(BundleRefusalError):
                pack_bundle(
                    source_root=source,
                    output_dir=base / "bundle",
                    source_checksum="a" * 64,
                    release_sha="b" * 64,
                    terminal_state=TerminalState(
                        active_import_lease=True,
                        open_geocode_claims=0,
                        pending_provider_work=0,
                        reconciliation_complete=True,
                    ),
                )

    def test_pack_is_non_overwriting(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum="a" * 64,
                release_sha="b" * 64,
            )
            with self.assertRaises(BundleExistsError):
                pack_bundle(
                    source_root=source,
                    output_dir=bundle,
                    source_checksum="a" * 64,
                    release_sha="b" * 64,
                )

    def test_cli_dry_run_and_verify(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum="a" * 64,
                release_sha="b" * 64,
            )

            dry_run_buffer = StringIO()
            with contextlib.redirect_stdout(dry_run_buffer):
                self.assertEqual(transfer_bundle_main(["dry-run", str(source)]), 0)
            payload = json.loads(dry_run_buffer.getvalue())
            self.assertEqual(payload["media_object_count"], 2)

            self.assertEqual(transfer_bundle_main(["verify", str(bundle)]), 0)


if __name__ == "__main__":
    unittest.main()
