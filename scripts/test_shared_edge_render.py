"""Tests for deterministic shared-edge release rendering."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.shared_edge_render import (
    BOOTSTRAP_CONFIG,
    HOOK_FILENAME,
    ISSUANCE_FILENAME,
    TLS_CONFIG,
    EdgeConfiguration,
    SharedEdgeRenderError,
    render_template,
    validate_configuration,
    write_release,
)


def fixture_configuration(**overrides: object) -> EdgeConfiguration:
    """Return a complete fixture-mode edge configuration."""
    values: dict[str, object] = {
        "wef_hostname": "wef.test",
        "forecast_hostname": "forecast.test",
        "wef_api_upstream": "fixture-wef-api:8080",
        "wef_media_upstream": "fixture-wef-media:8080",
        "wef_web_upstream": "fixture-wef-web:8080",
        "forecast_upstream": "fixture-forecast:8080",
        "client_max_body_size": "1m",
        "fixture_mode": True,
    }
    values.update(overrides)
    return EdgeConfiguration(**values)  # type: ignore[arg-type]


class RenderTemplateTests(unittest.TestCase):
    """Verify strict placeholder substitution."""

    def test_substitutes_every_placeholder(self) -> None:
        rendered = render_template("a {{NAME}} b {{PORT}}", {"NAME": "wef", "PORT": "443"})
        self.assertEqual(rendered, "a wef b 443")

    def test_rejects_leftover_placeholders(self) -> None:
        with self.assertRaises(SharedEdgeRenderError):
            render_template("a {{NAME}} b {{MISSING}}", {"NAME": "wef"})


class ValidateConfigurationTests(unittest.TestCase):
    """Verify unsafe configurations are rejected before rendering."""

    def test_accepts_fixture_configuration(self) -> None:
        validate_configuration(fixture_configuration())

    def test_rejects_duplicate_hostnames(self) -> None:
        configuration = fixture_configuration(
            wef_hostname="wef.test",
            forecast_hostname="wef.test",
        )
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_rejects_non_fixture_hostnames_in_fixture_mode(self) -> None:
        configuration = fixture_configuration(wef_hostname="wef.example.com")
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_accepts_production_hostnames_outside_fixture_mode(self) -> None:
        configuration = fixture_configuration(
            wef_hostname="wef.example.com",
            forecast_hostname="forecast.example.com",
            fixture_mode=False,
        )
        validate_configuration(configuration)

    def test_rejects_uppercase_hostnames(self) -> None:
        configuration = fixture_configuration(wef_hostname="WEF.test")
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_rejects_upstreams_without_ports(self) -> None:
        configuration = fixture_configuration(wef_api_upstream="fixture-wef-api")
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_rejects_upstream_traversal_characters(self) -> None:
        configuration = fixture_configuration(
            forecast_upstream="../escape:8080",
        )
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_rejects_unbounded_body_sizes(self) -> None:
        configuration = fixture_configuration(client_max_body_size="999999999m")
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)

    def test_rejects_real_email_in_fixture_mode(self) -> None:
        configuration = fixture_configuration(email="owner@example.test")
        with self.assertRaises(SharedEdgeRenderError):
            validate_configuration(configuration)


class WriteReleaseTests(unittest.TestCase):
    """Verify deterministic release directory production."""

    def test_writes_complete_deterministic_release(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "r-001"
            second = root / "r-002"
            written_first = write_release(fixture_configuration(), first)
            write_release(fixture_configuration(), second)
            self.assertEqual(
                sorted(path.name for path in written_first),
                sorted([BOOTSTRAP_CONFIG, TLS_CONFIG, ISSUANCE_FILENAME, HOOK_FILENAME]),
            )
            for name in (
                BOOTSTRAP_CONFIG,
                TLS_CONFIG,
                ISSUANCE_FILENAME,
                HOOK_FILENAME,
            ):
                self.assertEqual(
                    (first / name).read_bytes(),
                    (second / name).read_bytes(),
                    f"{name} must render deterministically",
                )
            hook = first / HOOK_FILENAME
            self.assertEqual(hook.stat().st_mode & 0o777, 0o755, "hook must be world-executable")

    def test_rejects_non_empty_release_directories(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "occupied"
            target.mkdir()
            (target / "stowaway.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(SharedEdgeRenderError):
                write_release(fixture_configuration(), target)

    def test_rejects_path_traversal_output(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "escape" / ".." / "r-001"
            with self.assertRaises(SharedEdgeRenderError):
                write_release(fixture_configuration(), target)

    def test_rejects_invalid_release_directory_names(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "R001_Invalid"
            with self.assertRaises(SharedEdgeRenderError):
                write_release(fixture_configuration(), target)

    def test_renders_fixture_acme_server_in_fixture_mode(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "r-001"
            write_release(fixture_configuration(), target)
            issuance = (target / ISSUANCE_FILENAME).read_text(encoding="utf-8")
            self.assertIn("https://pebble:14000/dir", issuance)
            self.assertNotIn("letsencrypt.org", issuance)


if __name__ == "__main__":
    unittest.main()
