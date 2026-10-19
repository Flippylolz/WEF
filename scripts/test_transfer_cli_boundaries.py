"""Operator CLI admission and subprocess entry points use only synthetic bundles."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import transfer_bundle, transfer_candidate, transfer_remote
from scripts.deploy.candidate_config import candidate_paths
from scripts.transfer.bundle import pack_bundle
from scripts.transfer.constants import INCLUDED_TABLES


class TransferCliBoundaryTests(unittest.TestCase):
    """Exercise parser, filesystem and process composition without SSH or database writes."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "database.sql").write_text("-- synthetic fixture\n", encoding="utf-8")
        (self.source / "table_counts.json").write_text('{"locations":1}', encoding="utf-8")
        self.bundle = self.root / "bundle"
        pack_bundle(
            source_root=self.source,
            output_dir=self.bundle,
            source_checksum="a" * 64,
            release_sha="b" * 64,
        )

    def test_bundle_cli_creates_bundle_and_emits_non_sensitive_summary(self) -> None:
        output = self.root / "packed"
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(
                transfer_bundle.main(
                    [
                        "pack",
                        str(self.source),
                        str(output),
                        "--source-checksum",
                        "a" * 64,
                        "--release-sha",
                        "b" * 64,
                    ]
                ),
                0,
            )
            payload = json.loads(out.getvalue())
        self.assertEqual(payload["bundle_dir"], str(output))
        self.assertEqual(payload["manifest"], str(output / "manifest.json"))
        self.assertGreater(payload["expected_bundle_bytes"], 0)

    def test_remote_plan_and_rsync_command_options(self) -> None:
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(transfer_remote.main(["plan", str(self.bundle)]), 0)
            payload = json.loads(out.getvalue())
        self.assertEqual(payload["bundle_checksum"], "a" * 64)
        self.assertEqual([entry["name"] for entry in payload["components"]], ["database.sql"])
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(
                transfer_remote.main(
                    [
                        "rsync-plan",
                        str(self.bundle),
                        "--remote-host",
                        "example.test",
                        "--ssh-port",
                        "2222",
                        "--identity-file",
                        str(self.root / "key"),
                        "--known-hosts-file",
                        str(self.root / "hosts"),
                        "--dry-run",
                    ]
                ),
                0,
            )
            commands = out.getvalue().splitlines()
        self.assertEqual(len(commands), 2)
        self.assertTrue(commands[0].startswith("ssh "))
        self.assertIn("StrictHostKeyChecking=yes", commands[0])
        self.assertIn("rsync --dry-run", commands[1])
        self.assertIn("2222", commands[1])

    def test_remote_dry_run_returns_failure_and_collision_evidence(self) -> None:
        path = self.root / "inventory.json"
        path.write_text(
            json.dumps({"schema": "wef-server-inventory@1", "resources": {}}), encoding="utf-8"
        )
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(
                transfer_remote.main(
                    [
                        "server-dry-run",
                        str(self.bundle),
                        str(path),
                        "--candidate-database",
                        "fixture",
                        "--existing-databases",
                        "other, fixture, ,last",
                        "--incoming-exists",
                    ]
                ),
                1,
            )
            payload = json.loads(out.getvalue())
        self.assertFalse(payload["allowed"])
        self.assertIn("candidate database name is already in use", payload["refusal_reasons"])
        self.assertIn("incoming bundle path already exists on server", payload["refusal_reasons"])

    def test_candidate_preflight_normalizes_keys_and_reports_refusal(self) -> None:
        path = self.root / "snapshots.json"
        path.write_text(
            json.dumps({"locations": {"incoming": {"1": {}, "uuid": {}}}}), encoding="utf-8"
        )
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(
                transfer_candidate.main(["restore-preflight", str(path), "--batch-size", "1"]), 0
            )
            payload = json.loads(out.getvalue())
        self.assertEqual(payload["total_new_rows"], 2)
        self.assertEqual([batch["key_count"] for batch in payload["batches"]], [1, 1])
        path.write_text(
            json.dumps(
                {"locations": {"existing": {"1": {"v": "old"}}, "incoming": {"1": {"v": "new"}}}}
            ),
            encoding="utf-8",
        )
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(transfer_candidate.main(["restore-preflight", str(path)]), 1)
            self.assertFalse(json.loads(out.getvalue())["allowed"])
            self.assertIn("conflicting rows", out.getvalue())

    def test_candidate_preflight_refuses_malformed_snapshot_documents(self) -> None:
        path = self.root / "snapshots.json"
        payload: object
        for payload in ([], {"locations": []}, {"locations": {"incoming": []}}):
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(TypeError):
                transfer_candidate.main(["restore-preflight", str(path)])
        with (
            mock.patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            transfer_candidate.main(["unknown-command"])
        self.assertEqual(error.exception.code, 2)

    def test_candidate_reconcile_refuses_nonobject_counts_and_exposes_media_drift(self) -> None:
        counts = self.root / "counts.json"
        args = [
            "reconcile",
            str(self.bundle),
            "--table-counts",
            str(counts),
            "--wef-root",
            str(self.root),
            "--production-source-messages",
            "0",
        ]
        counts.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(TypeError, "table counts must be a JSON object"):
            transfer_candidate.main(args)
        paths = candidate_paths(self.root, "a" * 64)
        paths.restricted_originals.mkdir(parents=True)
        paths.public_derivatives.mkdir(parents=True)
        (paths.public_derivatives / "extra.bin").write_bytes(b"synthetic")
        counts.write_text(json.dumps(dict.fromkeys(INCLUDED_TABLES, 0)), encoding="utf-8")
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(transfer_candidate.main(args), 1)
            payload = json.loads(out.getvalue())
        self.assertEqual(payload["media_counts"]["public_derivative_count"], 1)
        self.assertEqual(payload["media_mismatches"], ["public_derivatives:1!=0"])

    def test_real_module_entrypoints(self) -> None:
        snapshots = self.root / "snapshots.json"
        snapshots.write_text("{}", encoding="utf-8")
        commands = (
            ("scripts.transfer_bundle", ["verify", str(self.bundle)]),
            ("scripts.transfer_remote", ["plan", str(self.bundle)]),
            ("scripts.transfer_candidate", ["restore-preflight", str(snapshots)]),
            ("scripts.transfer_restore", ["staging-teardown-sql"]),
        )
        for module, arguments in commands:
            with self.subTest(module=module):
                result = subprocess.run(  # noqa: S603 - fixed modules and the current Python executable
                    [sys.executable, "-m", module, *arguments],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=Path(transfer_bundle.__file__).resolve().parents[1],
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout)
