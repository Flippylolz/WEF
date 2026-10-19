"""Synthetic shared-edge configuration and redirect validation boundaries."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import shared_edge_render as render
from scripts.deploy import shared_edge_smoke as smoke
from scripts.test_shared_edge_render import fixture_configuration
from scripts.test_shared_edge_smoke import FakeCurl


class SharedEdgeRenderSmokeBoundaryTests(unittest.TestCase):
    """Recording HTTP clients never connect to a host or mutate an edge."""

    def test_redirect_rejects_hostname_prefix_and_userinfo_authorities(self) -> None:
        target = smoke.build_fixture_smoke_target()
        for location in ("https://wef.test.evil.test/", "https://wef.test@evil.test/"):
            curl = FakeCurl(
                {
                    f"http://{target.wef_hostname}:{target.http_port}/": (
                        301,
                        {"location": location},
                        "",
                    )
                }
            )
            with self.subTest(location=location), self.assertRaises(smoke.SharedEdgeSmokeError):
                smoke.smoke_http_redirect(
                    curl, target, hostname=target.wef_hostname, attempts=1, delay_seconds=0
                )

    def test_redirect_validates_scheme_authority_ports_and_bounded_retries(self) -> None:
        target = smoke.build_fixture_smoke_target()
        url = f"http://{target.wef_hostname}:{target.http_port}/"
        for location in (
            "/relative",
            "http://wef.test/",
            "//wef.test/",
            "https://user:synthetic@wef.test/",
            "https://wef.test:0/",
            "https://wef.test:bad/",
            "https://wef.test:65536/",
            "https://[invalid/",
        ):
            with (
                self.subTest(location=location),
                self.assertRaisesRegex(smoke.SharedEdgeSmokeError, "Location.*unsafe"),
            ):
                smoke.smoke_http_redirect(
                    FakeCurl({url: (301, {"location": location}, "")}),
                    target,
                    hostname=target.wef_hostname,
                    attempts=1,
                    delay_seconds=0,
                )
        for location in ("https://wef.test/", "https://WEF.TEST:8443/path?query#fragment"):
            smoke.smoke_http_redirect(
                FakeCurl({url: (301, {"location": location}, "")}),
                target,
                hostname=target.wef_hostname,
                attempts=1,
                delay_seconds=0,
            )
        curl = mock.Mock(side_effect=[(404, {}, ""), (301, {"location": "https://wef.test/"}, "")])
        with mock.patch("scripts.deploy.shared_edge_smoke.time.sleep") as sleep:
            smoke.smoke_http_redirect(
                curl, target, hostname=target.wef_hostname, attempts=2, delay_seconds=0.2
            )
        self.assertEqual(curl.call_count, 2)
        sleep.assert_called_once_with(0.2)

    def test_https_fixture_body_errors_and_pre_redirect_failures(self) -> None:
        target = smoke.build_fixture_smoke_target()
        first = f"https://{target.wef_hostname}:{target.https_port}/"
        for body, diagnostic in (("not-json", "non-JSON"), ("{}", "unexpected fixture")):
            with (
                self.subTest(body=body),
                self.assertRaisesRegex(smoke.SharedEdgeSmokeError, diagnostic),
            ):
                smoke.smoke_https_routes(FakeCurl({first: (200, {}, body)}), target)
        before_redirect = f"http://{target.wef_hostname}:{target.http_port}/"
        for status, headers in ((200, {}), (404, {"location": "https://wef.test/"})):
            with (
                self.subTest(status=status, headers=headers),
                self.assertRaisesRegex(smoke.SharedEdgeSmokeError, "404 without Location"),
            ):
                smoke.smoke_http_no_redirect(
                    FakeCurl({before_redirect: (status, headers, "")}), target
                )

    def test_complete_smoke_composition_with_optional_forecast_and_real_safe_entrypoint(
        self,
    ) -> None:
        for include_forecast in (False, True):
            target = replace(
                smoke.build_fixture_smoke_target(),
                forecast_hostname="forecast.test" if include_forecast else None,
            )
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
                f"http://{target.wef_hostname}:{target.http_port}/": (
                    301,
                    {"location": f"https://{target.wef_hostname}/"},
                    "",
                ),
            }
            if include_forecast:
                responses[f"https://forecast.test:{target.https_port}/"] = (
                    200,
                    {},
                    json.dumps({"fixture": "forecast"}),
                )
                responses[f"http://forecast.test:{target.http_port}/"] = (
                    301,
                    {"location": "https://forecast.test/"},
                    "",
                )
            curl = mock.Mock(wraps=FakeCurl(responses))
            smoke.smoke_both_https_and_redirects(curl, target)
            self.assertEqual(curl.call_count, 6 if include_forecast else 4)
            curl = mock.Mock(return_value=(200, {}, "unstructured production content"))
            smoke.smoke_https_routes(curl, target, expect_fixture_bodies=False)
            self.assertEqual(curl.call_count, 4 if include_forecast else 3)
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            self.assertEqual(smoke.main(), 0)
            self.assertIn("import the smoke helpers", out.getvalue())
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.deploy.shared_edge_smoke"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_render_acme_boundaries_properties_and_non_parented_output(self) -> None:
        for configuration, diagnostic in (
            (fixture_configuration(email="invalid"), "not a valid address"),
            (
                fixture_configuration(acme_server=render.PRODUCTION_ACME_SERVER),
                "local proof ACME server",
            ),
            (
                fixture_configuration(fixture_mode=False, acme_server=render.FIXTURE_ACME_SERVER),
                "production releases must not",
            ),
        ):
            with (
                self.subTest(diagnostic=diagnostic),
                self.assertRaisesRegex(render.SharedEdgeRenderError, diagnostic),
            ):
                render.validate_configuration(configuration)
        production = fixture_configuration(fixture_mode=False, email="fixture@example.invalid")
        render.validate_configuration(production)
        self.assertEqual(production.resolved_acme_server, render.PRODUCTION_ACME_SERVER)
        self.assertTrue(production.includes_forecast)
        self.assertFalse(
            fixture_configuration(forecast_hostname=None, forecast_upstream=None).includes_forecast
        )
        issuance = render.render_issuance_commands(production)
        self.assertIn("--email fixture@example.invalid", issuance)
        self.assertIn(render.PRODUCTION_ACME_SERVER, issuance)
        with self.assertRaises(render.SharedEdgeRenderError):
            render.validate_release_dir(Path("relative-release"))

    def test_forecast_blocks_normalize_real_template_boundaries_and_optional_upstreams(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / render.FORECAST_VHOST_TEMPLATE
            for content in ("server {}", "\nserver {}", "server {}\n", "\nserver {}\n"):
                template.write_text(content, encoding="utf-8")
                result = render.tls_replacements(fixture_configuration(), templates_dir=root)
                self.assertEqual(result["FORECAST_SERVER_BLOCK"], "\nserver {}\n")
            config = fixture_configuration(
                forecast_http_upstream="forecast-gateway:3000",
                fillable_upstream="fillable-gateway:8080",
            )
            files = render.write_release(config, root / "optional-release")
            tls = (root / "optional-release/tls.conf").read_text(encoding="utf-8")
            self.assertEqual(len(files), 5)
            self.assertIn("forecast-gateway:3000", tls)
            self.assertIn("fillable-gateway:8080", tls)
            self.assertIn("max-age=0", tls)

    def test_render_cli_reports_safe_success_refusal_and_real_synthetic_write(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = [
                "--wef-hostname",
                "wef.test",
                "--wef-api-upstream",
                "api:8080",
                "--wef-media-upstream",
                "media:8080",
                "--wef-web-upstream",
                "web:8080",
                "--fixture-mode",
                "--acme-server",
                render.FIXTURE_ACME_SERVER,
            ]
            with mock.patch("sys.stdout", new_callable=StringIO) as out:
                self.assertEqual(render.main([*args, "--output-dir", str(root / "first")]), 0)
                self.assertIn("wrote 5 files", out.getvalue())
            bad = list(args)
            bad[1] = "INVALID"
            with mock.patch("sys.stderr", new_callable=StringIO) as err:
                self.assertEqual(render.main([*bad, "--output-dir", str(root / "bad")]), 1)
                self.assertIn("shared_edge_render:", err.getvalue())
            completed = subprocess.run(  # noqa: S603 - fixed renderer and synthetic output tree
                [
                    sys.executable,
                    "-m",
                    "scripts.deploy.shared_edge_render",
                    *args,
                    "--output-dir",
                    str(root / "child"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((root / "child/tls.conf").is_file())
