"""Tests for shared-edge cutover preflight gates."""

# ruff: noqa: D102, PT009, PT027, S101

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.shared_edge_preflight import (
    SharedEdgePreflightError,
    validate_cutover_compose_text,
    validate_edge_root,
    validate_forecast_listener_present,
    validate_listener_plan,
)


class ListenerPlanTests(unittest.TestCase):
    def test_accepts_free_edge_ports(self) -> None:
        validate_listener_plan({3100, 3000}, edge_http_port=80, edge_https_port=443)

    def test_rejects_occupied_http_port(self) -> None:
        with self.assertRaises(SharedEdgePreflightError):
            validate_listener_plan({80}, edge_http_port=80, edge_https_port=443)


class EdgeRootTests(unittest.TestCase):
    def test_requires_complete_edge_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(SharedEdgePreflightError):
                validate_edge_root(root)
            for name in ("releases", "letsencrypt", "webroot", "state", "hooks"):
                (root / name).mkdir()
            (root / "letsencrypt").chmod(0o700)
            validate_edge_root(root)


class ForecastListenerTests(unittest.TestCase):
    def test_requires_port_3000(self) -> None:
        validate_forecast_listener_present({3000, 3100})

    def test_rejects_missing_port_3000(self) -> None:
        with self.assertRaises(SharedEdgePreflightError):
            validate_forecast_listener_present({3100})


class CutoverComposePolicyTests(unittest.TestCase):
    def test_accepts_minimal_overlay(self) -> None:
        text = Path("infra/compose.production-cutover.yaml").read_text(encoding="utf-8")
        validate_cutover_compose_text(text)

    def test_rejects_missing_edge_network(self) -> None:
        with self.assertRaises(SharedEdgePreflightError):
            validate_cutover_compose_text("services: {}\n")


if __name__ == "__main__":
    unittest.main()
