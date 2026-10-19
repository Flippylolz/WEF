"""Production and candidate configuration refuse unsafe synthetic inputs."""

# ruff: noqa: D102, PT009, PT027, S104

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.deploy import build_candidate_config as candidate_cli
from scripts.deploy import build_release_config as build
from scripts.deploy import candidate_config as candidate
from scripts.deploy import validate_release as validate
from scripts.test_candidate_config import (
    BUNDLE_CHECKSUM,
    POSTGRES_PASSWORD,
    POSTGRES_USER,
    sample_context,
)

ROOT = Path("/home/nuc/wef")
SHA = "a" * 40
BACKEND = "ghcr.io/flippylolz/wef-backend@sha256:" + "b" * 64
WEB = "ghcr.io/flippylolz/wef-web@sha256:" + "c" * 64
RELEASE = validate.ReleaseContext(ROOT, ROOT / "releases" / SHA, SHA, 3100)
CONTEXT = build.ConfigBuildContext(RELEASE, "0.0.0.0", BACKEND, WEB)


def fixture_environment() -> dict[str, str]:
    """Invent credentials without inspecting developer or CI secrets."""
    return {
        "POSTGRES_DB": "wef",
        "POSTGRES_USER": "wef",
        "POSTGRES_PASSWORD": "synthetic:/password-0123456789abcdef",
        "WEF_GEOAPIFY_API_KEY": "synthetic-geoapify-0123456789",
        "WEF_ADMIN_SESSION_SECRET": "synthetic-admin-session-0123456789abcdef",
        "WEF_CONTACT_ENCRYPTION_KEY": "a" * 64,
        "WEF_CONTACT_HMAC_KEY": "b" * 64,
        "WEF_TELEGRAM_API_ID": "12345678",
        "WEF_TELEGRAM_API_HASH": "c" * 32,
        "WEF_LOG_LEVEL": "info",
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
    }


def fixture_values() -> dict[str, str]:
    """Build a clean production environment using only invented values."""
    with mock.patch.dict(os.environ, fixture_environment(), clear=True):
        return build.build_values(CONTEXT)


