"""Structural checks for shared-edge reconnect after WEF deploys."""

# ruff: noqa: D101, D102, PT009

from __future__ import annotations

import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RECONNECT = REPOSITORY_ROOT / "scripts" / "deploy" / "reconnect-wef-upstreams.sh"
DEPLOY = REPOSITORY_ROOT / "scripts" / "deploy" / "deploy.sh"
COMMON = REPOSITORY_ROOT / "scripts" / "deploy" / "production-common.sh"
OVERLAY = REPOSITORY_ROOT / "infra" / "compose.production-shared-edge.yaml"


class DeploySharedEdgeReconnectTests(unittest.TestCase):
    def test_reconnect_script_attaches_aliases_and_reloads_nginx(self) -> None:
        text = RECONNECT.read_text(encoding="utf-8")
        self.assertIn("wef-api", text)
        self.assertIn("wef-web", text)
        self.assertIn("wef-media", text)
        self.assertIn("nginx -s reload", text)
        self.assertNotIn("docker compose", text)

    def test_deploy_requires_public_https_after_bring_up(self) -> None:
        deploy = DEPLOY.read_text(encoding="utf-8")
        common = COMMON.read_text(encoding="utf-8")
        self.assertIn("bring_up_application_services", deploy)
        self.assertIn("smoke_public_https_origin", deploy)
        self.assertLess(
            deploy.index("bring_up_application_services"), deploy.index("smoke_public_https_origin")
        )
        self.assertIn("compose.production-shared-edge.yaml", common)
        self.assertIn("reconnect_shared_edge_upstreams", common)

    def test_shared_edge_overlay_keeps_caddy(self) -> None:
        text = OVERLAY.read_text(encoding="utf-8")
        self.assertIn("wef-api", text)
        self.assertIn("wef-web", text)
        self.assertIn("wef-media", text)
        self.assertIn("media-edge", text)
        self.assertNotIn("caddy-rehearsal", text)
        self.assertNotIn("profiles:", text)


if __name__ == "__main__":
    unittest.main()
