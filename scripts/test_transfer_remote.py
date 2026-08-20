"""Tests for historical transfer remote planning and server dry-run."""

# ruff: noqa: D102, PT009

from __future__ import annotations

import json
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.transfer.bundle import pack_bundle
from scripts.transfer.remote_paths import remote_bundle_paths
from scripts.transfer.rsync_transfer import (
    RsyncTarget,
    build_remote_prepare_command,
    build_rsync_command,
)
from scripts.transfer.server_dry_run import evaluate_server_dry_run
from scripts.transfer.transfer_plan import build_transfer_plan
from scripts.transfer_remote import main as transfer_remote_main

BUNDLE_CHECKSUM = "a" * 64


def write_fixture_source(root: Path) -> None:
    """Create one minimal bundle source tree for tests."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "database.sql").write_text("-- synthetic dump\n", encoding="utf-8")
    (root / "table_counts.json").write_text(
        json.dumps({"locations": 1, "offers": 2}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_fixture_inventory(path: Path, *, disk_free: int, memory_kb: int) -> None:
    """Write one minimal server inventory fixture."""
    payload = {
        "schema": "wef-server-inventory@1",
        "resources": {
            "disk_free_bytes": disk_free,
            "memory_available_kb": memory_kb,
        },
        "wef_paths": [
            {"path": "/home/nuc/wef/imports"},
            {"path": "/home/nuc/wef/imports/incoming"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class TransferRemoteTests(unittest.TestCase):
    """Verify transfer plan, rsync command, and server dry-run flows."""

    def test_remote_paths_are_checksum_scoped(self) -> None:
        root = Path("/home/nuc/wef")
        paths = remote_bundle_paths(root, BUNDLE_CHECKSUM)
        self.assertEqual(
            paths.incoming_dir,
            root / "imports" / "incoming" / BUNDLE_CHECKSUM,
        )
        self.assertNotIn("System/Volumes", paths.incoming_dir.as_posix())

    def test_build_transfer_plan_from_verified_bundle(self) -> None:
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
            plan = build_transfer_plan(bundle_dir=bundle, wef_root=Path("/home/nuc/wef"))
            self.assertEqual(plan.bundle_checksum, BUNDLE_CHECKSUM)
            self.assertGreater(plan.total_bytes, 0)
            self.assertTrue(str(plan.remote_incoming_dir).endswith(BUNDLE_CHECKSUM))

    def test_rsync_command_uses_partial_and_progress(self) -> None:
        with TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "bundle"
            bundle.mkdir()
            (bundle / "manifest.json").write_text("{}", encoding="utf-8")
            command = build_rsync_command(
                local_bundle_dir=bundle,
                remote_incoming_dir=Path("/home/nuc/wef/imports/incoming/" + BUNDLE_CHECKSUM),
                target=RsyncTarget(user="nuc", host="example.test"),
            )
            self.assertEqual(command[0], "rsync")
            self.assertIn("--partial", command)
            self.assertIn("--progress", command)

    def test_remote_prepare_command_creates_incoming_directory(self) -> None:
        command = build_remote_prepare_command(
            remote_incoming_dir=Path("/home/nuc/wef/imports/incoming/" + BUNDLE_CHECKSUM),
            target=RsyncTarget(user="nuc", host="example.test"),
        )
        self.assertEqual(command[0], "ssh")
        self.assertIn("mkdir -p", command[-1])
        self.assertIn(BUNDLE_CHECKSUM, command[-1])

    def test_server_dry_run_allows_sufficient_capacity(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            inventory = base / "inventory.json"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            plan = build_transfer_plan(bundle_dir=bundle, wef_root=Path("/home/nuc/wef"))
            write_fixture_inventory(
                inventory,
                disk_free=plan.total_bytes * 2,
                memory_kb=2_097_152,
            )
            summary = evaluate_server_dry_run(
                plan=plan,
                inventory=json.loads(inventory.read_text(encoding="utf-8")),
                candidate_database="wef_hist_candidate",
            )
            self.assertTrue(summary.allowed)

    def test_server_dry_run_refuses_insufficient_disk(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            inventory = base / "inventory.json"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            plan = build_transfer_plan(bundle_dir=bundle, wef_root=Path("/home/nuc/wef"))
            write_fixture_inventory(inventory, disk_free=1, memory_kb=2_097_152)
            summary = evaluate_server_dry_run(
                plan=plan,
                inventory=json.loads(inventory.read_text(encoding="utf-8")),
                candidate_database="wef_hist_candidate",
            )
            self.assertFalse(summary.allowed)
            self.assertIn("insufficient remote disk headroom", summary.refusal_reasons[0])

    def test_cli_server_dry_run_exit_code(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            bundle = base / "bundle"
            inventory = base / "inventory.json"
            write_fixture_source(source)
            pack_bundle(
                source_root=source,
                output_dir=bundle,
                source_checksum=BUNDLE_CHECKSUM,
                release_sha="b" * 64,
            )
            plan = build_transfer_plan(bundle_dir=bundle, wef_root=Path("/home/nuc/wef"))
            write_fixture_inventory(
                inventory,
                disk_free=plan.total_bytes * 2,
                memory_kb=2_097_152,
            )
            buffer = StringIO()
            with unittest.mock.patch("sys.stdout", buffer):
                status = transfer_remote_main(
                    [
                        "server-dry-run",
                        str(bundle),
                        str(inventory),
                        "--candidate-database",
                        "wef_hist_candidate",
                    ],
                )
            self.assertEqual(status, 0)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["allowed"])


if __name__ == "__main__":
    unittest.main()
