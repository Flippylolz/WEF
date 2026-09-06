"""Release environment round-trip, defaults and secret-file permission proof."""

from __future__ import annotations

# Executable proof assertions and bounded result output are intentional.
# ruff: noqa: S101
import os
import tempfile
from pathlib import Path

from scripts.deploy.build_release_config import (
    ConfigBuildContext,
    build_values,
    write_environment,
)
from scripts.deploy.validate_release import ReleaseContext

_PRIVATE_ENV_MODE = 0o600

RELEASE_SHA = "a" * 40
BACKEND_DIGEST = f"sha256:{'b' * 64}"
WEB_DIGEST = f"sha256:{'c' * 64}"


def _build_fixture_values(extra_environment: dict[str, str]) -> dict[str, str]:
    """Build one validated release environment from fixture inputs."""
    previous = {key: os.environ.get(key) for key in extra_environment}
    os.environ.update(extra_environment)
    try:
        return build_values(
            ConfigBuildContext(
                release=ReleaseContext(
                    root=Path("/home/nuc/wef"),
                    release_dir=Path(f"/home/nuc/wef/releases/{RELEASE_SHA}"),
                    release_sha=RELEASE_SHA,
                    public_port=3100,
                ),
                bind_address="0.0.0.0",  # noqa: S104 - inert config fixture; never binds
                backend_image=f"ghcr.io/flippylolz/wef-backend@{BACKEND_DIGEST}",
                web_image=f"ghcr.io/flippylolz/wef-web@{WEB_DIGEST}",
            ),
        )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _assert_blank_groq_batch_defaults(groq_environment: dict[str, str]) -> None:
    """Prove unset GitHub batch vars fall back to code defaults."""
    with_blank_batch = _build_fixture_values(
        {
            **groq_environment,
            "WEF_GROQ_USE_BATCH_API": "false",
            "WEF_GROQ_BATCH_CHUNK_SIZE": "",
            "WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS": "",
            "WEF_GROQ_BATCH_MAX_WAIT_SECONDS": "",
        },
    )
    assert with_blank_batch["WEF_GROQ_USE_BATCH_API"] == "false"
    assert with_blank_batch["WEF_GROQ_BATCH_CHUNK_SIZE"] == "2"
    assert with_blank_batch["WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS"] == "2"
    assert with_blank_batch["WEF_GROQ_BATCH_MAX_WAIT_SECONDS"] == "3600"


def assert_release_configuration() -> None:
    """Prove complete validation and mode-0600 secret material."""
    environment = {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "safe:/password-0123456789abcdef",
        "POSTGRES_USER": "wef",
        "WEF_ADMIN_SESSION_SECRET": "fixture-admin-session-secret-0123456789abcdef",
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
        "WEF_CONTACT_ENCRYPTION_KEY": "0123456789abcdef" * 4,
        "WEF_CONTACT_HMAC_KEY": "fedcba9876543210" * 4,
        "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
        "WEF_LOG_LEVEL": "INFO",
        "WEF_TELEGRAM_API_HASH": "0123456789abcdef0123456789abcdef",
        "WEF_TELEGRAM_API_ID": "12345678",
    }
    values = _build_fixture_values(environment)

    assert "safe%3A%2Fpassword-0123456789abcdef" in values["WEF_DATABASE_URL"]
    assert values["WEF_GEOAPIFY_API_KEY"] == "fixture-geoapify-key-0123456789"
    assert "WEF_GROQ_API_KEY" not in values

    groq_environment = {
        **environment,
        "WEF_GROQ_API_KEY": "gsk_fixture-groq-key-0123456789abcdef",
        "WEF_AI_CURATION_ENABLED": "false",
        "WEF_GROQ_MODEL": "openai/gpt-oss-20b",
        "WEF_GROQ_ZDR_VERIFIED": "false",
        "WEF_GROQ_TIMEOUT_SECONDS": "30",
    }
    with_groq = _build_fixture_values(groq_environment)
    assert with_groq["WEF_GROQ_API_KEY"].startswith("gsk_fixture")
    assert with_groq["WEF_AI_CURATION_ENABLED"] == "false"
    assert with_groq["WEF_GROQ_ZDR_VERIFIED"] == "false"
    assert with_groq["WEF_GROQ_USE_BATCH_API"] == "true"
    assert with_groq["WEF_GROQ_BATCH_CHUNK_SIZE"] == "20"
    _assert_blank_groq_batch_defaults(groq_environment)
    recovery_flags = (
        "WEF_AI_RECOVERY_ENABLED",
        "WEF_AI_RECOVERY_ACTIVATION_VERIFIED",
        "WEF_AI_RECOVERY_AUTO_APPLY",
    )
    assert all(with_groq[name] == "false" for name in recovery_flags)
    enabled = _build_fixture_values(
        {
            **groq_environment,
            **dict.fromkeys(recovery_flags, "true"),
            "WEF_AI_RECOVERY_OWNER_ID": "12345678-1234-1234-1234-123456789abc",
        }
    )
    assert all(enabled[name] == "true" for name in recovery_flags)
    assert enabled["WEF_AI_RECOVERY_OWNER_ID"] == "12345678-1234-1234-1234-123456789abc"
    for name, value in (
        ("WEF_AI_RECOVERY_ENABLED", "maybe"),
        ("WEF_AI_RECOVERY_OWNER_ID", "not-a-uuid"),
    ):
        try:
            _build_fixture_values({**groq_environment, name: value})
        except ValueError:
            pass
        else:
            message = f"Invalid recovery configuration accepted: {name}"
            raise AssertionError(message)

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "production.env"
        write_environment(path, values)
        assert path.stat().st_mode & 0o777 == _PRIVATE_ENV_MODE
        assert "POSTGRES_PASSWORD=safe:/password-0123456789abcdef" in path.read_text(
            encoding="utf-8",
        )
