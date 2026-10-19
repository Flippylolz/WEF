"""Release-state, metadata and CLI refusal cases using synthetic evidence only."""

# ruff: noqa: D102, PT009, PT027

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import release_cache as cache
from scripts.deploy import release_observation as observation
from scripts.deploy import release_order as order
from scripts.deploy import release_report as report
from scripts.deploy import release_state as state
from scripts.test_release_report import END, OLD, SHA, START, fixture


class ReleaseEvidenceBoundaryTests(unittest.TestCase):
    """Use temporary state and process doubles; never GitHub or a production host."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_state_shape_validation_and_atomic_write_failure(self) -> None:
        path = self.root / "state.json"
        payload: object
        for payload in ([], {}, {"config_file": "fixture", "public_port": "80"}):
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(TypeError):
                state.read_state(path)
        valid = {
            "candidate_release_sha": SHA,
            "failure_reason": "health_verification",
            "recorded_at": START,
            "restored_release_sha": None,
        }
        for payload in ([], {}, {**valid, "restored_release_sha": False}):
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(payload=payload), self.assertRaises(TypeError):
                state.read_failure_state(path)
        path.write_text(json.dumps(valid), encoding="utf-8")
        self.assertEqual(state.read_failure_state(path), valid)
        before = path.read_bytes()
        with (
            mock.patch.object(
                Path, "replace", side_effect=OSError("synthetic replacement failure")
            ),
            self.assertRaises(OSError),
        ):
            state.write_json_state(path, {"replacement": True})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.root.glob(".state.json.*.tmp")), [])

    def test_release_links_reject_targets_outside_owned_roots(self) -> None:
        for release, config in (
            (self.root / "outside", self.root / "secrets/releases" / SHA / "production.env"),
            (self.root / "releases" / SHA, self.root / "outside/production.env"),
        ):
            with self.subTest(release=release, config=config), self.assertRaises(ValueError):
                state.activate_release_links(self.root, release, config)

    def test_state_cli_round_trips_fields_failure_evidence_and_atomic_links(self) -> None:
        path = self.root / "state.json"
        release = self.root / "releases" / SHA
        config = self.root / "secrets/releases" / SHA / "production.env"
        release.mkdir(parents=True)
        config.parent.mkdir(parents=True)
        values = {
            "release_dir": str(release),
            "config_file": str(config),
            "release_sha": SHA,
            "public_port": 8080,
        }
        with mock.patch.object(
            sys,
            "argv",
            ["release-state", "write", str(path), str(release), str(config), SHA, "8080"],
        ):
            self.assertEqual(state.main(), 0)
        self.assertEqual(state.read_state(path), values)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        for field, value in values.items():
            with (
                self.subTest(field=field),
                mock.patch.object(sys, "argv", ["release-state", "get", str(path), field]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(state.main(), 0)
                self.assertEqual(out.getvalue(), f"{value}\n")
        with mock.patch.object(
            sys, "argv", ["release-state", "activate", str(self.root), str(release), str(config)]
        ):
            self.assertEqual(state.main(), 0)
        self.assertEqual((self.root / "releases/current").resolve(), release.resolve())
        self.assertEqual((self.root / "secrets/current").resolve(), config.parent.resolve())
        failure = self.root / "failure.json"
        for restored in ([], [OLD]):
            with (
                self.subTest(restored=restored),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "release-state",
                        "failure",
                        str(failure),
                        SHA,
                        "health_verification",
                        START,
                        *restored,
                    ],
                ),
            ):
                self.assertEqual(state.main(), 0)
            self.assertEqual(
                state.read_failure_state(failure)["restored_release_sha"], OLD if restored else None
            )
        result = subprocess.run(  # noqa: S603 - current Python, fixed module and synthetic state
            [sys.executable, "-m", "scripts.deploy.release_state", "get", str(path), "public_port"],
            cwd=Path(state.__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "8080\n")

    def test_order_snapshot_refuses_orphaned_invalid_and_inconsistent_state(self) -> None:
        (self.root / "state").mkdir()
        releases = self.root / "releases"
        releases.mkdir()
        active = releases / "current"
        active.symlink_to(releases / "missing")
        with self.assertRaisesRegex(ValueError, "without durable current state"):
            order.snapshot(self.root)
        active.unlink()
        path = self.root / "state/current.json"
        for sha in (True, "invalid"):
            path.write_text(json.dumps({"release_sha": sha}), encoding="utf-8")
            with self.subTest(sha=sha), self.assertRaisesRegex(ValueError, "SHA is invalid"):
                order.snapshot(self.root)
        release = releases / SHA
        release.mkdir()
        active.symlink_to(release)
        secrets = self.root / "secrets/releases" / SHA
        secrets.mkdir(parents=True)
        current_secret = self.root / "secrets/current"
        current_secret.symlink_to(secrets)
        values = {
            "release_sha": SHA,
            "release_dir": str(release),
            "config_file": str(secrets / "production.env"),
        }
        for changed in (
            {"release_dir": str(self.root / "wrong")},
            {"config_file": str(self.root / "wrong.env")},
        ):
            path.write_text(json.dumps({**values, **changed}), encoding="utf-8")
            with (
                self.subTest(changed=changed),
                self.assertRaisesRegex(ValueError, "configuration links"),
            ):
                order.snapshot(self.root)
        path.write_text(json.dumps(values), encoding="utf-8")
        (release / "release-manifest.json").write_text(
            json.dumps({"source_sha": OLD}), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "manifest and state disagree"):
            order.snapshot(self.root)

    def test_ancestry_and_candidate_identity_fail_closed(self) -> None:
        for executable, older in ((None, SHA), ("/fixture/git", "bad")):
            with (
                self.subTest(executable=executable),
                mock.patch("scripts.deploy.release_order.shutil.which", return_value=executable),
                self.assertRaisesRegex(ValueError, "full source history"),
            ):
                order.ancestor(older, OLD)
        with (
            mock.patch("scripts.deploy.release_order.shutil.which", return_value="/fixture/git"),
            mock.patch("scripts.deploy.release_order.subprocess.run") as run,
        ):
            for code in (0, 1):
                run.return_value = subprocess.CompletedProcess([], code)
                self.assertEqual(order.ancestor(SHA, OLD), code == 0)
                self.assertEqual(
                    run.call_args.args[0], ["/fixture/git", "merge-base", "--is-ancestor", SHA, OLD]
                )
            run.return_value = subprocess.CompletedProcess([], 2)
            with self.assertRaisesRegex(ValueError, "could not be verified"):
                order.ancestor(SHA, OLD)
        for current, candidate in (
            ({}, {"source_sha": "bad"}),
            ({"release_sha": False}, {"source_sha": SHA}),
        ):
            with (
                self.subTest(current=current),
                self.assertRaisesRegex(ValueError, "identity is invalid"),
            ):
                order.decide(current, candidate)
        with self.assertRaisesRegex(ValueError, "pending source identity"):
            order.mark_pending(self.root, "bad")

    def test_order_cli_snapshot_decision_guard_pending_and_noop_observations(self) -> None:
        (self.root / "state").mkdir()
        with (
            mock.patch.object(sys, "argv", ["release-order", "snapshot", str(self.root)]),
            mock.patch("sys.stdout", new_callable=StringIO) as out,
        ):
            self.assertEqual(order.main(), 0)
            self.assertEqual(json.loads(out.getvalue()), {"release_sha": None, "images": {}})
        current, manifest = self.root / "current.json", self.root / "manifest.json"
        current.write_text('{"release_sha":null}', encoding="utf-8")
        manifest.write_text(json.dumps({"source_sha": SHA}), encoding="utf-8")
        with (
            mock.patch.object(
                sys, "argv", ["release-order", "decide", str(current), str(manifest)]
            ),
            mock.patch("sys.stdout", new_callable=StringIO) as out,
        ):
            self.assertEqual(order.main(), 0)
            self.assertEqual(out.getvalue(), "activate\n")
        with mock.patch.object(sys, "argv", ["release-order", "guard", str(self.root), "none"]):
            self.assertEqual(order.main(), 0)
        with mock.patch.object(sys, "argv", ["release-order", "pending", str(self.root), SHA]):
            self.assertEqual(order.main(), 0)
        self.assertEqual(
            json.loads((self.root / "state/activation-pending.json").read_text())["release_sha"],
            SHA,
        )
        for outcome in ("already_current", "superseded"):
            with (
                self.subTest(outcome=outcome),
                mock.patch.object(sys, "argv", ["release-order", "observation", SHA, outcome]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(order.main(), 0)
                payload = json.loads(out.getvalue().removeprefix("observation="))
            self.assertEqual(payload["release_sha"], SHA)
            self.assertEqual("healthy_at" in payload, outcome == "already_current")
        with (
            mock.patch.object(sys, "argv", ["release-order", "observation", "bad", "unknown"]),
            mock.patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            order.main()
        self.assertEqual(error.exception.code, 2)

    def test_observation_rejects_invalid_identity_and_ignores_naive_or_invalid_times(self) -> None:
        payload = {
            "release_sha": SHA,
            "healthy_at": "not-a-date",
            "started_at": "2026-01-01T00:00:00",
        }
        self.assertEqual(
            observation.clean_observation(payload, SHA),
            {"release_sha": SHA, "previous_sha": None, "restored_sha": None},
        )
        for event, sha in (("unknown", SHA), ("started", "bad")):
            with (
                self.subTest(event=event),
                self.assertRaisesRegex(ValueError, "invalid release observation"),
            ):
                observation.record(
                    self.root / "observation.json", event, sha, self.root / "absent.json"
                )

    def test_observation_cli_exports_only_safe_fields_and_direct_script_records(self) -> None:
        path = self.root / "observation.json"
        path.write_text(
            json.dumps(
                {"release_sha": SHA, "healthy_at": END, "private": "synthetic-private-value"}
            ),
            encoding="utf-8",
        )
        with (
            mock.patch.object(sys, "argv", ["observation", "export", str(path), SHA]),
            mock.patch("sys.stdout", new_callable=StringIO) as out,
        ):
            self.assertEqual(observation.main(), 0)
            self.assertNotIn("synthetic-private-value", out.getvalue())
        with (
            mock.patch.object(sys, "argv", ["observation", "healthy", str(path), SHA]),
            mock.patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit) as error,
        ):
            observation.main()
        self.assertEqual(error.exception.code, 2)
        result = subprocess.run(  # noqa: S603 - current Python, fixed entrypoint and synthetic arguments
            [
                sys.executable,
                str(Path(observation.__file__)),
                "started",
                str(path),
                SHA,
                str(self.root / "absent.json"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(path.read_text())["previous_sha"])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_cache_capture_errors_and_cli_never_export_build_metadata(self) -> None:
        with (
            mock.patch("scripts.deploy.release_cache.shutil.which", return_value="/fixture/docker"),
            mock.patch("scripts.deploy.release_cache.subprocess.run") as run,
        ):
            for error in (
                OSError("synthetic offline"),
                subprocess.TimeoutExpired("fixture", 20),
                ValueError("synthetic decode failure"),
            ):
                run.side_effect = error
                self.assertEqual(
                    cache.collect_cache({"buildx.build.ref": "builder/node/id"})["state"], "unknown"
                )
        output = self.root / "output"
        for metadata in ("{", "[]", '{"private":"synthetic-private-value"}'):
            output.write_text("", encoding="utf-8")
            with (
                self.subTest(metadata=metadata),
                mock.patch.dict(
                    os.environ, {"BUILD_METADATA": metadata, "GITHUB_OUTPUT": str(output)}
                ),
                mock.patch("scripts.deploy.release_cache.shutil.which", return_value=None),
            ):
                self.assertEqual(cache.main(), 0)
            self.assertEqual(
                json.loads(output.read_text().removeprefix("cache_metrics="))["state"], "unknown"
            )
            self.assertNotIn("synthetic-private-value", output.read_text())
        result = subprocess.run(
            [sys.executable, "-m", "scripts.deploy.release_cache"],
            cwd=Path(cache.__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "PATH": str(self.root),
                "GITHUB_OUTPUT": str(output),
                "BUILD_METADATA": "{}",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_report_timestamp_skipped_intervals_noop_health_and_unknown_cache(self) -> None:
        self.assertIsNone(report.timestamp("not-a-date"))
        self.assertEqual(
            report.interval_gap(START, END, [{"conclusion": "skipped"}])["seconds"], 60
        )
        needs = fixture()
        needs["deploy"]["outputs"]["observation"] = json.dumps(
            {"release_sha": SHA, "already_current_at": START, "healthy_at": END}
        )
        result = report.build_report(needs, {}, [])
        self.assertEqual(result["outcome"], "already_current")
        self.assertIsNone(result["merge_to_healthy"]["seconds"])
        for raw in ("[]", "{", None):
            needs["build-backend"] = {"outputs": {"cache_metrics": raw}}
            self.assertEqual(report.cache_evidence(needs)["state"], "unknown")
        result = report.build_report(
            fixture(),
            {"id": 1},
            [
                {
                    "name": "<fixture|name",
                    "started_at": START,
                    "completed_at": END,
                    "conclusion": "success",
                },
                {"name": "Release outcome"},
            ],
        )
        self.assertEqual(len(result["stages"]), 1)
        self.assertIn("&lt;fixture\\|name | success | 60.0", report.render_summary(result))

    def test_api_retries_are_bounded_and_missing_or_nonobject_metadata_stays_unavailable(
        self,
    ) -> None:
        with mock.patch("scripts.deploy.release_report.shutil.which", return_value=None):
            self.assertEqual(report.read_api("fixture"), {})
        with (
            mock.patch("scripts.deploy.release_report.shutil.which", return_value="/fixture/gh"),
            mock.patch("scripts.deploy.release_report.time.sleep") as sleep,
            mock.patch("scripts.deploy.release_report.subprocess.run") as run,
        ):
            run.side_effect = [
                subprocess.TimeoutExpired("fixture", 30),
                subprocess.CompletedProcess([], 1, "", ""),
                subprocess.CompletedProcess([], 0, "[]", ""),
            ]
            self.assertEqual(report.read_api("fixture"), {})
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 15])
            self.assertEqual(run.call_count, 3)
            run.side_effect = None
            run.return_value = subprocess.CompletedProcess([], 0, '{"items":[]}', "")
            self.assertEqual(report.read_api("fixture", wrap_list=True), {"items": []})
            self.assertEqual(run.call_args.args[0][-2:], ["--jq", "{items: .}"])

    def test_report_real_entrypoint_preserves_missing_actions_evidence(self) -> None:
        output, summary = self.root / "report.json", self.root / "summary.md"
        result = subprocess.run(  # noqa: S603 - current Python, fixed entrypoint and synthetic arguments
            [sys.executable, "-m", "scripts.deploy.release_report", str(output)],
            cwd=Path(report.__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "PATH": str(self.root),
                "GITHUB_REPOSITORY": "fixture/repo",
                "GITHUB_RUN_ID": "1",
                "GITHUB_RUN_ATTEMPT": "1",
                "RELEASE_NEEDS": "{}",
                "GITHUB_STEP_SUMMARY": str(summary),
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(output.read_text())
        self.assertEqual(payload["outcome"], "verification_failed")
        self.assertEqual(payload["reporting_errors"], ["actions_metadata_unavailable"])
        self.assertIn("verification_failed", summary.read_text())
