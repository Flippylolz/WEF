"""Unit tests for historical candidate activation helpers."""

# ruff: noqa: D101, D102, PT009, PT027

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.activate_historical_candidate import (
    HistoricalActivationError,
    point_media_roots,
    restore_media_roots,
    rewrite_database_url,
    update_environment_values,
    validate_candidate_media,
)


class RewriteDatabaseUrlTests(unittest.TestCase):
    def test_rewrites_path_only(self) -> None:
        url = "postgresql+asyncpg://wef:secret@db:5432/wef"
        self.assertEqual(
            rewrite_database_url(url, "wef_hist_candidate"),
            "postgresql+asyncpg://wef:secret@db:5432/wef_hist_candidate",
        )

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