class ProductionConfigurationBoundaryTests(unittest.TestCase):
    """Temporary files and clean environment mappings never access a host."""

    def test_round_trip_permissions_sorted_output_and_collision_refusal(self) -> None:
        values = fixture_values()
        self.assertIn("synthetic%3A%2Fpassword", values["WEF_DATABASE_URL"])
        self.assertEqual(values["WEF_LOG_LEVEL"], "INFO")
        self.assertEqual(values["WEF_PARSER_REPLAY_ENABLED"], "false")
        self.assertNotIn("WEF_GROQ_API_KEY", values)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "production.env"
            build.write_environment(path, values)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(validate.parse_environment(path), values)
            self.assertEqual(path.read_text().splitlines(), sorted(path.read_text().splitlines()))
            with self.assertRaises(FileExistsError):
                build.write_environment(path, {"REPLACED": "no"})
            self.assertEqual(validate.parse_environment(path), values)

    def test_required_and_unsafe_build_inputs_refuse_without_printing_values(self) -> None:
        for name in fixture_environment():
            for missing in (True, False):
                environment = fixture_environment()
                if missing:
                    del environment[name]
                else:
                    environment[name] = ""
                with (
                    self.subTest(name=name, missing=missing),
                    mock.patch.dict(os.environ, environment, clear=True),
                    self.assertRaisesRegex(ValueError, "required environment value is missing"),
                ):
                    build.build_values(CONTEXT)
        for name, invalid, diagnostic in (
            ("POSTGRES_DB", "unsafe-name", "safe PostgreSQL identifiers"),
            ("POSTGRES_USER", "unsafe-name", "safe PostgreSQL identifiers"),
            ("POSTGRES_PASSWORD", "unsafe'password-0123456789abcdef", "database password"),
            ("WEF_GEOAPIFY_API_KEY", "unsafe key", "Geoapify API key"),
            ("WEF_ADMIN_SESSION_SECRET", "short", "admin session secret"),
            ("WEF_LOG_LEVEL", "TRACE", "log level"),
            ("WEF_CONTACT_ENCRYPTION_KEY", "bad-key", "encryption key"),
            ("WEF_CONTACT_HMAC_KEY", "bad-key", "HMAC key"),
            ("WEF_CONTACT_HMAC_KEY", "a" * 64, "must be distinct"),
            ("WEF_TELEGRAM_API_ID", "0", "positive integer"),
            ("WEF_TELEGRAM_API_HASH", "bad-hash", "32 hexadecimal"),
        ):
            with (
                self.subTest(name=name),
                mock.patch.dict(os.environ, {**fixture_environment(), name: invalid}, clear=True),
                self.assertRaisesRegex(ValueError, diagnostic) as error,
            ):
                build.build_values(CONTEXT)
            self.assertNotIn(invalid, str(error.exception))

    def test_bootstrap_pair_lengths_and_normalized_optional_credentials(self) -> None:
        for extra, diagnostic in (
            ({"WEF_BOOTSTRAP_OWNER_USERNAME": "owner"}, "both be set"),
            ({"WEF_BOOTSTRAP_OWNER_PASSWORD": "synthetic-password"}, "both be set"),
            (
                {
                    "WEF_BOOTSTRAP_OWNER_USERNAME": "ab",
                    "WEF_BOOTSTRAP_OWNER_PASSWORD": "long-password",
                },
                "minimum length",
            ),
            (
                {"WEF_BOOTSTRAP_OWNER_USERNAME": "owner", "WEF_BOOTSTRAP_OWNER_PASSWORD": "short"},
                "minimum length",
            ),
        ):
            with (
                self.subTest(extra=extra),
                mock.patch.dict(os.environ, {**fixture_environment(), **extra}, clear=True),
                self.assertRaisesRegex(ValueError, diagnostic),
            ):
                build.build_values(CONTEXT)
        with mock.patch.dict(
            os.environ,
            {
                **fixture_environment(),
                "WEF_BOOTSTRAP_OWNER_USERNAME": " owner ",
                "WEF_BOOTSTRAP_OWNER_PASSWORD": " synthetic-password ",
                "WEF_TELEGRAM_SESSION": " synthetic-session ",
                "WEF_TELEGRAM_PHONE": " +48123456789 ",
                "WEF_PARSER_REPLAY_ENABLED": " TRUE ",
                "WEF_PARSER_REPLAY_AUTO_APPLY": "false",
            },
            clear=True,
        ):
            values = build.build_values(CONTEXT)
        self.assertEqual(values["WEF_BOOTSTRAP_OWNER_USERNAME"], "owner")
        self.assertEqual(values["WEF_BOOTSTRAP_OWNER_PASSWORD"], "synthetic-password")
        self.assertEqual(values["WEF_TELEGRAM_SESSION"], "synthetic-session")
        self.assertEqual(values["WEF_TELEGRAM_PHONE"], "+48123456789")
        self.assertEqual(values["WEF_PARSER_REPLAY_ENABLED"], "true")
        for flag in ("WEF_PARSER_REPLAY_ENABLED", "WEF_PARSER_REPLAY_AUTO_APPLY"):
            with (
                self.subTest(flag=flag),
                mock.patch.dict(os.environ, {**fixture_environment(), flag: "maybe"}, clear=True),
                self.assertRaisesRegex(ValueError, "parser replay flags"),
            ):
                build.build_values(CONTEXT)

    def test_groq_settings_preserve_explicit_flags_and_blank_batch_defaults(self) -> None:
        for enabled, chunk in (("true", "20"), ("false", "2")):
            with mock.patch.dict(
                os.environ,
                {
                    **fixture_environment(),
                    "WEF_GROQ_API_KEY": "synthetic-groq-key-0123456789",
                    "WEF_GROQ_USE_BATCH_API": enabled,
                    "WEF_GROQ_BATCH_CHUNK_SIZE": " ",
                    "WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS": "",
                    "WEF_GROQ_BATCH_MAX_WAIT_SECONDS": "",
                    "WEF_AI_CURATION_ENABLED": "true",
                    "WEF_GROQ_ZDR_VERIFIED": "true",
                    "WEF_AI_RECOVERY_ENABLED": "true",
                    "WEF_AI_RECOVERY_ACTIVATION_VERIFIED": "true",
                    "WEF_AI_RECOVERY_AUTO_APPLY": "true",
                    "WEF_AI_RECOVERY_OWNER_ID": "12345678-1234-1234-1234-123456789ABC",
                },
                clear=True,
            ):
                values = build.build_values(CONTEXT)
            self.assertEqual(values["WEF_GROQ_BATCH_CHUNK_SIZE"], chunk)
            self.assertEqual(values["WEF_GROQ_USE_BATCH_API"], enabled)
            self.assertEqual(values["WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS"], "2")
            self.assertEqual(values["WEF_GROQ_BATCH_MAX_WAIT_SECONDS"], "3600")
            self.assertEqual(
                values["WEF_AI_RECOVERY_OWNER_ID"], "12345678-1234-1234-1234-123456789abc"
            )
            self.assertEqual(values["WEF_AI_RECOVERY_AUTO_APPLY"], "true")

    def test_groq_unsafe_values_and_numeric_boundaries_refuse(self) -> None:
        invalid_settings = (
            ("WEF_GROQ_API_KEY", "bad key", "Groq API key"),
            ("WEF_GROQ_MODEL", "other/model", "Groq model"),
            ("WEF_AI_CURATION_ENABLED", "maybe", "enablement flags"),
            ("WEF_GROQ_ZDR_VERIFIED", "maybe", "enablement flags"),
            ("WEF_GROQ_TIMEOUT_SECONDS", "0", "Groq timeout"),
            ("WEF_GROQ_TIMEOUT_SECONDS", "121", "Groq timeout"),
            ("WEF_GROQ_USE_BATCH_API", "maybe", "batch API flag"),
            *(("WEF_GROQ_BATCH_CHUNK_SIZE", value, "chunk size") for value in ("x", "0", "101")),
            ("WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS", "x", "must be a number"),
            *(
                ("WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS", value, "from 0.5 to 60")
                for value in ("0", "61", "nan", "inf")
            ),
            *(
                ("WEF_GROQ_BATCH_MAX_WAIT_SECONDS", value, "from 30 to 86400")
                for value in ("x", "29", "86401")
            ),
            *(
                (name, "maybe", "AI recovery flags")
                for name in (
                    "WEF_AI_RECOVERY_ENABLED",
                    "WEF_AI_RECOVERY_ACTIVATION_VERIFIED",
                    "WEF_AI_RECOVERY_AUTO_APPLY",
                )
            ),
            ("WEF_AI_RECOVERY_OWNER_ID", "invalid-uuid", "UUID"),
        )
        for name, value, diagnostic in invalid_settings:
            with (
                self.subTest(name=name, value=value),
                mock.patch.dict(
                    os.environ,
                    {
                        **fixture_environment(),
                        "WEF_GROQ_API_KEY": "synthetic-groq-key-0123456789",
                        name: value,
                    },
                    clear=True,
                ),
                self.assertRaisesRegex(ValueError, diagnostic),
            ):
                build.build_values(CONTEXT)

    def test_environment_parser_refuses_malformed_duplicate_and_unsafe_lines(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.env"
            path.write_text("\n # comment\nKEY=a=b\n", encoding="utf-8")
            self.assertEqual(validate.parse_environment(path), {"KEY": "a=b"})
            for raw, diagnostic in (
                ("invalid", "not KEY=VALUE"),
                ("bad-key=value", "invalid or duplicate key"),
                ("KEY=a\nKEY=b", "invalid or duplicate key"),
                ("KEY=", "empty or unsafe value"),
                ("KEY= value", "empty or unsafe value"),
                ("KEY=a\x00b", "empty or unsafe value"),
            ):
                path.write_text(raw, encoding="utf-8")
                with (
                    self.subTest(raw=raw),
                    self.assertRaisesRegex(validate.ReleaseConfigurationError, diagnostic),
                ):
                    validate.parse_environment(path)

    def test_validation_rejects_identity_paths_images_ports_and_credentials(self) -> None:
        values = fixture_values()
        for extra, context, diagnostic in (
            ({}, replace(RELEASE, release_sha="bad"), "40 lowercase"),
            ({"WEF_RELEASE_SHA": "b" * 40}, RELEASE, "SHA does not match"),
            ({"WEF_ROOT": "/other"}, RELEASE, "paths do not match"),
            ({"WEF_RELEASE_DIR": "/other"}, RELEASE, "paths do not match"),
            (
                {"WEF_ROOT": "/other", "WEF_RELEASE_DIR": "/other/releases/" + SHA},
                replace(RELEASE, root=Path("/other"), release_dir=Path("/other/releases") / SHA),
                "production root",
            ),
            (
                {"WEF_RELEASE_DIR": str(ROOT / "other" / SHA)},
                replace(RELEASE, release_dir=ROOT / "other" / SHA),
                "direct child",
            ),
            ({"WEF_PUBLIC_PORT": "3101"}, RELEASE, "public port"),
            ({"WEF_PUBLIC_PORT": "1023"}, replace(RELEASE, public_port=1023), "public port"),
            ({"WEF_PUBLIC_PORT": "65536"}, replace(RELEASE, public_port=65536), "public port"),
            ({"WEF_BIND_ADDRESS": "127.0.0.1"}, RELEASE, "bind address"),
            ({"WEF_BACKEND_IMAGE": "backend:mutable"}, RELEASE, "approved GHCR digests"),
            ({"WEF_WEB_IMAGE": "web:mutable"}, replace(RELEASE, test_mode=True), "test images"),
            ({"WEF_DATABASE_URL": "postgresql://wef@db:5432/wef"}, RELEASE, "internal PostGIS"),
            (
                {"WEF_DATABASE_URL": "postgresql+asyncpg://wef@external:5432/wef"},
                RELEASE,
                "internal PostGIS",
            ),
            ({"WEF_ALLOW_SYNTHETIC_SEED": "maybe"}, RELEASE, "explicit boolean"),
            ({"WEF_GEOAPIFY_API_KEY": "bad key"}, RELEASE, "Geoapify API key"),
            ({"WEF_ADMIN_SESSION_SECRET": "short"}, RELEASE, "admin session secret"),
            ({"WEF_CONTACT_ENCRYPTION_KEY": "bad"}, RELEASE, "encryption key"),
            ({"WEF_CONTACT_HMAC_KEY": "bad"}, RELEASE, "HMAC key"),
            ({"WEF_CONTACT_HMAC_KEY": "a" * 64}, RELEASE, "must be distinct"),
            ({"WEF_TELEGRAM_API_ID": "0"}, RELEASE, "positive integer"),
            ({"WEF_TELEGRAM_API_HASH": "bad"}, RELEASE, "32 hexadecimal"),
            ({"EXTRA": "replace-for-production"}, RELEASE, "placeholder"),
        ):
            with (
                self.subTest(extra=extra, context=context),
                self.assertRaisesRegex(validate.ReleaseConfigurationError, diagnostic),
            ):
                validate.validate_environment({**values, **extra}, context)
        missing = dict(values)
        del missing["POSTGRES_DB"]
        with self.assertRaisesRegex(validate.ReleaseConfigurationError, "missing 1 required"):
            validate.validate_environment(missing, RELEASE)
        validate.validate_environment(
            {
                **values,
                "WEF_BIND_ADDRESS": "127.0.0.1",
                "WEF_BACKEND_IMAGE": "backend:local",
                "WEF_WEB_IMAGE": "web:local",
            },
            replace(RELEASE, test_mode=True),
        )

    def test_cli_build_validate_and_safe_failure_entrypoint(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "production.env"
            args = [str(path), str(ROOT), str(RELEASE.release_dir), SHA, "3100"]
            with (
                mock.patch.dict(os.environ, fixture_environment(), clear=True),
                mock.patch.object(sys, "argv", ["build", *args, "0.0.0.0", BACKEND, WEB]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(build.main(), 0)
                self.assertIn("mode 0600", out.getvalue())
                self.assertNotIn(fixture_environment()["POSTGRES_PASSWORD"], out.getvalue())
            with (
                mock.patch.object(sys, "argv", ["validate", *args]),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(validate.main(), 0)
                self.assertIn("complete and safe", out.getvalue())
            path.write_text("INVALID", encoding="utf-8")
            with (
                mock.patch.object(sys, "argv", ["validate", *args]),
                mock.patch("sys.stderr", new_callable=StringIO) as err,
                self.assertRaises(SystemExit) as error,
            ):
                validate.main()
            self.assertEqual(error.exception.code, 2)
            self.assertIn("not KEY=VALUE", err.getvalue())
            for module in ("build_release_config", "validate_release"):
                completed = subprocess.run(  # noqa: S603 - fixed safe module help entrypoint
                    [sys.executable, "-m", f"scripts.deploy.{module}", "--help"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout)


class CandidateConfigurationBoundaryTests(unittest.TestCase):
    """Canonical layout and loopback configuration have no host side effects."""

    def test_build_input_checks_refuse_unsafe_names_password_and_ports(self) -> None:
        context = sample_context(ROOT)
        for changed, username, password, diagnostic in (
            (
                replace(context, candidate_database="bad-name"),
                POSTGRES_USER,
                POSTGRES_PASSWORD,
                "database name",
            ),
            (context, "bad-name", POSTGRES_PASSWORD, "database username"),
            (context, POSTGRES_USER, "short", "database password"),
            (replace(context, verify_port=1023), POSTGRES_USER, POSTGRES_PASSWORD, "safe range"),
            (replace(context, verify_port=65536), POSTGRES_USER, POSTGRES_PASSWORD, "safe range"),
        ):
            with (
                self.subTest(diagnostic=diagnostic),
                self.assertRaisesRegex(candidate.CandidateConfigurationError, diagnostic),
            ):
                candidate.build_candidate_values(
                    context=changed, postgres_user=username, postgres_password=password
                )

    def test_candidate_identity_database_and_canonical_path_guards(self) -> None:
        context = sample_context(ROOT)
        values = candidate.build_candidate_values(
            context=context, postgres_user=POSTGRES_USER, postgres_password=POSTGRES_PASSWORD
        )
        for extra, changed, diagnostic in (
            ({"WEF_CANDIDATE_BUNDLE_CHECKSUM": "b" * 64}, context, "checksum does not match"),
            ({"WEF_ROOT": "/other"}, context, "root does not match"),
            ({"WEF_MIGRATION_HEAD": "old"}, context, "migration head"),
            (
                {
                    "WEF_ROOT": "/other",
                    "WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH": "/other/candidates/"
                    + BUNDLE_CHECKSUM
                    + "/media/originals",
                    "WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH": "/other/candidates/"
                    + BUNDLE_CHECKSUM
                    + "/media/public",
                },
                replace(context, root=Path("/other"), test_mode=False),
                "production root",
            ),
            (
                {"WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH": "/other"},
                context,
                "restricted originals path",
            ),
            (
                {"WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH": "/other"},
                context,
                "public derivatives path",
            ),
            ({"WEF_CANDIDATE_VERIFY_BIND_ADDRESS": "0.0.0.0"}, context, "loopback only"),
            ({"WEF_CANDIDATE_VERIFY_PORT": "13101"}, context, "verify port does not match"),
            (
                {"WEF_CANDIDATE_DATABASE_URL": "postgresql://user@db:5432/wef_hist_candidate"},
                context,
                "internal PostGIS",
            ),
            (
                {
                    "WEF_CANDIDATE_DATABASE_URL": "postgresql+asyncpg://user@external:5432/wef_hist_candidate"
                },
                context,
                "internal PostGIS",
            ),
            (
                {"WEF_CANDIDATE_DATABASE_URL": "postgresql+asyncpg://user@db:5432/wrong"},
                context,
                "configured candidate database",
            ),
            ({"EXTRA": "change-me"}, context, "placeholder"),
        ):
            with (
                self.subTest(diagnostic=diagnostic),
                self.assertRaisesRegex(candidate.CandidateConfigurationError, diagnostic),
            ):
                candidate.validate_candidate_environment({**values, **extra}, changed)
        missing = dict(values)
        del missing["POSTGRES_USER"]
        with self.assertRaisesRegex(candidate.CandidateConfigurationError, "missing 1 required"):
            candidate.validate_candidate_environment(missing, context)
        candidate.validate_candidate_environment(values, replace(context, test_mode=False))

    def test_relative_root_and_containment_boundary(self) -> None:
        paths = candidate.candidate_paths(Path("fixture-relative-root"), BUNDLE_CHECKSUM)
        self.assertEqual(paths.root, Path("fixture-relative-root").resolve())
        for path in (ROOT, ROOT.parent / "outside"):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(candidate.CandidateConfigurationError, "stay beneath"),
            ):
                candidate._validate_containment(path, ROOT)  # noqa: SLF001 - direct containment guard contract
        self.assertEqual(candidate.candidate_paths(Path("/"), BUNDLE_CHECKSUM).root, Path("/"))

    def test_candidate_cli_writes_private_config_and_real_help(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "candidate.env"
            with (
                mock.patch.dict(
                    os.environ,
                    {"POSTGRES_USER": POSTGRES_USER, "POSTGRES_PASSWORD": POSTGRES_PASSWORD},
                    clear=True,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "candidate",
                        str(output),
                        str(root),
                        BUNDLE_CHECKSUM,
                        "wef_hist_candidate",
                        BACKEND,
                        WEB,
                        "--test-mode",
                        "--verify-port",
                        "14100",
                    ],
                ),
                mock.patch("sys.stdout", new_callable=StringIO) as out,
            ):
                self.assertEqual(candidate_cli.main(), 0)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            values = validate.parse_environment(output)
            self.assertEqual(values["WEF_CANDIDATE_VERIFY_PORT"], "14100")
            self.assertEqual(values["WEF_CANDIDATE_VERIFY_BIND_ADDRESS"], "127.0.0.1")
            self.assertNotIn(POSTGRES_PASSWORD, out.getvalue())
            completed = subprocess.run(
                [sys.executable, "-m", "scripts.deploy.build_candidate_config", "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("--test-mode", completed.stdout)


if __name__ == "__main__":
    unittest.main()
