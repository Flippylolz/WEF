"""Host admission and process failures stop shared-edge cutover before mutation."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import subprocess
import sys
import unittest
from functools import partial
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import shared_edge_preflight as preflight
from scripts.deploy.shared_edge_release import SharedEdgeReleaseError


class SharedEdgePreflightBoundaryTests(unittest.TestCase):
    """Use invented listeners and process results, never the host Docker daemon."""

    def test_root_and_certificate_permissions_are_required(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "edge"
            with self.assertRaisesRegex(preflight.SharedEdgePreflightError, "root is missing"):
                preflight.validate_edge_root(root)
            root.mkdir()
            for name in preflight.REQUIRED_EDGE_SUBDIRS:
                (root / name).mkdir()
            (root / "letsencrypt").chmod(0o755)
            with self.assertRaisesRegex(preflight.SharedEdgePreflightError, "mode 0700"):
                preflight.validate_edge_root(root)
            (root / "letsencrypt").chmod(0o700)
            preflight.validate_edge_root(root)

    def test_cutover_requires_rollback_material_and_forbids_unrelated_or_destructive_commands(
        self,
    ) -> None:
        safe = "wef-edge caddy-rehearsal"
        for content, message in (
            ("wef-edge", "must keep Caddy"),
            (f"{safe} AI-Forecast", "must not reference"),
        ):
            with (
                self.subTest(content=content),
                self.assertRaisesRegex(preflight.SharedEdgePreflightError, message),
            ):
                preflight.validate_cutover_compose_text(content)
        for command in preflight.FORBIDDEN_COMMAND_FRAGMENTS:
            with (
                self.subTest(command=command),
                self.assertRaisesRegex(preflight.SharedEdgePreflightError, "forbidden command"),
            ):
                preflight.validate_cutover_compose_text(f"{safe}\n{command.upper()}")

    def test_network_inspection_uses_resolved_executable_and_requires_docker(self) -> None:
        with (
            mock.patch("scripts.deploy.shared_edge_preflight.shutil.which", return_value=None),
            self.assertRaisesRegex(preflight.SharedEdgePreflightError, "docker is required"),
        ):
            preflight.network_exists("wef-edge")
        for code in (0, 1):
            with (
                self.subTest(code=code),
                mock.patch(
                    "scripts.deploy.shared_edge_preflight.shutil.which",
                    return_value="/fixture/docker",
                ),
                mock.patch("scripts.deploy.shared_edge_preflight.subprocess.run") as run,
            ):
                run.return_value = subprocess.CompletedProcess([], code, "", "")
                self.assertEqual(preflight.network_exists("wef-edge"), code == 0)
                self.assertEqual(
                    run.call_args.args[0], ["/fixture/docker", "network", "inspect", "wef-edge"]
                )
                self.assertFalse(run.call_args.kwargs["check"])

    def test_listener_inspection_reports_missing_tool_and_process_diagnostics(self) -> None:
        with (
            mock.patch("scripts.deploy.shared_edge_preflight.shutil.which", return_value=None),
            self.assertRaisesRegex(preflight.SharedEdgePreflightError, "ss is required"),
        ):
            preflight.occupied_tcp_ports()
        for detail in (" denied\n", ""):
            with (
                self.subTest(detail=detail),
                mock.patch(
                    "scripts.deploy.shared_edge_preflight.shutil.which",
                    return_value="/fixture/ss",
                ),
                mock.patch("scripts.deploy.shared_edge_preflight.subprocess.run") as run,
            ):
                run.return_value = subprocess.CompletedProcess([], 1, "", detail)
                with self.assertRaisesRegex(
                    preflight.SharedEdgePreflightError, "denied" if detail else "failed to inspect"
                ):
                    preflight.occupied_tcp_ports()

    def test_listener_parser_handles_ipv4_ipv6_and_ignores_nonports(self) -> None:
        listeners = "\n".join(
            f"LISTEN 0 128 {local} *:*"
            for local in ("not-an-endpoint", "*:service", "127.0.0.1:3000", "[::]:443", "*:3000")
        )
        with (
            mock.patch(
                "scripts.deploy.shared_edge_preflight.shutil.which", return_value="/fixture/ss"
            ),
            mock.patch(
                "scripts.deploy.shared_edge_preflight.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, listeners, ""),
            ) as run,
        ):
            self.assertEqual(preflight.occupied_tcp_ports(), {443, 3000})
            self.assertEqual(run.call_args.args[0], ["/fixture/ss", "-H", "-ltn"])

    def test_preflight_orders_host_gates_and_translates_release_refusal(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in preflight.REQUIRED_EDGE_SUBDIRS:
                (root / name).mkdir()
            (root / "letsencrypt").chmod(0o700)
            invoke = partial(
                preflight.run_preflight,
                edge_root=root,
                release_name="synthetic",
                config="tls",
                upstream_network="wef-edge",
            )
            with (
                mock.patch.object(preflight, "network_exists", return_value=False),
                mock.patch.object(
                    preflight,
                    "occupied_tcp_ports",
                ) as ports,
                self.assertRaisesRegex(preflight.SharedEdgePreflightError, "network is missing"),
            ):
                invoke()
            ports.assert_not_called()
            for require_forecast in (True, False):
                with (
                    self.subTest(require_forecast=require_forecast),
                    mock.patch.object(
                        preflight,
                        "network_exists",
                        return_value=True,
                    ),
                    mock.patch.object(
                        preflight,
                        "occupied_tcp_ports",
                        return_value={3000} if require_forecast else set(),
                    ),
                    mock.patch.object(
                        preflight,
                        "validate_release_config",
                    ) as validate,
                    mock.patch.object(
                        preflight, "extract_upstreams", return_value=("fixture-api",)
                    ) as upstreams,
                    mock.patch.object(
                        preflight,
                        "verify_upstreams",
                    ) as verify,
                ):
                    invoke(require_forecast_listener=require_forecast)
                    validate.assert_called_once_with(
                        root, "synthetic", "tls", upstream_network="wef-edge"
                    )
                    upstreams.assert_called_once_with(root, "synthetic")
                    verify.assert_called_once_with(("fixture-api",), "wef-edge")
                    validate.side_effect = SharedEdgeReleaseError("synthetic release refusal")
                    with self.assertRaisesRegex(
                        preflight.SharedEdgePreflightError, "edge release validation failed"
                    ) as error:
                        invoke(require_forecast_listener=require_forecast)
                    self.assertIsInstance(error.exception.__cause__, SharedEdgeReleaseError)

    def test_cli_passes_listener_option_reports_errors_and_runs_real_entrypoint(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "absent"
            args = ["--edge-root", str(root), "--release-name", "synthetic"]
            with (
                mock.patch.object(preflight, "run_preflight") as run,
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(preflight.main([*args, "--skip-forecast-listener-check"]), 0)
                self.assertFalse(run.call_args.kwargs["require_forecast_listener"])
                self.assertIn("preflight passed", out.getvalue())
            with (
                mock.patch.object(
                    preflight,
                    "run_preflight",
                    side_effect=preflight.SharedEdgePreflightError("synthetic refusal"),
                ),
                mock.patch(
                    "sys.stderr",
                    new_callable=StringIO,
                ) as err,
            ):
                self.assertEqual(preflight.main(args), 1)
                self.assertIn("preflight failed: synthetic refusal", err.getvalue())
            result = subprocess.run(  # noqa: S603 - current Python, fixed module and synthetic args
                [sys.executable, "-m", "scripts.deploy.shared_edge_preflight", *args],
                cwd=Path(preflight.__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("shared-edge root is missing", result.stderr)
