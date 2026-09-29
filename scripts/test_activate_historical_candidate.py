"""Unit tests for historical candidate activation helpers."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.deploy.activate_historical_candidate import (
    ActivationContext,
    HistoricalActivationError,
    point_media_roots,
    redact_database_url,
    resolve_compose_files,
    restore_media_roots,
    rewrite_database_url,
    smoke_public_https,
    update_environment_values,
    validate_candidate_media,
)


class PublicHttpsSmokeTests(unittest.TestCase):
    def test_primary_hostname_and_explicit_alias_override(self) -> None:
        root = Path("/synthetic/wef")
        with patch("scripts.deploy.activate_historical_candidate._probe_public_https") as probe:
            probe.return_value = None
            smoke_public_https(root)
            probe.assert_called_once_with("https://flipstarnuc.duckdns.org", root)
            probe.reset_mock()
            smoke_public_https(root, "https://2fa54e2405.duckdns.org")
            probe.assert_called_once_with("https://2fa54e2405.duckdns.org", root)

    def test_unhealthy_primary_origin_blocks_activation(self) -> None:
        with (
            patch("scripts.deploy.activate_historical_candidate._probe_public_https") as probe,
            patch("scripts.deploy.activate_historical_candidate.time.sleep") as sleep,
        ):
            probe.return_value = "not ready"
            with self.assertRaisesRegex(HistoricalActivationError, "failed after 2 attempts"):
                smoke_public_https(Path("/synthetic/wef"), attempts=2)
            self.assertEqual(probe.call_count, 2)
            sleep.assert_called_once_with(5.0)


class RewriteDatabaseUrlTests(unittest.TestCase):
    def test_rewrites_path_only(self) -> None:
        url = "postgresql+asyncpg://wef:secret@db:5432/wef"
        self.assertEqual(
            rewrite_database_url(url, "wef_hist_candidate"),
            "postgresql+asyncpg://wef:secret@db:5432/wef_hist_candidate",
        )

    def test_redacts_password(self) -> None:
        redacted = redact_database_url(
            "postgresql+asyncpg://wef:secret@db:5432/wef",
        )
        self.assertEqual(redacted, "postgresql+asyncpg://wef:***@db:5432/wef")

    def test_rejects_unsafe_names(self) -> None:
        with self.assertRaises(HistoricalActivationError):
            rewrite_database_url(
                "postgresql+asyncpg://wef:secret@db:5432/wef",
                "../escape",
            )


class UpdateEnvironmentTests(unittest.TestCase):
    def test_updates_db_keys(self) -> None:
        values = {
            "POSTGRES_DB": "wef",
            "WEF_DATABASE_URL": "postgresql+asyncpg://wef:x@db:5432/wef",
        }
        updated = update_environment_values(values, database_name="wef_hist_candidate")
        self.assertEqual(updated["POSTGRES_DB"], "wef_hist_candidate")
        self.assertIn("/wef_hist_candidate", updated["WEF_DATABASE_URL"])
        self.assertEqual(values["POSTGRES_DB"], "wef")


class ComposeResolutionTests(unittest.TestCase):
    def test_resolves_optional_cutover_overlay(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "releases" / "current"
            release.mkdir(parents=True)
            base = release / "compose.production.yaml"
            cutover = release / "compose.production-cutover.yaml"
            base.write_text("services: {}\n", encoding="utf-8")
            cutover.write_text("services: {}\n", encoding="utf-8")
            context = ActivationContext(
                root=root,
                config_file=root / "production.env",
                bundle_checksum="a" * 64,
            )
            resolved_base, resolved_cutover = resolve_compose_files(
                context,
                {"WEF_RELEASE_DIR": str(release)},
            )
            self.assertEqual(resolved_base, base)
            self.assertEqual(resolved_cutover, cutover)


class MediaPointerTests(unittest.TestCase):
    def test_points_and_restores_media_roots(self) -> None:
        checksum = "a" * 64
        with TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_public = root / "candidates" / checksum / "media" / "public"
            candidate_originals = root / "candidates" / checksum / "media" / "originals"
            candidate_public.mkdir(parents=True)
            candidate_originals.mkdir(parents=True)
            (candidate_public / "marker.txt").write_text("public", encoding="utf-8")
            (candidate_originals / "marker.txt").write_text(
                "original",
                encoding="utf-8",
            )
            media = root / "media"
            (media / "public").mkdir(parents=True)
            (media / "originals").mkdir(parents=True)
            (media / "public" / "old.txt").write_text("old", encoding="utf-8")
            (media / "originals" / "old.txt").write_text("old", encoding="utf-8")

            validate_candidate_media(root, checksum)
            point_media_roots(
                root,
                bundle_checksum=checksum,
                backup_suffix="pre-historical-activation",
            )
            self.assertTrue((media / "public").is_symlink())
            self.assertEqual(
                (media / "public" / "marker.txt").read_text(encoding="utf-8"),
                "public",
            )
            restore_media_roots(root, backup_suffix="pre-historical-activation")
            self.assertFalse((media / "public").is_symlink())
            self.assertEqual(
                (media / "public" / "old.txt").read_text(encoding="utf-8"),
                "old",
            )


if __name__ == "__main__":
    unittest.main()
