"""Tests for non-public historical candidate reconciliation."""

# ruff: noqa: D102, PT009

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.transfer.bundle import pack_bundle
from scripts.transfer.constants import INCLUDED_TABLES
from scripts.transfer.reconcile import MediaCounts, reconcile_candidate
from scripts.transfer_candidate import main as transfer_candidate_main

BUNDLE_CHECKSUM = "a" * 64


def write_fixture_source(root: Path) -> None:
    """Create one minimal bundle source tree for tests."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "database.sql").write_text("-- synthetic dump\n", encoding="utf-8")
    (root / "table_counts.json").write_text(
        json.dumps({"locations": 1, "offers": 2}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    originals = root / "media" / "originals"
    public = root / "media" / "public"
    originals.mkdir(parents=True)
    public.mkdir(parents=True)
    (originals / "a.bin").write_bytes(b"orig")
    (public / "b.bin").write_bytes(b"pub")


def matching_table_counts(**overrides: int) -> dict[str, int]:
    """Return one complete included-table count map for fixture reconciliation."""
    counts = dict.fromkeys(INCLUDED_TABLES, 0)
    counts.update(overrides)
    return counts


class CandidateReconcileTests(unittest.TestCase):
    """Verify candidate reconciliation gates."""

    def test_reconcile_allows_matching_counts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            summary = reconcile_candidate(
                manifest=manifest,
                table_row_counts=matching_table_counts(locations=1, offers=2),
                media_counts=MediaCounts(
                    restricted_original_count=1,
                    public_derivative_count=1,
                ),
                production_source_messages=0,
            )
            self.assertTrue(summary.allowed)
            self.assertEqual(summary.refusal_reasons, ())

    def test_reconcile_refuses_table_and_public_drift(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            summary = reconcile_candidate(
                manifest=manifest,
                table_row_counts=matching_table_counts(locations=9, offers=2),
                media_counts=MediaCounts(
                    restricted_original_count=1,
                    public_derivative_count=1,
                ),
                production_source_messages=5,
            )
            self.assertFalse(summary.allowed)
            self.assertIn(
                "candidate table counts do not match bundle manifest",
                summary.refusal_reasons,
            )
            self.assertIn(
                "public production still exposes historical source messages",
                summary.refusal_reasons,
            )

    def test_cli_reconcile_against_candidate_media_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            wef_root = base / "wef"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            media_root = wef_root / "candidates" / BUNDLE_CHECKSUM / "media"
            (media_root / "originals").mkdir(parents=True)
            (media_root / "public").mkdir(parents=True)
            (media_root / "originals" / "a.bin").write_bytes(b"orig")
            (media_root / "public" / "b.bin").write_bytes(b"pub")
            counts = base / "counts.json"
            counts.write_text(
                json.dumps(matching_table_counts(locations=1, offers=2), sort_keys=True) + "\n",
                encoding="utf-8",
            )
            status = transfer_candidate_main(
                [
                    "reconcile",
                    str(bundle),
                    "--table-counts",
                    str(counts),
                    "--wef-root",
                    str(wef_root),
                    "--production-source-messages",
                    "0",
                ],
            )
            self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
