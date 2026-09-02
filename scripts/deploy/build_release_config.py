"""Build a complete mode-0600 production environment from CI inputs."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from scripts.deploy.validate_release import (
    ReleaseContext,
    validate_environment,
)

DATABASE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9_.~!%^*+:/=,?-]{24,128}$")
SAFE_PROVIDER_KEY = re.compile(r"^[A-Za-z0-9._-]{20,200}$")
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
CONTACT_KEY_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
TELEGRAM_API_ID_PATTERN = re.compile(r"^[1-9][0-9]{4,15}$")
TELEGRAM_API_HASH_PATTERN = re.compile(r"^[A-Fa-f0-9]{32}$")
MIN_BOOTSTRAP_USERNAME_LENGTH = 3
MIN_BOOTSTRAP_PASSWORD_LENGTH = 10
MIN_GROQ_BATCH_CHUNK_SIZE = 1
MAX_GROQ_BATCH_CHUNK_SIZE = 100
MIN_GROQ_BATCH_POLL_INTERVAL_SECONDS = 0.5
MAX_GROQ_BATCH_POLL_INTERVAL_SECONDS = 60.0
MIN_GROQ_BATCH_MAX_WAIT_SECONDS = 30
MAX_GROQ_BATCH_MAX_WAIT_SECONDS = 86400


@dataclass(frozen=True, slots=True)
class ConfigBuildContext:
    """Non-secret release values supplied by the deployment workflow."""

    release: ReleaseContext
    bind_address: str
    backend_image: str
    web_image: str


def required_environment(name: str) -> str:
    """Read one required CI value without displaying it."""
    value = os.environ.get(name)
    if value is None or not value:
        msg = f"required environment value is missing: {name}"
        raise ValueError(msg)
    return value


def _optional_env(name: str, default: str) -> str:
    """Read one optional CI value, treating blank as the default."""
    value = os.environ.get(name, default).strip()
    return value or default


def _require_contact_keys() -> tuple[str, str]:
    """Require distinct 32-byte hex contact crypto keys."""
    contact_encryption_key = required_environment("WEF_CONTACT_ENCRYPTION_KEY")
    contact_hmac_key = required_environment("WEF_CONTACT_HMAC_KEY")
    if not CONTACT_KEY_PATTERN.fullmatch(contact_encryption_key):
        msg = "contact encryption key must be 32-byte hex"
        raise ValueError(msg)
    if not CONTACT_KEY_PATTERN.fullmatch(contact_hmac_key):
        msg = "contact HMAC key must be 32-byte hex"
        raise ValueError(msg)
    if contact_encryption_key == contact_hmac_key:
        msg = "contact encryption and HMAC keys must be distinct"
        raise ValueError(msg)
    return contact_encryption_key, contact_hmac_key


def _require_telegram_credentials() -> tuple[str, str, str | None, str | None]:
    """Require API id/hash; session and phone are optional until first login."""
    api_id = required_environment("WEF_TELEGRAM_API_ID")
    api_hash = required_environment("WEF_TELEGRAM_API_HASH")
    if not TELEGRAM_API_ID_PATTERN.fullmatch(api_id):
        msg = "Telegram api_id must be a positive integer"
        raise ValueError(msg)
    if not TELEGRAM_API_HASH_PATTERN.fullmatch(api_hash):
        msg = "Telegram api_hash must be 32 hexadecimal characters"
        raise ValueError(msg)
    session = os.environ.get("WEF_TELEGRAM_SESSION", "").strip() or None
    phone = os.environ.get("WEF_TELEGRAM_PHONE", "").strip() or None
    return api_id, api_hash, session, phone


def _optional_bootstrap_owner(values: dict[str, str]) -> None:
    """Attach paired bootstrap owner credentials when both are present."""
    bootstrap_username = os.environ.get("WEF_BOOTSTRAP_OWNER_USERNAME", "").strip()
    bootstrap_password = os.environ.get("WEF_BOOTSTRAP_OWNER_PASSWORD", "").strip()
    if not bootstrap_username and not bootstrap_password:
        return
    if not bootstrap_username or not bootstrap_password:
        msg = "bootstrap owner username and password must both be set or both omitted"
        raise ValueError(msg)
    if (
        len(bootstrap_username) < MIN_BOOTSTRAP_USERNAME_LENGTH
        or len(bootstrap_password) < MIN_BOOTSTRAP_PASSWORD_LENGTH
    ):
        msg = "bootstrap owner credentials do not meet minimum length"
        raise ValueError(msg)
    values["WEF_BOOTSTRAP_OWNER_USERNAME"] = bootstrap_username
    values["WEF_BOOTSTRAP_OWNER_PASSWORD"] = bootstrap_password


def _groq_batch_settings_from_environment() -> dict[str, str]:
    """Read and validate optional Groq Batch API tuning from CI inputs."""
    use_batch_api = _optional_env("WEF_GROQ_USE_BATCH_API", "true").lower()
    if use_batch_api not in {"true", "false"}:
        msg = "Groq batch API flag must be true or false"
        raise ValueError(msg)
    chunk_size = _optional_env("WEF_GROQ_BATCH_CHUNK_SIZE", "20")
    if (
        not chunk_size.isdigit()
        or not MIN_GROQ_BATCH_CHUNK_SIZE <= int(chunk_size) <= MAX_GROQ_BATCH_CHUNK_SIZE
    ):
        msg = "Groq batch chunk size must be an integer from 1 to 100"
        raise ValueError(msg)
    poll_interval = _optional_env("WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS", "2")
    try:
        poll_seconds = float(poll_interval)
    except ValueError as error:
        msg = "Groq batch poll interval must be a number"
        raise ValueError(msg) from error
    if (
        not MIN_GROQ_BATCH_POLL_INTERVAL_SECONDS
        <= poll_seconds
        <= MAX_GROQ_BATCH_POLL_INTERVAL_SECONDS
    ):
        msg = "Groq batch poll interval must be from 0.5 to 60 seconds"
        raise ValueError(msg)
    max_wait = _optional_env("WEF_GROQ_BATCH_MAX_WAIT_SECONDS", "3600")
    if (
        not max_wait.isdigit()
        or not MIN_GROQ_BATCH_MAX_WAIT_SECONDS <= int(max_wait) <= MAX_GROQ_BATCH_MAX_WAIT_SECONDS
    ):
        msg = "Groq batch max wait must be an integer from 30 to 86400"
        raise ValueError(msg)
    return {
        "WEF_GROQ_USE_BATCH_API": use_batch_api,
        "WEF_GROQ_BATCH_CHUNK_SIZE": chunk_size,
        "WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS": poll_interval,
        "WEF_GROQ_BATCH_MAX_WAIT_SECONDS": max_wait,
    }


def _optional_groq_curation(values: dict[str, str]) -> None:
    """Attach optional Groq AI curation settings when a key is present.

    Absence keeps AI off and must not fail deploy. Activation still requires
    WEF_AI_CURATION_ENABLED=true and WEF_GROQ_ZDR_VERIFIED=true at runtime.
    """
    groq_api_key = os.environ.get("WEF_GROQ_API_KEY", "").strip()
    if not groq_api_key:
        return
    if not SAFE_PROVIDER_KEY.fullmatch(groq_api_key):
        msg = "Groq API key is not safe for a Compose environment file"
        raise ValueError(msg)
    model = os.environ.get("WEF_GROQ_MODEL", "openai/gpt-oss-20b").strip()
    if model != "openai/gpt-oss-20b":
        msg = "Groq model must be exactly openai/gpt-oss-20b"
        raise ValueError(msg)
    enabled = os.environ.get("WEF_AI_CURATION_ENABLED", "false").strip().lower()
    zdr = os.environ.get("WEF_GROQ_ZDR_VERIFIED", "false").strip().lower()
    if enabled not in {"true", "false"} or zdr not in {"true", "false"}:
        msg = "Groq enablement flags must be true or false"
        raise ValueError(msg)
    timeout = os.environ.get("WEF_GROQ_TIMEOUT_SECONDS", "30").strip()
    if not re.fullmatch(r"(?:[1-9]|[1-9][0-9]|1[01][0-9]|120)", timeout):
        msg = "Groq timeout must be an integer from 1 to 120"
        raise ValueError(msg)
    values["WEF_GROQ_API_KEY"] = groq_api_key
    values["WEF_GROQ_MODEL"] = model
    values["WEF_AI_CURATION_ENABLED"] = enabled
    values["WEF_GROQ_ZDR_VERIFIED"] = zdr
    values["WEF_GROQ_TIMEOUT_SECONDS"] = timeout
    values.update(_groq_batch_settings_from_environment())


def build_values(
    context: ConfigBuildContext,
) -> dict[str, str]:
    """Construct and validate the complete production service environment."""
    database = required_environment("POSTGRES_DB")
    username = required_environment("POSTGRES_USER")
    password = required_environment("POSTGRES_PASSWORD")
    geoapify_api_key = required_environment("WEF_GEOAPIFY_API_KEY")
    admin_session_secret = required_environment("WEF_ADMIN_SESSION_SECRET")
    contact_encryption_key, contact_hmac_key = _require_contact_keys()
    telegram_api_id, telegram_api_hash, telegram_session, telegram_phone = (
        _require_telegram_credentials()
    )
    if not DATABASE_IDENTIFIER.fullmatch(database) or not DATABASE_IDENTIFIER.fullmatch(
        username,
    ):
        msg = "database name and username must use safe PostgreSQL identifiers"
        raise ValueError(msg)
    if not SAFE_PASSWORD.fullmatch(password):
        msg = "database password is not safe for a Compose environment file"
        raise ValueError(msg)
    if not SAFE_PROVIDER_KEY.fullmatch(geoapify_api_key):
        msg = "Geoapify API key is not safe for a Compose environment file"
        raise ValueError(msg)
    if not re.fullmatch(r"^[A-Za-z0-9._-]{32,200}$", admin_session_secret):
        msg = "admin session secret is not safe for a Compose environment file"
        raise ValueError(msg)
    log_level = required_environment("WEF_LOG_LEVEL").upper()
    if log_level not in ALLOWED_LOG_LEVELS:
        msg = "log level is not supported"
        raise ValueError(msg)

    encoded_username = quote(username, safe="")
    encoded_password = quote(password, safe="")
    encoded_database = quote(database, safe="")
    values = {
        "POSTGRES_DB": database,
        "POSTGRES_PASSWORD": password,
        "POSTGRES_USER": username,
        "WEF_ADMIN_SESSION_SECRET": admin_session_secret,
        "WEF_ALLOW_SYNTHETIC_SEED": required_environment(
            "WEF_ALLOW_SYNTHETIC_SEED",
        ),
        "WEF_BACKEND_IMAGE": context.backend_image,
        "WEF_BIND_ADDRESS": context.bind_address,
        "WEF_CONTACT_ENCRYPTION_KEY": contact_encryption_key,
        "WEF_CONTACT_HMAC_KEY": contact_hmac_key,
        "WEF_DATABASE_URL": (
            f"postgresql+asyncpg://{encoded_username}:{encoded_password}@db:5432/{encoded_database}"
        ),
        "WEF_GEOAPIFY_API_KEY": geoapify_api_key,
        "WEF_LOG_LEVEL": log_level,
        "WEF_PUBLIC_PORT": str(context.release.public_port),
        "WEF_RELEASE_DIR": str(context.release.release_dir),
        "WEF_RELEASE_SHA": context.release.release_sha,
        "WEF_ROOT": str(context.release.root),
        "WEF_TELEGRAM_API_HASH": telegram_api_hash,
        "WEF_TELEGRAM_API_ID": telegram_api_id,
        "WEF_WEB_IMAGE": context.web_image,
    }
    _optional_bootstrap_owner(values)
    _optional_groq_curation(values)
    if telegram_session is not None:
        values["WEF_TELEGRAM_SESSION"] = telegram_session
    if telegram_phone is not None:
        values["WEF_TELEGRAM_PHONE"] = telegram_phone
    validate_environment(values, context.release)
    return values


def write_environment(path: Path, values: dict[str, str]) -> None:
    """Create one non-overwriting mode-0600 env file."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        for key, value in sorted(values.items()):
            stream.write(f"{key}={value}\n")


def main() -> int:
    """Build one complete release configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("release_sha")
    parser.add_argument("public_port", type=int)
    parser.add_argument("bind_address")
    parser.add_argument("backend_image")
    parser.add_argument("web_image")
    arguments = parser.parse_args()

    values = build_values(
        ConfigBuildContext(
            release=ReleaseContext(
                root=arguments.root,
                release_dir=arguments.release_dir,
                release_sha=arguments.release_sha,
                public_port=arguments.public_port,
            ),
            bind_address=arguments.bind_address,
            backend_image=arguments.backend_image,
            web_image=arguments.web_image,
        ),
    )
    write_environment(arguments.output, values)
    print("Complete production configuration created with mode 0600.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
