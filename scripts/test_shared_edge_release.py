"""Tests for atomic shared-edge release activation state."""

# ruff: noqa: D102, PT009, PT027, S101

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.shared_edge_release import (
    EdgeState,
    SharedEdgeReleaseError,
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

    def test_switches_between_bootstrap_and_tls(self) -> None:
        set_active_config(self.release, "bootstrap")
        self.assertEqual(read_active_config(self.release), "bootstrap")
        set_active_config(self.release, "tls")
        self.assertEqual(read_active_config(self.release), "tls")

    def test_rejects_unknown_configuration_names(self) -> None:
        with self.assertRaises(SharedEdgeReleaseError):
            set_active_config(self.release, "../escape")

    def test_rejects_pointer_escaping_the_release(self) -> None:
        (self.release / "active.conf").symlink_to("../deploy-hook.sh")
        with self.assertRaises(SharedEdgeReleaseError):
            read_active_config(self.release)


if __name__ == "__main__":
    unittest.main()
