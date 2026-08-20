"""Unit tests for historical transfer foundation helpers."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import unittest

from scripts.transfer.batch_order import insert_order
from scripts.transfer.checkpoints import advance_checkpoint, next_batch_index
from scripts.transfer.conflicts import ConflictClass, classify_row, summarize_conflicts
from scripts.transfer.constants import EXCLUDED_TABLES, INCLUDED_TABLES
from scripts.transfer.dry_run import build_dry_run_summary, forbidden_bundle_path
from scripts.transfer.manifest import (
    BundleComponent,
    MediaSummary,
    create_manifest,
    render_manifest,
    validate_manifest,
)
from scripts.transfer.paths import PathValidationError, validate_media_relative_path
from scripts.transfer.terminal_state import TerminalState, packaging_refusal_reasons


class TransferFoundationTests(unittest.TestCase):
    """Verify manifest, refusal, conflict, path, and ordering helpers."""

    def test_manifest_is_deterministic_and_validates(self) -> None:
        media = MediaSummary(
            restricted_original_count=1,
            restricted_original_bytes=10,
            public_derivative_count=2,
            public_derivative_bytes=20,
        )
        components = (
            BundleComponent("database.sql", "a" * 64, 100),
            BundleComponent("media.tar", "b" * 64, 200),
        )
        manifest = create_manifest(
            source_checksum="c" * 64,
            release_sha="d" * 64,
            table_row_counts={"offers": 2, "locations": 1},
            media=media,
            components=components,
        )
        rendered_once = render_manifest(manifest)
        rendered_twice = render_manifest(
            create_manifest(
                source_checksum="c" * 64,
                release_sha="d" * 64,
                table_row_counts={"locations": 1, "offers": 2},
                media=media,
                components=components,
            )
        )
        self.assertEqual(rendered_once, rendered_twice)
        validate_manifest(json.loads(rendered_once))

    def test_manifest_rejects_invalid_source_checksum(self) -> None:
        with self.assertRaises(ValueError):
            create_manifest(
                source_checksum="not-a-checksum",
                release_sha="d" * 64,
                table_row_counts={},
                media=MediaSummary(0, 0, 0, 0),
                components=(),
            )

    def test_terminal_state_refusal_reasons_are_sorted(self) -> None:
        reasons = packaging_refusal_reasons(
            TerminalState(
                active_import_lease=True,
                open_geocode_claims=1,
                pending_provider_work=0,
                reconciliation_complete=False,
            ),
        )
        self.assertEqual(
            reasons,
            (
                "active_import_lease",
                "open_geocode_claims",
                "reconciliation_incomplete",
            ),
        )

    def test_conflict_summary_blocks_on_conflicts(self) -> None:
        summary = summarize_conflicts(
            [
                ConflictClass.IDENTICAL,
                ConflictClass.NEW,
                ConflictClass.CONFLICTING,
            ],
        )
        self.assertTrue(summary.blocks_restore)
        self.assertEqual(summary.new, 1)

    def test_classify_row_outcomes(self) -> None:
        existing = {("offers", "1"): {"price": 1}}
        self.assertEqual(
            classify_row(key=("offers", "1"), existing=existing, incoming={"price": 1}),
            ConflictClass.IDENTICAL,
        )
        self.assertEqual(
            classify_row(key=("offers", "2"), existing=existing, incoming={"price": 2}),
            ConflictClass.NEW,
        )
        self.assertEqual(
            classify_row(key=("offers", "1"), existing=existing, incoming={"price": 2}),
            ConflictClass.CONFLICTING,
        )

    def test_media_path_validation_rejects_traversal(self) -> None:
        with self.assertRaises(PathValidationError):
            validate_media_relative_path("../escape")
        self.assertEqual(
            validate_media_relative_path("originals/ab/cd.jpg"),
            "originals/ab/cd.jpg",
        )

    def test_insert_order_covers_all_included_tables(self) -> None:
        ordered = insert_order()
        self.assertEqual(set(ordered), set(INCLUDED_TABLES))
        self.assertEqual(len(ordered), len(INCLUDED_TABLES))

    def test_excluded_tables_are_not_in_bundle_scope(self) -> None:
        self.assertEqual(set(EXCLUDED_TABLES) & set(INCLUDED_TABLES), set())

    def test_dry_run_summary_estimates_headroom(self) -> None:
        summary = build_dry_run_summary(
            table_row_counts={"offers": 10},
            media_object_count=3,
            media_bytes=300,
            database_dump_bytes=700,
        )
        self.assertEqual(summary.expected_bundle_bytes, 1000)
        self.assertEqual(summary.minimum_headroom_bytes, 1250)

    def test_forbidden_bundle_path_fragments(self) -> None:
        self.assertTrue(forbidden_bundle_path("imports/raw-export/part.sql"))
        self.assertFalse(forbidden_bundle_path("bundle/database.sql"))

    def test_checkpoint_resume_advances_batches(self) -> None:
        self.assertEqual(next_batch_index(None), 0)
        checkpoint = advance_checkpoint(
            None,
            table="offers",
            batch_size=100,
            rows_remaining=250,
        )
        self.assertIsNotNone(checkpoint)
        self.assertEqual(next_batch_index(checkpoint), 1)


if __name__ == "__main__":
    unittest.main()
