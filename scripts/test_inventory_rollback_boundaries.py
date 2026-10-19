"""Synthetic non-interference inventories and complete rollback evidence."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from scripts.deploy import compare_server_inventory as inventory
from scripts.deploy import release_state
from scripts.deploy import verify_rollback_rehearsal as rollback

HEALTHY = "a" * 40
FAILED = "b" * 40


def inventory_fixture() -> dict[str, Any]:
    """Describe invented services and metadata without inspecting a host."""
    return {
        "schema": "wef-server-inventory@1",
        "hostname": "fixture-host",
        "uid": 1000,
        "compose_projects": [
            {"Name": "unrelated", "Status": "running"},
            {"Name": "wef-production"},
        ],
        "containers": [
            {"name": "unrelated-container", "state": "running", "health": None},
            *(
                {"name": f"wef-production-{name}-1", "state": "running", "health": "healthy"}
                for name in ("api", "db", "edge", "web")
            ),
        ],
        "listeners": ["tcp 127.0.0.1:22", "tcp 0.0.0.0:3100"],
        "existing_http": {"fixture-service": 200},
        "wef_paths": [
            {"path": path, "kind": "directory", "mode": mode, "uid": 1000}
            for path, mode in inventory.EXPECTED_WEF_PATHS.items()
        ],
    }


def rollback_evidence(root: Path) -> tuple[Path, Path]:
    """Write a complete synthetic restored release tree under one temporary root."""
    for directory in ("state", "postgres", "media", "caddy-data"):
        (root / directory).mkdir(parents=True)
    for sha in (HEALTHY, FAILED):
        release = root / "releases" / sha
        release.mkdir(parents=True)
        (release / "release-manifest.json").write_text(
            json.dumps(
                {
                    "schema": "wef-release@1",
                    "source_sha": sha,
                    "source_timestamp": "2026-10-19T00:00:00+00:00",
                    "migration_revision": "synthetic-revision",
                    "images": {"backend": "sha256:" + "c" * 64, "web": "sha256:" + "d" * 64},
                }
            ),
            encoding="utf-8",
        )
    config = root / "secrets/releases" / HEALTHY / "production.env"
    config.parent.mkdir(parents=True)
    config.write_text("SYNTHETIC_CONFIGURATION=only\n", encoding="utf-8")
    config.chmod(0o600)
    state: release_state.ReleaseState = {
        "release_sha": HEALTHY,
        "release_dir": str(root / "releases" / HEALTHY),
        "config_file": str(config),
        "public_port": 3100,
    }
    for name in ("current.json", "previous.json"):
        release_state.write_state(root / "state" / name, state)
    release_state.write_json_state(
        root / "state/last-failure.json",
        {
            "candidate_release_sha": FAILED,
            "failure_reason": "health_verification",
            "recorded_at": "2026-10-19T00:00:00+00:00",
            "restored_release_sha": HEALTHY,
        },
    )
    release_state.activate_release_links(root, root / "releases" / HEALTHY, config)
    before, after = root / "before.json", root / "after.json"
    for path in (before, after):
        path.write_text(json.dumps(inventory_fixture()), encoding="utf-8")
    return before, after


class InventoryRollbackBoundaryTests(unittest.TestCase):
    """All paths, state, metadata and CLI evidence are invented temporary fixtures."""

    def test_comparison_allows_wef_changes_but_refuses_each_unrelated_drift(self) -> None:
        before = inventory_fixture()
        after = copy.deepcopy(before)
        after["compose_projects"][1]["Status"] = "changed"
        after["containers"][1]["image"] = "changed-wef-image"
        after["listeners"].append("tcp 127.0.0.1:3100")
        inventory.compare(before, after)
        for key, value, diagnostic in (
            ("hostname", "other-host", "identity changed"),
            ("uid", 2000, "identity changed"),
            (
                "compose_projects",
                [{"Name": "unrelated", "Status": "changed"}],
                "Compose project changed",
            ),
            ("containers", [], "container changed"),
            ("listeners", ["tcp 127.0.0.1:23"], "host listener changed"),
            ("existing_http", {"fixture-service": 503}, "HTTP service changed"),
        ):
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(inventory.InventoryMismatchError, diagnostic),
            ):
                inventory.compare(before, {**before, key: value})

    def test_path_metadata_set_uid_modes_and_activated_media_ownership(self) -> None:
        for paths in ([], [*inventory_fixture()["wef_paths"], {"path": "/unexpected"}]):
            with (
                self.subTest(paths=paths),
                self.assertRaisesRegex(inventory.InventoryMismatchError, "path set"),
            ):
                inventory.validate_expected_paths({**inventory_fixture(), "wef_paths": paths})
        for field, value in (("kind", "file"), ("mode", 0o777), ("uid", 2000)):
            payload = inventory_fixture()
            payload["wef_paths"][0][field] = value
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(inventory.InventoryMismatchError, "metadata is unsafe"),
            ):
                inventory.validate_expected_paths(payload)
        payload = inventory_fixture()
        for entry in payload["wef_paths"]:
            if entry["path"] == "/home/nuc/wef/postgres":
                entry["uid"] = 999
        inventory.validate_expected_paths(payload)
        for entry in payload["wef_paths"]:
            if entry["path"] == "/home/nuc/wef/media/public":
                entry.update(kind="symlink", uid=2000)
        with self.assertRaisesRegex(inventory.InventoryMismatchError, "metadata is unsafe"):
            inventory.validate_expected_paths(payload)

    def test_inventory_schemas_and_safe_real_cli(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = root / "before.json", root / "after.json"
            before.write_text(json.dumps(inventory_fixture()), encoding="utf-8")
            for raw in ("[]", '{"schema":"invalid"}'):
                after.write_text(raw, encoding="utf-8")
                with (
                    self.subTest(raw=raw),
                    self.assertRaisesRegex(inventory.InventoryMismatchError, "invalid schema"),
                ):
                    inventory.load_inventory(after)
            after.write_text(before.read_text(), encoding="utf-8")
            with (
                mock.patch.object(sys, "argv", ["inventory", str(before), str(after)]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(inventory.main(), 0)
                self.assertIn("health are unchanged", out.getvalue())
            child = subprocess.run(  # noqa: S603 - fixed CLI and synthetic inventory files
                [
                    sys.executable,
                    "-m",
                    "scripts.deploy.compare_server_inventory",
                    str(before),
                    str(after),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)

    def test_complete_rollback_restoration_evidence_and_real_cli(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = rollback_evidence(root)
            rollback.verify(root, HEALTHY, FAILED, before, after)
            self.assertEqual(rollback.read_manifest(root, HEALTHY)["source_sha"], HEALTHY)
            args = [str(root), HEALTHY, FAILED, str(before), str(after)]
            with (
                mock.patch.object(sys, "argv", ["rollback-evidence", *args]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(rollback.main(), 0)
                self.assertIn("restoration and non-interference evidence pass", out.getvalue())
            child = subprocess.run(  # noqa: S603 - fixed verifier and synthetic restored state
                [sys.executable, "-m", "scripts.deploy.verify_rollback_rehearsal", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)

    def test_rollback_refuses_failed_runtime_missing_listener_and_corrupt_identity(self) -> None:
        value: object
        for key, value in (("compose_projects", []), ("containers", []), ("listeners", [])):
            with self.subTest(key=key), self.assertRaises(AssertionError):
                rollback.assert_runtime_inventory({**inventory_fixture(), key: value})
        for field, value in (("state", "exited"), ("health", "unhealthy")):
            payload = inventory_fixture()
            payload["containers"][1][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                rollback.assert_runtime_inventory(payload)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = rollback_evidence(root)
            path = root / "releases" / FAILED / "release-manifest.json"
            original = json.loads(path.read_text())
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(TypeError, "not an object"):
                rollback.read_manifest(root, FAILED)
            path.write_text(json.dumps({**original, "source_sha": HEALTHY}), encoding="utf-8")
            with self.assertRaises(AssertionError):
                rollback.verify(root, HEALTHY, FAILED, before, after)
