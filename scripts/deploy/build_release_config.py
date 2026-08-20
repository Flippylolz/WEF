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


def build_values(
    context: ConfigBuildContext,
) -> dict[str, str]:
    """Construct and validate the complete production service environment."""
    database = required_environment("POSTGRES_DB")
    username = required_environment("POSTGRES_USER")
    password = required_environment("POSTGRES_PASSWORD")
    geoapify_api_key = required_environment("WEF_GEOAPIFY_API_KEY")
    admin_session_secret = required_environment("WEF_ADMIN_SESSION_SECRET")
    contact_encryption_key = required_environment("WEF_CONTACT_ENCRYPTION_KEY")
    contact_hmac_key = required_environment("WEF_CONTACT_HMAC_KEY")
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
    if not re.fullmatch(r"^[A-Fa-f0-9]{64}$", contact_encryption_key):
        msg = "contact encryption key must be 32-byte hex"
        raise ValueError(msg)
    if not re.fullmatch(r"^[A-Fa-f0-9]{64}$", contact_hmac_key):
        msg = "contact HMAC key must be 32-byte hex"
        raise ValueError(msg)
    if contact_encryption_key == contact_hmac_key:
        msg = "contact encryption and HMAC keys must be distinct"
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
        "WEF_WEB_IMAGE": context.web_image,
    }
    bootstrap_username = os.environ.get("WEF_BOOTSTRAP_OWNER_USERNAME", "").strip()
    bootstrap_password = os.environ.get("WEF_BOOTSTRAP_OWNER_PASSWORD", "").strip()
    if bootstrap_username or bootstrap_password:
        if not bootstrap_username or not bootstrap_password:
            msg = "bootstrap owner username and password must both be set or both omitted"
            raise ValueError(msg)
        if len(bootstrap_username) < 3 or len(bootstrap_password) < 10:
            msg = "bootstrap owner credentials do not meet minimum length"
            raise ValueError(msg)
        values["WEF_BOOTSTRAP_OWNER_USERNAME"] = bootstrap_username
        values["WEF_BOOTSTRAP_OWNER_PASSWORD"] = bootstrap_password
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
