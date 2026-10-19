"""Synthetic bundle corruption and transfer admission regression cases."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import runpy
import tarfile
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.transfer import bundle, constants, manifest, reconcile, source_layout, transfer_plan
from scripts.transfer.batch_order import insert_order
from scripts.transfer.checkpoints import BatchCheckpoint, advance_checkpoint
from scripts.transfer.paths import PathValidationError, validate_media_relative_path
from scripts.transfer.remote_paths import RemotePathError, remote_bundle_paths
from scripts.transfer.restore import RestorePreflightError, build_restore_plan
from scripts.transfer.rsync_transfer import (
    RsyncOptions,
    RsyncTarget,
    RsyncTransferError,
    build_remote_prepare_command,
    build_rsync_command,
)
from scripts.transfer.server_dry_run import (
    ServerDryRunError,
    evaluate_server_dry_run,
    load_server_inventory,
)
from scripts.transfer.terminal_state import TerminalState, packaging_refusal_reasons


class TransferFileBoundaryTests(unittest.TestCase):
    """Check actual temporary files without importing historical source material."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "database.sql").write_text("-- synthetic fixture\n", encoding="utf-8")
        self.counts = self.source / "table_counts.json"
        self.counts.write_text('{"locations":1}', encoding="utf-8")
        self.output = self.root / "bundle"

    def pack(self) -> Path:
        """Build one immutable synthetic bundle for mutation tests."""
        bundle.pack_bundle(
            source_root=self.source,
            output_dir=self.output,
            source_checksum="a" * 64,
            release_sha="b" * 64,
        )
        return self.output

    def test_manifest_validation_and_release_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "release SHA"):
            manifest.create_manifest(
                source_checksum="a" * 64,
                release_sha="wrong",
                table_row_counts={},
                media=manifest.MediaSummary(0, 0, 0, 0),
                components=(),
            )
        for payload, message in (
            ({}, "schema mismatch"),
            ({"schema": constants.BUNDLE_SCHEMA}, "checksum is invalid"),
            (
                {
                    "schema": constants.BUNDLE_SCHEMA,
                    "source_checksum": "a" * 64,
                    "credentials": "synthetic",
                },
                "forbidden sensitive keys",
            ),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                manifest.validate_manifest(payload)

    def test_source_refuses_missing_roots_and_metadata(self) -> None:
        with self.assertRaisesRegex(source_layout.BundleSourceError, "root must be a directory"):
            source_layout.inspect_source(self.root / "absent")
        self.counts.unlink()
        with self.assertRaisesRegex(source_layout.BundleSourceError, "missing table_counts.json"):
            source_layout.inspect_source(self.source)
        self.counts.write_text("{}", encoding="utf-8")
        (self.source / "database.sql").unlink()
        with self.assertRaisesRegex(source_layout.BundleSourceError, "missing database.sql"):
            source_layout.inspect_source(self.source)

    def test_source_counts_reject_invalid_or_excluded_tables(self) -> None:
        payload: object
        for payload in (
            [],
            {constants.EXCLUDED_TABLES[0]: 0},
            {"unknown": 0},
            {"locations": -1},
            {"locations": "1"},
        ):
            self.counts.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(source_layout.BundleSourceError):
                source_layout.load_table_counts(self.counts)

    def test_media_tree_refuses_broken_symlinks_and_unsafe_names(self) -> None:
        media = self.source / "media" / "originals"
        media.mkdir(parents=True)
        link = media / "broken"
        link.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(source_layout.BundleSourceError, "must not contain symlinks"):
            source_layout.inspect_source(self.source)
        link.unlink()
        unsafe = media / "bad\\name.bin"
        unsafe.write_bytes(b"synthetic")
        with self.assertRaisesRegex(source_layout.BundleSourceError, "unsafe media path"):
            source_layout.inspect_source(self.source)
        unsafe.unlink()
        (media / "telegram-session.dat").write_bytes(b"synthetic")
        with self.assertRaisesRegex(source_layout.BundleSourceError, "forbidden media path"):
            source_layout.inspect_source(self.source)

    def test_empty_tar_and_nested_media(self) -> None:
        empty = self.root / "empty.tar"
        bundle._write_tar(self.root / "absent", empty)  # noqa: SLF001 - media root can vanish after preflight
        with tarfile.open(empty) as archive:
            self.assertEqual(archive.getnames(), [])
        media = self.source / "media" / "originals" / "nested"
        media.mkdir(parents=True)
        (media / "fixture.bin").write_bytes(b"synthetic")
        self.pack()
        with tarfile.open(self.output / bundle.RESTRICTED_TAR) as archive:
            self.assertEqual(archive.getnames(), ["nested/fixture.bin"])

    def test_bundle_verification_refuses_corruption(self) -> None:
        with self.assertRaisesRegex(bundle.BundleVerificationError, "missing manifest"):
            bundle.verify_bundle(self.output)
        self.pack()
        database = self.output / bundle.DATABASE_COMPONENT
        original = database.read_bytes()
        for content, message in (
            (None, "component is missing"),
            (b"x", "size mismatch"),
            (b"!" * len(original), "checksum mismatch"),
        ):
            if database.exists():
                database.unlink()
            if content is not None:
                database.write_bytes(content)
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(
                    bundle.BundleVerificationError,
                    message,
                ),
            ):
                bundle.verify_bundle(self.output)
        database.write_bytes(original)
        (self.output / bundle.BUNDLE_CHECKSUMS_NAME).unlink()
        with self.assertRaisesRegex(bundle.BundleVerificationError, "missing SHA256SUMS"):
            bundle.verify_bundle(self.output)

    def test_transfer_plan_rechecks_components_after_verification(self) -> None:
        self.pack()
        database = self.output / bundle.DATABASE_COMPONENT
        original = database.read_bytes()
        real_verify = bundle.verify_bundle
        for content, message in (
            (None, "missing locally"),
            (b"x", "size mismatch"),
            (b"!" * len(original), "checksum mismatch"),
        ):
            database.write_bytes(original)

            def mutate_after_verification(directory: Path, content: bytes | None = content) -> None:
                real_verify(directory)
                database.unlink()
                if content is not None:
                    database.write_bytes(content)

            with (
                self.subTest(message=message),
                mock.patch.object(
                    transfer_plan,
                    "verify_bundle",
                    side_effect=mutate_after_verification,
                ),
                self.assertRaisesRegex(transfer_plan.TransferPlanError, message),
            ):
                transfer_plan.build_transfer_plan(bundle_dir=self.output, wef_root=Path("/fixture"))

    def test_candidate_manifest_and_media_filesystem_failures(self) -> None:
        with self.assertRaisesRegex(reconcile.CandidateReconcileError, "missing manifest"):
            reconcile.load_bundle_manifest(self.output)
        self.output.mkdir()
        (self.output / bundle.BUNDLE_MANIFEST_NAME).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(reconcile.CandidateReconcileError, "must be a JSON object"):
            reconcile.load_bundle_manifest(self.output)
        media = self.root / "media"
        with self.assertRaisesRegex(reconcile.CandidateReconcileError, "must be a directory"):
            reconcile.count_media_files(media)
        nested = media / "nested"
        nested.mkdir(parents=True)
        (nested / "synthetic.bin").write_bytes(b"fixture")
        self.assertEqual(reconcile.count_media_files(media), 1)
        (nested / "link").symlink_to(nested / "synthetic.bin")
        with self.assertRaisesRegex(reconcile.CandidateReconcileError, "must not contain symlinks"):
            reconcile.count_media_files(media)

    def test_candidate_reconciliation_refuses_drift_and_malformed_aggregates(self) -> None:
        self.pack()
        payload = reconcile.load_bundle_manifest(self.output)
        changes: tuple[dict[str, object], ...] = (
            {"table_row_counts": None},
            {"media_summary": []},
            {"table_row_counts": {"locations": "1"}},
        )
        for changed in changes:
            with (
                self.subTest(changed=changed),
                self.assertRaises(reconcile.CandidateReconcileError),
            ):
                reconcile.reconcile_candidate(
                    manifest={**payload, **changed},
                    table_row_counts={},
                    media_counts=reconcile.MediaCounts(0, 0),
                    production_source_messages=0,
                )
        outcome = reconcile.reconcile_candidate(
            manifest={**payload, "migration_head": "old", "pipeline_id": "old"},
            table_row_counts={"locations": 2, constants.EXCLUDED_TABLES[0]: 1},
            media_counts=reconcile.MediaCounts(1, 1),
            production_source_messages=1,
        )
        self.assertFalse(outcome.allowed)
        self.assertIn("locations:2!=1", outcome.table_mismatches)
        self.assertIn(f"{constants.EXCLUDED_TABLES[0]}:unexpected", outcome.table_mismatches)
        self.assertTrue(any(item.endswith(":missing") for item in outcome.table_mismatches))
        self.assertEqual(
            outcome.media_mismatches, ("restricted_originals:1!=0", "public_derivatives:1!=0")
        )
        self.assertIn(
            "candidate migration head does not match released head", outcome.refusal_reasons
        )
        self.assertIn(
            "candidate pipeline id does not match released pipeline", outcome.refusal_reasons
        )
        self.assertIn(
            "candidate media counts do not match bundle manifest", outcome.refusal_reasons
        )

    def test_remote_paths_and_ssh_options(self) -> None:
        for root, checksum in ((Path("relative"), "a" * 64), (Path("/"), "wrong")):
            with self.subTest(root=root), self.assertRaises(RemotePathError):
                remote_bundle_paths(root, checksum)
        self.assertEqual(remote_bundle_paths(Path("/"), "a" * 64).root, Path("/"))
        options = RsyncOptions(Path("/fixture/id file"), Path("/fixture/known hosts"), dry_run=True)
        target = RsyncTarget("fixture", "example.test", 2222)
        incoming = Path("/fixture/imports/space dir")
        prepare = build_remote_prepare_command(
            remote_incoming_dir=incoming, target=target, options=options
        )
        self.assertEqual(prepare[-1], "mkdir -p '/fixture/imports/space dir'")
        self.assertIn("UserKnownHostsFile=/fixture/known hosts", prepare)
        self.assertIn("2222", prepare)
        command = build_rsync_command(
            local_bundle_dir=self.source,
            remote_incoming_dir=incoming,
            target=target,
            options=options,
        )
        self.assertEqual(command[1], "--dry-run")
        self.assertIn("StrictHostKeyChecking=yes", command[command.index("-e") + 1])
        self.assertIn("'/fixture/id file'", command[command.index("-e") + 1])
        with self.assertRaisesRegex(RsyncTransferError, "directory must exist"):
            build_rsync_command(
                local_bundle_dir=self.root / "missing", remote_incoming_dir=incoming, target=target
            )
        for invalid in (
            RsyncTarget("", "host"),
            RsyncTarget("user", ""),
            RsyncTarget("user", "host", 0),
            RsyncTarget("user", "host", 65536),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(RsyncTransferError):
                build_remote_prepare_command(remote_incoming_dir=incoming, target=invalid)

    def test_server_dry_run_reports_independent_capacity_and_collision_failures(self) -> None:
        self.pack()
        plan = transfer_plan.build_transfer_plan(bundle_dir=self.output, wef_root=Path("/fixture"))
        path = self.root / "inventory.json"
        value: object
        for value in ([], {}, {"schema": "old"}):
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(value=value), self.assertRaises(ServerDryRunError):
                load_server_inventory(path)
        for database, inventory in (("bad-name", {}), ("fixture", {"resources": None})):
            with self.subTest(database=database), self.assertRaises(ServerDryRunError):
                evaluate_server_dry_run(plan=plan, inventory=inventory, candidate_database=database)
        bad_plan = replace(plan, migration_head="old")
        for paths in (None, [None, {}, {"path": 1}, {"path": "/unrelated"}]):
            outcome = evaluate_server_dry_run(
                plan=bad_plan,
                inventory={"resources": {}, "wef_paths": paths},
                candidate_database="fixture",
                existing_databases=("fixture",),
                incoming_exists=True,
            )
            self.assertFalse(outcome.allowed)
            self.assertEqual(len(outcome.refusal_reasons), 6)
            self.assertIn("incoming bundle path already exists on server", outcome.refusal_reasons)
            self.assertIn("candidate database name is already in use", outcome.refusal_reasons)

    def test_order_checkpoint_and_restore_validation(self) -> None:
        with (
            mock.patch(
                "scripts.transfer.batch_order.TABLE_DEPENDENCIES", {"locations": ("locations",)}
            ),
            self.assertRaisesRegex(ValueError, "unable to resolve"),
        ):
            insert_order(("locations",))
        with self.assertRaisesRegex(ValueError, "table mismatch"):
            advance_checkpoint(
                BatchCheckpoint("offers", 1), table="locations", batch_size=1, rows_remaining=1
            )
        with self.assertRaisesRegex(ValueError, "batch size must be positive"):
            advance_checkpoint(None, table="locations", batch_size=0, rows_remaining=1)
        invalid_plans: tuple[
            tuple[int, dict[str, tuple[dict[object, object], dict[object, object]]]], ...
        ] = ((0, {}), (1, {"unknown": ({}, {})}))
        for batch_size, tables in invalid_plans:
            with self.subTest(batch_size=batch_size), self.assertRaises(RestorePreflightError):
                build_restore_plan(table_snapshots=tables, batch_size=batch_size)
        for value in ("", "/absolute", "bad\\path"):
            with self.subTest(value=value), self.assertRaises(PathValidationError):
                validate_media_relative_path(value)
        self.assertEqual(
            packaging_refusal_reasons(
                TerminalState(
                    active_import_lease=False,
                    open_geocode_claims=0,
                    pending_provider_work=1,
                    reconciliation_complete=True,
                )
            ),
            ("pending_provider_work",),
        )

    def test_new_restore_table_requires_primary_key_metadata(self) -> None:
        with (
            mock.patch.object(constants, "INCLUDED_TABLES", ("future_table",)),
            self.assertRaisesRegex(RuntimeError, "missing primary-key metadata"),
        ):
            runpy.run_path(
                str(Path(constants.__file__).with_name("table_keys.py")),
                run_name="transfer_metadata_fault",
            )
