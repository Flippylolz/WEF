"""Tests for candidate verification release configuration."""

# ruff: noqa: D102, PT009, PT027, S104, S105

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy.candidate_config import (
    CandidateConfigurationError,
    CandidateContext,
    build_candidate_values,
    candidate_paths,
    validate_candidate_environment,
)
from scripts.transfer.constants import MIGRATION_HEAD

BUNDLE_CHECKSUM = "2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d"
BACKEND_IMAGE = "ghcr.io/flippylolz/wef-backend@sha256:" + "a" * 64
WEB_IMAGE = "ghcr.io/flippylolz/wef-web@sha256:" + "b" * 64
POSTGRES_USER = "wef_candidate"
POSTGRES_PASSWORD = "Candidate-Safe-Password-1234567890"


def sample_context(root: Path, *, test_mode: bool = True) -> CandidateContext:
    """Return one test candidate context."""
    return CandidateContext(
        root=root,
        bundle_checksum=BUNDLE_CHECKSUM,
        candidate_database="wef_hist_candidate",
        backend_image=BACKEND_IMAGE,
        web_image=WEB_IMAGE,
        verify_port=13100,
        test_mode=test_mode,
    )


class CandidateConfigTests(unittest.TestCase):
    """Verify candidate path layout and validation."""

    def test_candidate_paths_are_checksum_scoped(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = candidate_paths(root, BUNDLE_CHECKSUM)
            self.assertEqual(
                paths.restricted_originals,
                root / "candidates" / BUNDLE_CHECKSUM / "media" / "originals",
            )
            self.assertEqual(
                paths.public_derivatives,
                root / "candidates" / BUNDLE_CHECKSUM / "media" / "public",
            )

    def test_build_values_include_loopback_and_migration_head(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            values = build_candidate_values(
                context=sample_context(root),
                postgres_user=POSTGRES_USER,
                postgres_password=POSTGRES_PASSWORD,
            )
            self.assertEqual(values["WEF_CANDIDATE_VERIFY_BIND_ADDRESS"], "127.0.0.1")
            self.assertEqual(values["WEF_MIGRATION_HEAD"], MIGRATION_HEAD)
            self.assertIn("wef_hist_candidate", values["WEF_CANDIDATE_DATABASE_URL"])

    def test_rejects_non_loopback_bind_address(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context = sample_context(root)
            values = build_candidate_values(
                context=context,
                postgres_user=POSTGRES_USER,
                postgres_password=POSTGRES_PASSWORD,
            )
            values["WEF_CANDIDATE_VERIFY_BIND_ADDRESS"] = "0.0.0.0"
            with self.assertRaises(CandidateConfigurationError):
                validate_candidate_environment(values, context)

    def test_rejects_paths_outside_wef_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context = sample_context(root)
            values = build_candidate_values(
                context=context,
                postgres_user=POSTGRES_USER,
                postgres_password=POSTGRES_PASSWORD,
            )
            values["WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH"] = str(
                root.parent / "outside" / "public",
            )
            with self.assertRaises(CandidateConfigurationError):
                validate_candidate_environment(values, context)

    def test_rejects_invalid_bundle_checksum(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(CandidateConfigurationError):
                build_candidate_values(
                    context=CandidateContext(
                        root=root,
                        bundle_checksum="not-a-checksum",
                        candidate_database="wef_hist_candidate",
                        backend_image=BACKEND_IMAGE,
                        web_image=WEB_IMAGE,
                        test_mode=True,
                    ),
                    postgres_user=POSTGRES_USER,
                    postgres_password=POSTGRES_PASSWORD,
                )


if __name__ == "__main__":
    unittest.main()
