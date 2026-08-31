"""Unit tests for passive Telegram event monitoring."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import json
import unittest

from scripts.deploy.check_telegram_passive_events import (
    EXIT_ERROR,
    EXIT_EVENT_DETECTED,
    EXIT_OK,
    PassiveEventCheckError,
    evaluate_snapshot,
    snapshot_from_status,
)


def _status(*, received: str | None = None, connected: bool = True) -> dict[str, object]:
    return {
        "max_persisted_external_id": 29434,
        "reconciliation": {"status": "aligned"},
        "runtime_health": {
            "release_sha": "b71c99fd5985",
            "transport_connected": connected,
            "consumer_running": True,
            "last_event_received_at": received,
            "last_event_committed_at": None,
            "remote_head_external_id": 29434,
        },
    }


class SnapshotTests(unittest.TestCase):
    def test_no_passive_event(self) -> None:
        snapshot = snapshot_from_status(_status(received=None))
        self.assertFalse(snapshot.passive_event_observed)
        self.assertEqual(evaluate_snapshot(snapshot), EXIT_OK)

    def test_passive_event_detected(self) -> None:
        snapshot = snapshot_from_status(_status(received="2026-08-31T18:00:00Z"))
        self.assertTrue(snapshot.passive_event_observed)
        self.assertEqual(evaluate_snapshot(snapshot), EXIT_EVENT_DETECTED)

    def test_unhealthy_worker_is_error(self) -> None:
        snapshot = snapshot_from_status(_status(received=None, connected=False))
        self.assertEqual(evaluate_snapshot(snapshot), EXIT_ERROR)

    def test_missing_runtime_health(self) -> None:
        with self.assertRaises(PassiveEventCheckError):
            snapshot_from_status({"max_persisted_external_id": 1})


class FixtureRoundTripTests(unittest.TestCase):
    def test_fixture_json_parses(self) -> None:
        payload = json.dumps(_status(received="2026-08-31T18:00:00Z"))
        snapshot = snapshot_from_status(json.loads(payload))
        self.assertEqual(snapshot.max_persisted_external_id, 29434)


if __name__ == "__main__":
    unittest.main()
