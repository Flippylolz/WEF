"""Synthetic edge activation, reload and rollback boundaries."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import shared_edge_release as edge
from scripts.deploy.shared_edge_render import write_release
from scripts.test_shared_edge_render import fixture_configuration


class SharedEdgeReleaseBoundaryTests(unittest.TestCase):
    """All filesystem mutations are temporary and the Docker boundary is replaced."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        edge.init_edge_tree(self.root)
        for name in ("baseline", "candidate"):
            write_release(fixture_configuration(), self.root / "releases" / name)
        self.boundary_patch = mock.patch("scripts.deploy.shared_edge_release._docker")
        self.docker = self.boundary_patch.start()
        self.addCleanup(self.boundary_patch.stop)
        self.docker.return_value = subprocess.CompletedProcess([], 0, "", "")

    def test_same_release_redirect_preserves_the_last_distinct_rollback_target(self) -> None:
        edge.activate_release(self.root, "baseline", "bootstrap")
        first = edge.activate_release(self.root, "candidate", "tls")
        second = edge.activate_release(self.root, "candidate", "tls-redirect")
        self.assertEqual(first["previous_release"], "baseline")
        self.assertEqual(second["previous_release"], "baseline")
        restored = edge.rollback_release(self.root)
        self.assertEqual(restored["current_release"], "baseline")
        self.assertEqual(
            (self.root / "current").resolve(), (self.root / "releases/baseline").resolve()
        )

    def test_failed_same_release_reload_restores_current_config_and_keeps_rollback_target(
        self,
    ) -> None:
        edge.activate_release(self.root, "baseline", "bootstrap")
        edge.activate_release(self.root, "candidate", "tls")
        before = edge.read_edge_state(self.root)
        with self.assertRaisesRegex(RuntimeError, "synthetic reload failure"):
            edge.activate_release(
                self.root,
                "candidate",
                "tls-redirect",
                reload_callback=mock.Mock(side_effect=RuntimeError("synthetic reload failure")),
            )
        self.assertEqual(edge.read_edge_state(self.root), before)
        self.assertEqual((self.root / "current").readlink(), Path("releases/candidate"))
        self.assertEqual(edge.read_active_config(self.root / "releases/candidate"), "tls")

    def test_legacy_self_rollback_is_refused_before_validation_or_pointer_changes(self) -> None:
        edge.set_active_config(self.root / "releases/candidate", "tls")
        (self.root / "current").symlink_to("releases/candidate")
        state = edge.EdgeState("candidate", "tls", "candidate")
        edge.write_edge_state(self.root, state)
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "current release"):
            edge.rollback_release(self.root)
        self.docker.assert_not_called()
        self.assertEqual(edge.read_edge_state(self.root), state)

    def test_bad_state_shapes_names_and_release_boundaries_refuse_before_mutation(self) -> None:
        state = self.root / "state" / edge.STATE_FILENAME
        payload: object
        for payload in (
            [],
            {},
            {"current_release": "baseline", "active_config": "tls", "previous_release": 1},
        ):
            state.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(TypeError):
                edge.read_edge_state(self.root)
        state.unlink()
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "releases/escape").symlink_to(outside)
        for name, message in (
            ("../outside", "name is invalid"),
            ("missing", "does not exist"),
            ("escape", "escapes"),
        ):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(edge.SharedEdgeReleaseError, message),
            ):
                edge.activate_release(self.root, name, "bootstrap")
        self.docker.assert_not_called()

    def test_active_config_requires_a_file_and_replaces_stale_temporary_pointers(self) -> None:
        release = self.root / "releases/candidate"
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "no active.conf"):
            edge.read_active_config(release)
        (release / "bootstrap.conf").unlink()
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "file is missing"):
            edge.set_active_config(release, "bootstrap")
        temporary = release / ".active.conf.tmp"
        temporary.symlink_to("absent.conf")
        edge.set_active_config(release, "tls")
        self.assertEqual(edge.read_active_config(release), "tls")
        self.assertFalse(temporary.is_symlink())

    def test_nginx_validation_preserves_uid_readonly_mount_and_network_constraints(self) -> None:
        self.boundary_patch.stop()
        with (
            mock.patch("scripts.deploy.shared_edge_release.shutil.which", return_value=None),
            self.assertRaisesRegex(edge.SharedEdgeReleaseError, "docker is required"),
        ):
            edge.validate_release_config(self.root, "candidate", "bootstrap")
        with (
            mock.patch(
                "scripts.deploy.shared_edge_release.shutil.which", return_value="/fixture/docker"
            ),
            mock.patch(
                "scripts.deploy.shared_edge_release.subprocess.run",
            ) as run,
        ):
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            edge.validate_release_config(
                self.root, "candidate", "tls", upstream_network="fixture-network"
            )
            command = run.call_args.args[0]
            self.assertEqual(command[0], "/fixture/docker")
            self.assertEqual(command[command.index("--user") + 1], "1000:1000")
            self.assertIn(f"{self.root.resolve()}:/etc/nginx-edge:ro", command)
            self.assertIn("fixture-network", command)
            self.assertEqual(command.count("--tmpfs"), 2)
            for stdout, stderr in (("", "synthetic stderr"), ("synthetic stdout", "")):
                run.return_value = subprocess.CompletedProcess([], 1, stdout, stderr)
                with (
                    self.subTest(stderr=stderr),
                    self.assertRaisesRegex(edge.SharedEdgeReleaseError, "nginx -t rejected"),
                ):
                    edge.validate_release_config(self.root, "candidate", "bootstrap")
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "unknown edge configuration"):
            edge.validate_release_config(self.root, "candidate", "unknown")

    def test_upstream_extraction_and_tcp_probes_refuse_missing_or_unreachable_targets(self) -> None:
        release = self.root / "releases/candidate"
        (release / "tls.conf").write_text(
            'proxy_pass http://fixture-api:8000;\nset $web "fixture-web:3000";\nproxy_pass http://fixture-api:8000;',
            encoding="utf-8",
        )
        self.assertEqual(
            edge.extract_upstreams(self.root, "candidate"), ["fixture-api:8000", "fixture-web:3000"]
        )
        edge.verify_upstreams(["fixture-api:8000"], "fixture-network")
        self.assertEqual(self.docker.call_args.args[0][-4:], ["nc", "-z", "fixture-api", "8000"])
        self.docker.return_value = subprocess.CompletedProcess([], 1, "", "denied")
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "unreachable"):
            edge.verify_upstreams(["fixture-api:8000"], "fixture-network")
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "only defined for TLS"):
            edge.extract_upstreams(self.root, "candidate", config="bootstrap")
        (release / "tls.conf").unlink()
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "file is missing"):
            edge.extract_upstreams(self.root, "candidate")

    def test_missing_hook_does_not_switch_active_state(self) -> None:
        edge.activate_release(self.root, "baseline", "bootstrap")
        (self.root / "releases/candidate/deploy-hook.sh").unlink()
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "deploy hook is missing"):
            edge.activate_release(self.root, "candidate", "bootstrap")
        self.assertEqual(
            edge.read_edge_state(self.root), edge.EdgeState("baseline", "bootstrap", None)
        )
        self.assertEqual((self.root / "current").readlink(), Path("releases/baseline"))

    def test_activation_callback_failure_restores_existing_pointer_and_preserves_record(
        self,
    ) -> None:
        for previous in (False, True):
            if previous:
                edge.activate_release(self.root, "baseline", "bootstrap")
            before = edge.read_edge_state(self.root)
            with (
                self.subTest(previous=previous),
                self.assertRaisesRegex(RuntimeError, "synthetic reload failure"),
            ):
                edge.activate_release(
                    self.root,
                    "candidate",
                    "bootstrap",
                    reload_callback=mock.Mock(side_effect=RuntimeError("synthetic reload failure")),
                )
            self.assertEqual(edge.read_edge_state(self.root), before)
            if previous:
                self.assertEqual((self.root / "current").readlink(), Path("releases/baseline"))

    def test_activation_and_rollback_replace_stale_links_and_preserve_previous_configuration(
        self,
    ) -> None:
        (self.root / ".current.tmp").write_text("stale", encoding="utf-8")
        edge.activate_release(self.root, "baseline", "tls")
        (self.root / ".previous.tmp").symlink_to("absent")
        callback = mock.Mock()
        state = edge.activate_release(self.root, "candidate", "bootstrap", reload_callback=callback)
        callback.assert_called_once_with()
        self.assertEqual(state["previous_release"], "baseline")
        self.assertEqual((self.root / "previous").readlink(), Path("releases/baseline"))
        self.assertEqual((self.root / "hooks/deploy-hook.sh").stat().st_mode & 0o777, 0o755)
        restored = edge.rollback_release(self.root, upstream_network="fixture-network")
        self.assertEqual(restored["active_config"], "tls")
        self.assertEqual(restored["previous_release"], "candidate")
        self.assertIn("fixture-network", self.docker.call_args.args[0])

    def test_rollback_requires_a_previous_record_and_reload_requires_running_container(
        self,
    ) -> None:
        for state in (None, edge.EdgeState("candidate", "bootstrap", None)):
            if state is not None:
                edge.write_edge_state(self.root, state)
            with (
                self.subTest(state=state),
                self.assertRaisesRegex(edge.SharedEdgeReleaseError, "no previous release"),
            ):
                edge.rollback_release(self.root)
        with self.assertRaisesRegex(edge.SharedEdgeReleaseError, "no running edge"):
            edge.graceful_reload()
        for stdout, stderr in (("", "synthetic stderr"), ("synthetic stdout", "")):
            self.docker.side_effect = [
                subprocess.CompletedProcess([], 0, "fixture-container\n", ""),
                subprocess.CompletedProcess([], 1, stdout, stderr),
            ]
            with (
                self.subTest(stderr=stderr),
                self.assertRaisesRegex(edge.SharedEdgeReleaseError, "graceful nginx reload failed"),
            ):
                edge.graceful_reload()

    def test_cli_callbacks_errors_and_real_invalid_release_entrypoint(self) -> None:
        result = edge.EdgeState("candidate", "tls", "baseline")
        for reload in (False, True):
            options = ["--reload"] if reload else []
            with (
                self.subTest(reload=reload),
                mock.patch.object(edge, "activate_release", return_value=result) as activate,
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(
                    edge.main(
                        [
                            "activate",
                            "--edge-root",
                            str(self.root),
                            "--release",
                            "candidate",
                            "--config",
                            "tls",
                            *options,
                        ]
                    ),
                    0,
                )
                self.assertIs(
                    activate.call_args.kwargs["reload_callback"],
                    edge.graceful_reload if reload else None,
                )
                self.assertIn("current=candidate", out.getvalue())
            with (
                mock.patch.object(edge, "rollback_release", return_value=result),
                mock.patch.object(edge, "graceful_reload") as signal,
                mock.patch("sys.stdout", new_callable=StringIO),
            ):
                self.assertEqual(
                    edge.main(["rollback", "--edge-root", str(self.root), *options]), 0
                )
                self.assertEqual(signal.call_count, int(reload))
        with (
            mock.patch.object(
                edge,
                "activate_release",
                side_effect=edge.SharedEdgeReleaseError("synthetic refusal"),
            ),
            mock.patch("sys.stderr", new_callable=StringIO) as err,
        ):
            self.assertEqual(
                edge.main(
                    [
                        "activate",
                        "--edge-root",
                        str(self.root),
                        "--release",
                        "candidate",
                        "--config",
                        "tls",
                    ]
                ),
                1,
            )
            self.assertIn("synthetic refusal", err.getvalue())
        completed = subprocess.run(  # noqa: S603 - current Python, fixed module and synthetic inputs
            [
                sys.executable,
                "-m",
                "scripts.deploy.shared_edge_release",
                "activate",
                "--edge-root",
                str(self.root),
                "--release",
                "../outside",
                "--config",
                "bootstrap",
            ],
            cwd=Path(edge.__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("release name is invalid", completed.stderr)
