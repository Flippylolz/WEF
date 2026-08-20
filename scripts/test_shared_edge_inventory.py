"""Tests for shared-edge inventory comparison."""

# ruff: noqa: D102, PT009, PT027, S101

from __future__ import annotations

import unittest

from scripts.deploy.shared_edge_inventory import (
    INVENTORY_SCHEMA,
    SharedEdgeInventoryError,
    compare,
    forecast_containers,
    unrelated_containers,
)


def sample_inventory(*, listener: str = "0.0.0.0:3000") -> dict[str, object]:
    return {
        "schema": INVENTORY_SCHEMA,
        "hostname": "fixture-host",
        "uid": "1000",
        "listeners": [listener],
        "compose_projects": [
            {"Name": "wef-production"},
            {"Name": "ai-forecast-production"},
        ],
        "containers": [
            {
                "name": "wef-production-api-1",
                "state": "running",
                "health": "healthy",
                "id": "a",
                "image_id": "img-a",
                "image_name": "backend",
                "ports": {},
            },
            {
                "name": "ai-forecast-production-web-1",
                "state": "running",
                "health": "healthy",
                "id": "b",
                "image_id": "img-b",
                "image_name": "forecast",
                "ports": {},
            },
        ],
        "networks": [],
        "captured_at": "2026-08-20T00:00:00+00:00",
    }


class InventoryCompareTests(unittest.TestCase):
    def test_accepts_unchanged_unrelated_state(self) -> None:
        before = sample_inventory()
        after = sample_inventory()
        compare(before, after)

    def test_rejects_listener_drift(self) -> None:
        before = sample_inventory()
        after = sample_inventory(listener="0.0.0.0:3100")
        with self.assertRaises(SharedEdgeInventoryError):
            compare(before, after)

    def test_tracks_forecast_containers_separately(self) -> None:
        inventory = sample_inventory()
        forecast = forecast_containers(inventory)
        self.assertEqual(set(forecast), {"ai-forecast-production-web-1"})
        unrelated = unrelated_containers(inventory)
        self.assertIn("ai-forecast-production-web-1", unrelated)


if __name__ == "__main__":
    unittest.main()
