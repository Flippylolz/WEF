"""Synthetic filesystem and process boundaries for historical activation."""

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

from scripts.deploy import activate_historical_candidate as activation
from scripts.deploy.validate_release import parse_environment


class ActivationBoundaryTests(unittest.TestCase):
    """Never contact Docker, HTTPS or any host outside one temporary root."""

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checksum = "a" * 64
        self.context = activation.ActivationContext(
            self.root,
            self.root / "production.env",
            self.checksum,
        )
        self.values = {
            "WEF_DATABASE_URL": "postgresql+asyncpg://fixture:synthetic@db:5432/wef",
            "POSTGRES_DB": "wef",
            "WEF_RELEASE_DIR": str(self.root / "release"),
        }
        activation.write_environment(self.context.config_file, self.values)
        self.public, self.originals = activation.media_roots_for_checksum(self.root, self.checksum)
        for path in (self.public, self.originals):
            path.mkdir(parents=True)
            (path / "fixture.webp").write_bytes(b"synthetic")
        for kind in ("public", "originals"):
            path = self.root / "media" / kind
            path.mkdir(parents=True)
            (path / "before.txt").write_text("before", encoding="utf-8")

    def test_urls_refuse_unsafe_shapes_and_redact_optional_credentials(self) -> None:
        with self.assertRaisesRegex(activation.HistoricalActivationError, "must be postgresql"):
            activation.rewrite_database_url("https://example.test/db", "wef_test_candidate")
        for url in ("postgresql://host/", "postgresql://host/bad-name"):
            with self.subTest(url=url), self.assertRaises(activation.HistoricalActivationError):
                activation.database_name_from_url(url)
        for value, expected in (
            ("postgresql://host/wef", "postgresql://host/wef"),
            ("postgresql://fixture:synthetic@host/wef", "postgresql://fixture:***@host/wef"),
            ("postgresql://:synthetic@host/wef", "postgresql://***@host/wef"),
            ("postgresql://fixture:synthetic@/wef", "postgresql://fixture:***@/wef"),
        ):
            with self.subTest(value=value):
                self.assertEqual(activation.redact_database_url(value), expected)

    def test_environment_replace_failure_preserves_original_and_cleans_temporary(self) -> None:
        before = self.context.config_file.read_bytes()
        with (
            mock.patch.object(Path, "replace", side_effect=OSError("synthetic replace failure")),
            self.assertRaisesRegex(OSError, "synthetic replace failure"),
        ):
            activation.write_environment(self.context.config_file, {"VALUE": "new"})
        self.assertEqual(self.context.config_file.read_bytes(), before)
        self.assertEqual(list(self.root.glob(".production.env.*.tmp")), [])
        self.assertEqual(self.context.config_file.stat().st_mode & 0o777, 0o600)

    def test_candidate_media_refuses_checksum_and_missing_or_empty_trees(self) -> None:
        with self.assertRaisesRegex(activation.HistoricalActivationError, "64 lowercase hex"):
            activation.validate_candidate_media(self.root, "wrong")
        for tree in (self.public, self.originals):
            marker = tree / "fixture.webp"
            marker.unlink()
            with (
                self.subTest(tree=tree),
                self.assertRaisesRegex(
                    activation.HistoricalActivationError,
                    "missing or empty",
                ),
            ):
                activation.validate_candidate_media(self.root, self.checksum)
            marker.write_bytes(b"synthetic")

    def test_media_backups_refuse_existing_directories_and_broken_links(self) -> None:
        for kind in ("public", "originals"):
            backup = self.root / "media" / f"{kind}.held"
            backup.symlink_to(self.root / "absent")
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(
                    activation.HistoricalActivationError,
                    "backup already exists",
                ),
            ):
                activation.point_media_roots(
                    self.root, bundle_checksum=self.checksum, backup_suffix="held"
                )
            backup.unlink()
            public_backup = self.root / "media" / "public.held"
            if public_backup.exists():
                public_backup.rename(self.root / "media/public")

    def test_media_pointing_checks_symlink_result_and_allows_absent_current_trees(self) -> None:
        for kind in ("public", "originals"):
            current = self.root / "media" / kind
            (current / "before.txt").unlink()
            current.rmdir()
        with (
            mock.patch.object(Path, "symlink_to", return_value=None),
            self.assertRaisesRegex(activation.HistoricalActivationError, "verification failed"),
        ):
            activation.point_media_roots(
                self.root, bundle_checksum=self.checksum, backup_suffix="before"
            )
        activation.point_media_roots(
            self.root, bundle_checksum=self.checksum, backup_suffix="before"
        )
        self.assertTrue((self.root / "media/public").is_symlink())
        self.assertTrue((self.root / "media/originals").is_symlink())

    def test_restore_removes_current_directories_and_requires_both_backups(self) -> None:
        media = self.root / "media"
        with self.assertRaisesRegex(activation.HistoricalActivationError, "missing media backup"):
            activation.restore_media_roots(self.root, backup_suffix="saved")
        (media / "public.saved").mkdir()
        with self.assertRaisesRegex(activation.HistoricalActivationError, "originals.saved"):
            activation.restore_media_roots(self.root, backup_suffix="saved")
        (media / "originals.saved").mkdir()
        activation.restore_media_roots(self.root, backup_suffix="saved")
        self.assertTrue((media / "public").is_dir())
        self.assertTrue((media / "originals").is_dir())

    def test_current_pointers_tolerate_uncreated_media_roots(self) -> None:
        for kind in ("public", "originals"):
            path = self.root / "media" / kind
            (path / "before.txt").unlink()
            path.rmdir()
        pointers = activation.current_pointers(self.context.config_file, self.root)
        self.assertEqual(pointers.database_name, "wef")
        self.assertEqual(pointers.media_public, str(self.root / "media/public"))
        self.assertEqual(pointers.media_originals, str(self.root / "media/originals"))

    def test_process_failure_messages_keep_available_diagnostics(self) -> None:
        for stdout, stderr, detail in (
            ("fallback", "", "fallback"),
            ("unused", "denied", "denied"),
            ("", "", ""),
        ):
            with (
                self.subTest(detail=detail),
                mock.patch(
                    "scripts.deploy.activate_historical_candidate.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, stdout, stderr),
                ),
                self.assertRaisesRegex(
                    activation.HistoricalActivationError, "command failed"
                ) as error,
            ):
                activation.psql(self.context, "wef_test_candidate", "SELECT 1")
            self.assertTrue(str(error.exception).endswith(detail))

    def test_identity_sync_checks_restore_and_fingerprints(self) -> None:
        for detail in ("denied", ""):
            with (
                self.subTest(detail=detail),
                mock.patch(
                    "scripts.deploy.activate_historical_candidate.subprocess.run",
                ) as run,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess([], 0, "", ""),
                    subprocess.CompletedProcess([], 0, "", ""),
                    subprocess.CompletedProcess([], 0, "synthetic identity SQL", ""),
                    subprocess.CompletedProcess([], 1, "", detail),
                ]
                with self.assertRaisesRegex(activation.HistoricalActivationError, "identity sync"):
                    activation.sync_identity_tables(self.context)
                self.assertEqual(run.call_args.kwargs["input"], "synthetic identity SQL")
        for equal in (False, True):
            with (
                self.subTest(equal=equal),
                mock.patch(
                    "scripts.deploy.activate_historical_candidate.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, "synthetic identity SQL", ""),
                ),
                mock.patch.object(
                    activation,
                    "identity_fingerprint",
                    side_effect=["first", "first" if equal else "second"],
                ),
            ):
                if equal:
                    activation.sync_identity_tables(self.context)
                else:
                    with self.assertRaisesRegex(
                        activation.HistoricalActivationError, "fingerprint mismatch"
                    ):
                        activation.sync_identity_tables(self.context)

    def test_identity_fingerprint_uses_bounded_identity_session_aggregates(self) -> None:
        with mock.patch("scripts.deploy.activate_historical_candidate.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, " 2:3:synthetic-hash\n", "")
            self.assertEqual(
                activation.identity_fingerprint(self.context, "wef_test_candidate"),
                "2:3:synthetic-hash",
            )
            statement = run.call_args.args[0][-1]
            self.assertIn("count(*)::text FROM users", statement)
            self.assertIn("count(*)::text FROM auth_sessions", statement)
            self.assertIn("ORDER BY id", statement)

    def test_migration_and_application_commands_resolve_fallback_and_cutover(self) -> None:
        release = Path(self.values["WEF_RELEASE_DIR"])
        release.mkdir()
        base = release / "compose.production.yaml"
        with self.assertRaisesRegex(activation.HistoricalActivationError, "not found for migrate"):
            activation.migrate_candidate(self.context, self.values)
        with self.assertRaisesRegex(activation.HistoricalActivationError, "not found"):
            activation.resolve_compose_files(self.context, self.values)
        base.write_text("services: {}\n", encoding="utf-8")
        with mock.patch("scripts.deploy.activate_historical_candidate.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            activation.migrate_candidate(self.context, self.values)
            self.assertIn(str(base), run.call_args.args[0])
            self.assertIn(
                "WEF_DATABASE_URL=postgresql+asyncpg://fixture:synthetic@db:5432/wef_hist_candidate",
                run.call_args.args[0],
            )
            with mock.patch.object(activation, "reconnect_shared_edge") as reconnect:
                activation.recreate_application(self.context, self.values)
                self.assertIn("edge", run.call_args.args[0])
                (release / "compose.production-cutover.yaml").write_text(
                    "services: {}\n", encoding="utf-8"
                )
                activation.recreate_application(self.context, self.values)
                self.assertEqual(run.call_args.args[0][-1], "media-edge")
                self.assertEqual(reconnect.call_count, 2)
        current = self.root / "releases/current"
        current.mkdir(parents=True)
        (current / "compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
        base.unlink()
        self.assertEqual(
            activation.resolve_compose_files(self.context, self.values),
            (current / "compose.production.yaml", None),
        )
        with mock.patch("scripts.deploy.activate_historical_candidate.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            activation.migrate_candidate(self.context, self.values)
            self.assertIn(str(current / "compose.production.yaml"), run.call_args.args[0])

    def test_reconnect_selects_release_then_operations_script_or_skips(self) -> None:
        for selected in (
            "/home/nuc/wef/releases/current/scripts/deploy/reconnect-wef-upstreams.sh",
            "/home/nuc/wef-shared-edge/ops/reconnect-wef-upstreams.sh",
            None,
        ):
            with (
                self.subTest(selected=selected),
                mock.patch.object(
                    Path,
                    "is_file",
                    autospec=True,
                    side_effect=lambda path, chosen=selected: str(path) == chosen,
                ),
                mock.patch("scripts.deploy.activate_historical_candidate.subprocess.run") as run,
            ):
                run.return_value = subprocess.CompletedProcess([], 0, "", "")
                activation.reconnect_shared_edge()
                if selected is None:
                    run.assert_not_called()
                else:
                    self.assertEqual(run.call_args.args[0], ["bash", selected])

    def test_real_https_probe_semantic_failures_and_media_extensions(self) -> None:
        public = self.root / "media/public"
        for responses, reason in (
            (["wrong"], "live health unexpected"),
            (["live", "wrong"], "ready health unexpected"),
            (["live", "ready", "wrong"], "map locations smoke failed"),
            (["live", "ready", "FeatureCollection"], "no public derivative"),
        ):
            with (
                self.subTest(reason=reason),
                mock.patch(
                    "scripts.deploy.activate_historical_candidate.subprocess.run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0, value, "") for value in responses
                    ],
                ),
                self.assertRaisesRegex(activation.HistoricalActivationError, reason),
            ):
                activation.smoke_public_https(self.root, "https://example.test", attempts=1)
        for extension in ("webp", "jpg"):
            sample = public / f"synthetic.{extension}"
            sample.write_bytes(b"synthetic")
            for status in ("503", "200"):
                with (
                    self.subTest(extension=extension, status=status),
                    mock.patch(
                        "scripts.deploy.activate_historical_candidate.subprocess.run",
                        side_effect=[
                            subprocess.CompletedProcess([], 0, value, "")
                            for value in ("live", "ready", "FeatureCollection", status)
                        ],
                    ) as run,
                ):
                    if status == "200":
                        activation.smoke_public_https(self.root, "https://example.test", attempts=1)
                    else:
                        with self.assertRaisesRegex(
                            activation.HistoricalActivationError, "HTTP 503"
                        ):
                            activation.smoke_public_https(
                                self.root, "https://example.test", attempts=1
                            )
                    self.assertEqual(
                        run.call_args.args[0][-1], f"https://example.test/media/{sample.name}"
                    )
            sample.unlink()
        with self.assertRaisesRegex(activation.HistoricalActivationError, "unknown smoke failure"):
            activation.smoke_public_https(self.root, attempts=0)

    def test_activation_dry_run_has_no_mutations_and_redacts_evidence(self) -> None:
        before = self.context.config_file.read_bytes()
        with mock.patch.object(activation, "identity_fingerprint", side_effect=["current", "old"]):
            plan = activation.activate(self.context, dry_run=True)
        self.assertTrue(plan["identity_sync_required"])
        self.assertNotIn("synthetic@", json.dumps(plan))
        self.assertEqual(self.context.config_file.read_bytes(), before)
        self.assertFalse((self.root / "state").exists())

    def test_activation_commit_updates_environment_media_and_state(self) -> None:
        with (
            mock.patch.object(activation, "identity_fingerprint", return_value="same"),
            mock.patch.object(
                activation,
                "migrate_candidate",
            ) as migrate,
            mock.patch.object(activation, "sync_identity_tables") as sync,
            mock.patch.object(
                activation,
                "recreate_application",
            ) as recreate,
            mock.patch.object(activation, "smoke_public_https") as smoke,
        ):
            result = activation.activate(self.context)
        self.assertEqual(result["status"], "activated")
        migrate.assert_called_once()
        sync.assert_not_called()
        recreate.assert_called_once()
        smoke.assert_called_once_with(self.root)
        self.assertEqual(
            parse_environment(self.context.config_file)["POSTGRES_DB"], "wef_hist_candidate"
        )
        self.assertTrue((self.root / "media/public").is_symlink())
        saved = json.loads((self.root / "state" / activation.ACTIVATION_STATE).read_text())
        self.assertEqual(saved, result)
        self.assertNotIn("synthetic@", json.dumps(saved))

    def test_activation_failure_restores_environment_and_original_media(self) -> None:
        with (
            mock.patch.object(
                activation, "identity_fingerprint", side_effect=["new", "old", "old"]
            ),
            mock.patch.object(
                activation,
                "migrate_candidate",
            ),
            mock.patch.object(activation, "sync_identity_tables") as sync,
            mock.patch.object(
                activation,
                "recreate_application",
                side_effect=[RuntimeError("synthetic recreate failure"), None],
            ) as recreate,
            self.assertRaisesRegex(RuntimeError, "synthetic recreate failure"),
        ):
            activation.activate(self.context)
        sync.assert_called_once_with(self.context)
        self.assertEqual(recreate.call_count, 2)
        self.assertEqual(parse_environment(self.context.config_file), self.values)
        self.assertEqual((self.root / "media/public/before.txt").read_text(), "before")
        self.assertEqual((self.root / "media/originals/before.txt").read_text(), "before")
        self.assertFalse((self.root / "state" / activation.ACTIVATION_STATE).exists())

    def test_activation_refuses_already_active_database_and_occupied_lock(self) -> None:
        values = {**self.values, "WEF_DATABASE_URL": "postgresql://db/wef_hist_candidate"}
        activation.write_environment(self.context.config_file, values)
        with self.assertRaisesRegex(activation.HistoricalActivationError, "already points"):
            activation.activate(self.context)
        activation.write_environment(self.context.config_file, self.values)
        with (
            mock.patch.object(activation, "identity_fingerprint", return_value="same"),
            mock.patch(
                "scripts.deploy.activate_historical_candidate.fcntl.flock",
                side_effect=BlockingIOError,
            ),
            self.assertRaisesRegex(activation.HistoricalActivationError, "holds the host lock"),
        ):
            activation.activate(self.context)
        self.assertEqual(parse_environment(self.context.config_file), self.values)

    def test_cli_exclusive_mode_success_refusal_and_real_entrypoint(self) -> None:
        args = [
            "--root",
            str(self.root),
            "--config-file",
            str(self.context.config_file),
            "--bundle-checksum",
            self.checksum,
        ]
        for modes in ([], ["--dry-run", "--activate"]):
            with (
                self.subTest(modes=modes),
                mock.patch("sys.stderr", new_callable=StringIO),
                self.assertRaises(SystemExit) as error,
            ):
                activation.main([*args, *modes])
            self.assertEqual(error.exception.code, 2)
        with (
            mock.patch.object(activation, "activate", return_value={"dry_run": True}) as activate,
            mock.patch(
                "sys.stdout",
                new_callable=StringIO,
            ) as out,
        ):
            self.assertEqual(activation.main([*args, "--dry-run"]), 0)
            self.assertEqual(json.loads(out.getvalue()), {"dry_run": True})
            self.assertTrue(activate.call_args.kwargs["dry_run"])
        with (
            mock.patch.object(
                activation,
                "activate",
                side_effect=activation.HistoricalActivationError("synthetic refusal"),
            ),
            mock.patch(
                "sys.stderr",
                new_callable=StringIO,
            ) as err,
        ):
            self.assertEqual(activation.main([*args, "--activate"]), 1)
            self.assertIn("historical_activation: synthetic refusal", err.getvalue())
        result = subprocess.run(  # noqa: S603 - current Python, fixed module and synthetic arguments
            [
                sys.executable,
                "-m",
                "scripts.deploy.activate_historical_candidate",
                *args[:-1],
                "wrong",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(activation.__file__).resolve().parents[2],
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("64 lowercase hex", result.stderr)
