"""Tests for shared-edge route smoke helpers."""

# ruff: noqa: D101, D102, D103, D107, PT027

from __future__ import annotations

import json
import unittest
from typing import TYPE_CHECKING

from scripts.deploy.shared_edge_smoke import (
    SharedEdgeSmokeError,
    SmokeTarget,
    build_fixture_smoke_target,
    smoke_http_no_redirect,
    smoke_http_redirect,
    smoke_https_routes,
)

if TYPE_CHECKING:
    from pathlib import Path


def fixture_target() -> SmokeTarget:
    return build_fixture_smoke_target()


class FakeCurl:
    def __init__(self, responses: dict[str, tuple[int, dict[str, str], str]]) -> None:
        self.responses = responses

    def __call__(
        self,
        url: str,
        *,
        resolve: str | None = None,
        cacert: Path | None = None,
        method: str | None = None,
    ) -> tuple[int, dict[str, str], str]:
        del resolve, cacert, method
        if url not in self.responses:
            message = f"unexpected curl url: {url}"
            raise AssertionError(message)
        return self.responses[url]


class HttpsSmokeTests(unittest.TestCase):
    def test_accepts_fixture_routes(self) -> None:
        target = fixture_target()
        responses = {
            f"https://{target.wef_hostname}:{target.https_port}/": (
                200,
                {},
                json.dumps({"fixture": "wef-web"}),
            ),
            f"https://{target.wef_hostname}:{target.https_port}/api/v1/health/ready": (
                200,
                {},
                json.dumps({"fixture": "wef-api"}),
            ),
            f"https://{target.wef_hostname}:{target.https_port}/media/derivatives/x.webp": (
                200,
                {},
                json.dumps({"fixture": "wef-media"}),
            ),
            f"https://{target.forecast_hostname}:{target.https_port}/": (
                200,
                {},
                json.dumps({"fixture": "forecast"}),
            ),
        }
        smoke_https_routes(FakeCurl(responses), target)

    def test_rejects_failed_status(self) -> None:
        target = fixture_target()
        responses = {
            f"https://{target.wef_hostname}:{target.https_port}/": (500, {}, "{}"),
            f"https://{target.wef_hostname}:{target.https_port}/api/v1/health/ready": (
                200,
                {},
                json.dumps({"fixture": "wef-api"}),
            ),
            f"https://{target.wef_hostname}:{target.https_port}/media/derivatives/x.webp": (
                200,
                {},
                json.dumps({"fixture": "wef-media"}),
            ),
            f"https://{target.forecast_hostname}:{target.https_port}/": (
                200,
                {},
                json.dumps({"fixture": "forecast"}),
            ),
        }
        with self.assertRaises(SharedEdgeSmokeError):
            smoke_https_routes(FakeCurl(responses), target)


class RedirectSmokeTests(unittest.TestCase):
    def test_accepts_301_location(self) -> None:
        target = fixture_target()
        curl = FakeCurl(
            {
                f"http://{target.wef_hostname}:{target.http_port}/": (
                    301,
                    {"location": f"https://{target.wef_hostname}/"},
                    "",
                )
            }
        )
        smoke_http_redirect(curl, target, hostname=target.wef_hostname)

    def test_rejects_missing_redirect(self) -> None:
        target = fixture_target()
        curl = FakeCurl(
            {
                f"http://{target.wef_hostname}:{target.http_port}/": (404, {}, ""),
            }
        )
        with self.assertRaises(SharedEdgeSmokeError):
            smoke_http_redirect(curl, target, hostname=target.wef_hostname)

    def test_no_redirect_accepts_404(self) -> None:
        target = fixture_target()
        curl = FakeCurl(
            {
                f"http://{target.wef_hostname}:{target.http_port}/": (404, {}, ""),
            }
        )
        smoke_http_no_redirect(curl, target)


if __name__ == "__main__":
    unittest.main()
