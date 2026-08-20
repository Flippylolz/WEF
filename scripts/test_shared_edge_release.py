"""Tests for atomic shared-edge release activation state."""

# ruff: noqa: D102, PT009, PT027, S101

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.deploy.shared_edge_release import (
    EdgeState,
    SharedEdgeReleaseError,
    graceful_reload,
    init_edge_tree,
    read_active_config,
    read_edge_state,
    set_active_config,
    write_edge_state,
)
from scripts.deploy.shared_edge_render import write_release
from scripts.test_shared_edge_render import fixture_configuration


class EdgeStateTests(unittest.TestCase):
    """Verify activation records round-trip atomically."""

    def test_round_trips_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            init_edge_tree(root)
            self.assertIsNone(read_edge_state(root))
            state = EdgeState("r-001", "bootstrap", None)
            write_edge_state(root, state)
            restored = read_edge_state(root)
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored["current_release"], "r-001")
            self.assertEqual(restored["active_config"], "bootstrap")
            self.assertIsNone(restored["previous_release"])


class ActiveConfigTests(unittest.TestCase):
    """Verify per-release configuration pointers."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.release = self.root / "releases" / "r-001"
        write_release(fixture_configuration(), self.release)

    def test_switches_between_bootstrap_tls_and_redirect(self) -> None:
        set_active_config(self.release, "bootstrap")
        self.assertEqual(read_active_config(self.release), "bootstrap")
        set_active_config(self.release, "tls")
        self.assertEqual(read_active_config(self.release), "tls")
        set_active_config(self.release, "tls-redirect")
        self.assertEqual(read_active_config(self.release), "tls-redirect")

    def test_rejects_unknown_configuration_names(self) -> None:
        with self.assertRaises(SharedEdgeReleaseError):
            set_active_config(self.release, "../escape")

    def test_rejects_pointer_escaping_the_release(self) -> None:
        (self.release / "active.conf").symlink_to("../deploy-hook.sh")
        with self.assertRaises(SharedEdgeReleaseError):
            read_active_config(self.release)


class GracefulReloadTests(unittest.TestCase):
    """Verify reload uses container HUP rather than nginx -s reload."""

    def test_signals_hup_on_running_nginx_container(self) -> None:
        calls: list[list[str]] = []

        class Result:
            def __init__(self, stdout: str = "", returncode: int = 0) -> None:
                self.stdout = stdout
                self.stderr = ""
                self.returncode = returncode

        def fake_docker(args: list[str]) -> Result:
            calls.append(list(args))
            if args[:2] == ["ps", "--quiet"]:
                return Result(stdout="abc123\n")
            return Result()

        with patch("scripts.deploy.shared_edge_release._docker", side_effect=fake_docker):
            graceful_reload()

        self.assertEqual(calls[0][:2], ["ps", "--quiet"])
        self.assertEqual(calls[1], ["kill", "-s", "HUP", "abc123"])


if __name__ == "__main__":
    unittest.main()
