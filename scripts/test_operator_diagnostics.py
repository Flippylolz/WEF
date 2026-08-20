"""Unit tests for operator diagnostics helpers."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.operator_diagnostics import (
    OperatorDiagnosticsError,
    collect_diagnostics,
    redact_mapping,
)


class RedactionTests(unittest.TestCase):
    def test_redacts_sensitive_keys(self) -> None:
        payload = redact_mapping(
            {
                "release_sha": "abc",
                "database_url": "postgresql://wef:secret@db/wef",
                "nested": {"password": "x", "ok": 1},
                "source_text_excerpt": "private",
            },
        )
        self.assertEqual(payload["release_sha"], "abc")
        self.assertEqual(payload["database_url"], "***")
        self.assertEqual(payload["nested"]["password"], "***")
        self.assertEqual(payload["nested"]["ok"], 1)
        self.assertEqual(payload["source_text_excerpt"], "***")


class CollectDiagnosticsTests(unittest.TestCase):
    def test_collects_release_failure_and_disk(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            (root / "media" / "public").mkdir(parents=True)
            (root / "postgres").mkdir()
            (root / "state" / "current.json").write_text(
                json.dumps(
                    {
                        "release_sha": "a" * 40,
                        "public_port": 3100,
                        "release_dir": f"{root}/releases/{'a' * 40}",
                        "config_file": f"{root}/secrets/production.env",
                    },
                ),
                encoding="utf-8",
            )
            (root / "state" / "last-failure.json").write_text(
                json.dumps(
                    {
                        "candidate_release_sha": "b" * 40,
                        "failure_reason": "health_verification",
                        "recorded_at": "2026-08-20T09:28:56Z",
                        "restored_release_sha": None,
                    },
                ),
                encoding="utf-8",
            )
            payload = collect_diagnostics(root, db_container=None)
            self.assertEqual(payload["release"]["release_sha"], "a" * 40)
            self.assertEqual(payload["last_failure"]["failure_reason"], "health_verification")
            self.assertNotIn("database_url", payload["last_failure"])
            self.assertGreaterEqual(len(payload["disk"]), 1)
            self.assertIsNone(payload["last_successful_import"])

    def test_missing_root_fails(self) -> None:
        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-root"
            with self.assertRaises(OperatorDiagnosticsError):
                collect_diagnostics(missing)


if __name__ == "__main__":
    unittest.main()
