"""Default cutover bindings, rollback failures and safe CLI planning."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import shared_edge_cutover as cutover
from scripts.deploy.shared_edge_release import EdgeState, SharedEdgeReleaseError
from scripts.deploy.shared_edge_smoke import build_fixture_smoke_target
from scripts.test_shared_edge_cutover import FakeActivator, RecordingCurl


class SharedEdgeCutoverBoundaryTests(unittest.TestCase):
    """Recording clients and replaced host commands never contact an edge instance."""

    def test_failure_before_activation_never_attempts_rollback(self) -> None:
        curl = RecordingCurl()
        activator = FakeActivator(curl)
        activator.fail_on = "tls"
        with self.assertRaisesRegex(cutover.SharedEdgeCutoverError, "before any activation"):
            cutover.run_cutover_stages(
                cutover.CutoverContext(
                    edge_root=Path("fixture-edge"),
                    release_name="candidate",
                    curl=curl,
                    smoke_target=build_fixture_smoke_target(),
                    activate_fn=activator.activate,
                    rollback_fn=activator.rollback,
                )
            )
        self.assertEqual(activator.rollback_count, 0)
        self.assertEqual(curl.calls, [])

    def test_default_bindings_forward_network_callback_and_restore_after_failed_smoke(self) -> None:
        for reload_callback in (None, mock.Mock()):
            curl = RecordingCurl(fail_on="/api/")
            root = Path("fixture-edge")
            with (
                self.subTest(reload_callback=reload_callback),
                mock.patch.object(
                    cutover,
                    "activate_release",
                    return_value=EdgeState("candidate", "tls", "baseline"),
                ) as activate,
                mock.patch.object(
                    cutover,
                    "rollback_release",
                    return_value=EdgeState("baseline", "bootstrap", "candidate"),
                ) as rollback,
                self.assertRaisesRegex(
                    cutover.SharedEdgeCutoverError,
                    "after tls.*rolled back",
                ),
            ):
                cutover.run_cutover_stages(
                    cutover.CutoverContext(
                        edge_root=root,
                        release_name="candidate",
                        curl=curl,
                        smoke_target=build_fixture_smoke_target(),
                        upstream_network="fixture-network",
                        reload_callback=reload_callback,
                    )
                )
            activate.assert_called_once_with(
                root,
                "candidate",
                "tls",
                upstream_network="fixture-network",
                reload_callback=reload_callback,
            )
            rollback.assert_called_once_with(root, upstream_network="fixture-network")
            if reload_callback is not None:
                reload_callback.assert_called_once_with()

    def test_rollback_failure_retains_its_cause_and_never_reports_restoration(self) -> None:
        curl = RecordingCurl(fail_on="/api/")
        activator = FakeActivator(curl)
        rollback = mock.Mock(side_effect=SharedEdgeReleaseError("synthetic rollback refusal"))
        with self.assertRaisesRegex(
            cutover.SharedEdgeCutoverError, "rollback also failed"
        ) as error:
            cutover.run_cutover_stages(
                cutover.CutoverContext(
                    edge_root=Path("fixture-edge"),
                    release_name="candidate",
                    curl=curl,
                    smoke_target=build_fixture_smoke_target(),
                    activate_fn=activator.activate,
                    rollback_fn=rollback,
                )
            )
        self.assertIsInstance(error.exception.__cause__, SharedEdgeReleaseError)
        rollback.assert_called_once_with()

    def test_cli_plans_each_stage_order_and_refuses_unbound_live_execution(self) -> None:
        with TemporaryDirectory() as temporary:
            args = ["--edge-root", temporary, "--release", "candidate"]
            for skip in (False, True):
                with (
                    self.subTest(skip=skip),
                    mock.patch("sys.stdout", new_callable=StringIO) as out,
                ):
                    self.assertEqual(
                        cutover.main([*args, "--dry-plan", *(["--skip-redirect"] if skip else [])]),
                        0,
                    )
                    self.assertEqual("-> redirect -> redirect-smoke" in out.getvalue(), not skip)
                    self.assertIn("tls -> https-smoke", out.getvalue())
            with mock.patch("sys.stderr", new_callable=StringIO) as err:
                self.assertEqual(cutover.main(args), 2)
                self.assertIn("requires a proof/operator curl binder", err.getvalue())
            completed = subprocess.run(  # noqa: S603 - fixed module and synthetic plan arguments
                [sys.executable, "-m", "scripts.deploy.shared_edge_cutover", *args, "--dry-plan"],
                cwd=Path(cutover.__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("-> redirect -> redirect-smoke", completed.stdout)
