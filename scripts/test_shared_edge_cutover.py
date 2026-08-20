"""Tests for staged shared-edge cutover orchestration."""

# ruff: noqa: D101, D102, D107, PLR0911, PT009, PT027

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.deploy.shared_edge_cutover import (
    CutoverContext,
    CutoverStage,
    SharedEdgeCutoverError,
    run_cutover_stages,
)
from scripts.deploy.shared_edge_release import EdgeState, SharedEdgeReleaseError
from scripts.deploy.shared_edge_smoke import build_fixture_smoke_target

EDGE_ROOT = Path("fixture-edge-root")


class RecordingCurl:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.redirect_enabled = False
        self.calls: list[str] = []

    def enable_redirect(self) -> None:
        self.redirect_enabled = True

    def __call__(
        self,
        url: str,
        *,
        resolve: str | None = None,
        cacert: Path | None = None,
        method: str | None = None,
    ) -> tuple[int, dict[str, str], str]:
        del resolve, cacert, method
        self.calls.append(url)
        if self.fail_on is not None and self.fail_on in url:
            return 500, {}, "{}"
        if url.startswith("https://") and "/api/" in url:
            return 200, {}, json.dumps({"fixture": "wef-api"})
        if url.startswith("https://") and "/media/" in url:
            return 200, {}, json.dumps({"fixture": "wef-media"})
        if url.startswith("https://forecast."):
            return 200, {}, json.dumps({"fixture": "forecast"})
        if url.startswith("https://"):
            return 200, {}, json.dumps({"fixture": "wef-web"})
        if url.startswith("http://"):
            if self.redirect_enabled:
                host = url.removeprefix("http://").split(":", maxsplit=1)[0]
                return 301, {"location": f"https://{host}/"}, ""
            return 404, {}, ""
        return 200, {}, "{}"


class FakeActivator:
    def __init__(self, curl: RecordingCurl | None = None) -> None:
        self.configs: list[str] = []
        self.rollback_count = 0
        self.fail_on: str | None = None
        self.curl = curl

    def activate(self, config: str) -> EdgeState:
        if self.fail_on == config:
            message = f"refusing {config}"
            raise SharedEdgeReleaseError(message)
        self.configs.append(config)
        if config == "tls-redirect" and self.curl is not None:
            self.curl.enable_redirect()
        return EdgeState("r-001", config, "r-000")

    def rollback(self) -> EdgeState:
        self.rollback_count += 1
        return EdgeState("r-000", "bootstrap", "r-001")


class CutoverOrchestratorTests(unittest.TestCase):
    def test_stops_before_redirect_when_requested(self) -> None:
        curl = RecordingCurl()
        activator = FakeActivator(curl)
        result = run_cutover_stages(
            CutoverContext(
                edge_root=EDGE_ROOT,
                release_name="r-001",
                smoke_target=build_fixture_smoke_target(),
                curl=curl,
                skip_redirect=True,
                activate_fn=activator.activate,
                rollback_fn=activator.rollback,
            )
        )
        self.assertEqual(activator.configs, ["tls"])
        self.assertEqual(
            result.completed_stages,
            [CutoverStage.TLS, CutoverStage.HTTPS_SMOKE],
        )
        self.assertEqual(result.state["active_config"], "tls")

    def test_runs_redirect_stage_after_https_smokes(self) -> None:
        curl = RecordingCurl()
        activator = FakeActivator(curl)
        result = run_cutover_stages(
            CutoverContext(
                edge_root=EDGE_ROOT,
                release_name="r-001",
                smoke_target=build_fixture_smoke_target(),
                curl=curl,
                activate_fn=activator.activate,
                rollback_fn=activator.rollback,
            )
        )
        self.assertEqual(activator.configs, ["tls", "tls-redirect"])
        self.assertEqual(
            result.completed_stages,
            [
                CutoverStage.TLS,
                CutoverStage.HTTPS_SMOKE,
                CutoverStage.REDIRECT,
                CutoverStage.REDIRECT_SMOKE,
            ],
        )
        self.assertEqual(result.state["active_config"], "tls-redirect")

    def test_rolls_back_when_https_smoke_fails(self) -> None:
        curl = RecordingCurl(fail_on="/api/")
        activator = FakeActivator(curl)
        with self.assertRaises(SharedEdgeCutoverError):
            run_cutover_stages(
                CutoverContext(
                    edge_root=EDGE_ROOT,
                    release_name="r-001",
                    smoke_target=build_fixture_smoke_target(),
                    curl=curl,
                    skip_redirect=True,
                    activate_fn=activator.activate,
                    rollback_fn=activator.rollback,
                )
            )
        self.assertEqual(activator.configs, ["tls"])
        self.assertEqual(activator.rollback_count, 1)

    def test_rolls_back_when_redirect_activation_fails(self) -> None:
        curl = RecordingCurl()
        activator = FakeActivator(curl)
        activator.fail_on = "tls-redirect"
        with self.assertRaises(SharedEdgeCutoverError):
            run_cutover_stages(
                CutoverContext(
                    edge_root=EDGE_ROOT,
                    release_name="r-001",
                    smoke_target=build_fixture_smoke_target(),
                    curl=curl,
                    activate_fn=activator.activate,
                    rollback_fn=activator.rollback,
                )
            )
        self.assertEqual(activator.configs, ["tls"])
        self.assertEqual(activator.rollback_count, 1)


if __name__ == "__main__":
    unittest.main()
