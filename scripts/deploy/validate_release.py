"""Validate a complete production release environment without printing values."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
DIGEST_IMAGE_PATTERN = re.compile(
    r"^ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+-(?:backend|web)"
    r"@sha256:[0-9a-f]{64}$",
)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PROVIDER_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]{20,200}$")
ADMIN_SESSION_SECRET_PATTERN = re.compile(r"^[A-Za-z0-9._-]{32,200}$")
CONTACT_KEY_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
FORBIDDEN_VALUE_FRAGMENTS = ("change-me", "changeme", "local-only", "replace-for", "dev-only")
MIN_PUBLIC_PORT = 1024
MAX_PUBLIC_PORT = 65535
REQUIRED_KEYS = frozenset(
    {
        "POSTGRES_DB",
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "WEF_ADMIN_SESSION_SECRET",
        "WEF_ALLOW_SYNTHETIC_SEED",
        "WEF_BACKEND_IMAGE",
        "WEF_BIND_ADDRESS",
        "WEF_CONTACT_ENCRYPTION_KEY",
        "WEF_CONTACT_HMAC_KEY",
        "WEF_DATABASE_URL",
        "WEF_GEOAPIFY_API_KEY",
        "WEF_LOG_LEVEL",
        "WEF_PUBLIC_PORT",
        "WEF_RELEASE_DIR",
        "WEF_RELEASE_SHA",
        "WEF_ROOT",
        "WEF_WEB_IMAGE",
    },
)


class ReleaseConfigurationError(ValueError):
    """Raised for an unsafe or incomplete release environment."""


@dataclass(frozen=True, slots=True)
class ReleaseContext:
    """Non-secret deployment context supplied outside the env file."""

    root: Path
    release_dir: Path
    release_sha: str
    public_port: int
    test_mode: bool = False


def parse_environment(path: Path) -> dict[str, str]:
    """Parse the deliberately restricted deployment env-file format."""
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            msg = f"line {line_number} is not KEY=VALUE"
            raise ReleaseConfigurationError(msg)
        key, value = line.split("=", maxsplit=1)
        if not KEY_PATTERN.fullmatch(key) or key in values:
            msg = f"line {line_number} has an invalid or duplicate key"
            raise ReleaseConfigurationError(msg)
        if not value or "\x00" in value or value != value.strip():
            msg = f"line {line_number} has an empty or unsafe value"
            raise ReleaseConfigurationError(msg)
        values[key] = value
    return values


def validate_environment(
    values: dict[str, str],
    context: ReleaseContext,
) -> None:
    """Validate release identity, paths, images, database, and rehearsal gates."""
    missing = REQUIRED_KEYS.difference(values)
    if missing:
        msg = f"release configuration is missing {len(missing)} required value(s)"
        raise ReleaseConfigurationError(msg)

    if any(
        fragment in value.lower()
        for value in values.values()
        for fragment in FORBIDDEN_VALUE_FRAGMENTS
    ):
        msg = "release configuration contains a placeholder value"
        raise ReleaseConfigurationError(msg)

    _validate_identity_and_paths(values, context)
    _validate_runtime_boundaries(values, context)


def _validate_identity_and_paths(
    values: dict[str, str],
    context: ReleaseContext,
) -> None:
    """Validate source identity and containment beneath the WEF root."""
    if not SHA_PATTERN.fullmatch(context.release_sha):
        msg = "release SHA must be 40 lowercase hexadecimal characters"
        raise ReleaseConfigurationError(msg)
    if values["WEF_RELEASE_SHA"] != context.release_sha:
        msg = "release SHA does not match deployment context"
        raise ReleaseConfigurationError(msg)

    if values["WEF_ROOT"] != str(context.root) or values["WEF_RELEASE_DIR"] != str(
        context.release_dir
    ):
        msg = "release paths do not match deployment context"
        raise ReleaseConfigurationError(msg)
    if not context.test_mode and context.root != Path("/home/nuc/wef"):
        msg = "production root must be /home/nuc/wef"
        raise ReleaseConfigurationError(msg)
    if context.release_dir.parent != context.root / "releases":
        msg = "release directory must be a direct child of the release root"
        raise ReleaseConfigurationError(msg)


def _validate_runtime_boundaries(
    values: dict[str, str],
    context: ReleaseContext,
) -> None:
    """Validate port, image, database, and synthetic rehearsal boundaries."""
    if (
        values["WEF_PUBLIC_PORT"] != str(context.public_port)
        or not MIN_PUBLIC_PORT <= context.public_port <= MAX_PUBLIC_PORT
    ):
        msg = "public port does not match the safe deployment context"
        raise ReleaseConfigurationError(msg)
    allowed_bind_addresses = {"0.0.0.0"}  # noqa: S104 - deliberate public edge
    if context.test_mode:
        allowed_bind_addresses.add("127.0.0.1")
    if values["WEF_BIND_ADDRESS"] not in allowed_bind_addresses:
        msg = "public bind address is not allowed"
        raise ReleaseConfigurationError(msg)

    images = (values["WEF_BACKEND_IMAGE"], values["WEF_WEB_IMAGE"])
    if not context.test_mode and any(not DIGEST_IMAGE_PATTERN.fullmatch(image) for image in images):
        msg = "application images must be approved GHCR digests"
        raise ReleaseConfigurationError(msg)
    if context.test_mode and any(
        "@" not in image and not image.endswith(":local") for image in images
    ):
        msg = "test images must be local tags or immutable digests"
        raise ReleaseConfigurationError(msg)

    database_url = values["WEF_DATABASE_URL"]
    if not database_url.startswith("postgresql+asyncpg://") or "@db:5432/" not in database_url:
        msg = "database URL must target the internal PostGIS service"
        raise ReleaseConfigurationError(msg)
    if values["WEF_ALLOW_SYNTHETIC_SEED"] not in {"true", "false"}:
        msg = "synthetic seed gate must be an explicit boolean"
        raise ReleaseConfigurationError(msg)
    if not PROVIDER_KEY_PATTERN.fullmatch(values["WEF_GEOAPIFY_API_KEY"]):
        msg = "Geoapify API key has an unsafe release format"
        raise ReleaseConfigurationError(msg)
    if not ADMIN_SESSION_SECRET_PATTERN.fullmatch(values["WEF_ADMIN_SESSION_SECRET"]):
        msg = "admin session secret has an unsafe release format"
        raise ReleaseConfigurationError(msg)
    _validate_contact_keys(values)


def _validate_contact_keys(values: dict[str, str]) -> None:
    """Require distinct 32-byte hex contact encryption and HMAC keys."""
    encryption_key = values["WEF_CONTACT_ENCRYPTION_KEY"]
    hmac_key = values["WEF_CONTACT_HMAC_KEY"]
    if not CONTACT_KEY_PATTERN.fullmatch(encryption_key):
        msg = "contact encryption key must be 32-byte hex"
        raise ReleaseConfigurationError(msg)
    if not CONTACT_KEY_PATTERN.fullmatch(hmac_key):
        msg = "contact HMAC key must be 32-byte hex"
        raise ReleaseConfigurationError(msg)
    if encryption_key == hmac_key:
        msg = "contact encryption and HMAC keys must be distinct"
        raise ReleaseConfigurationError(msg)


def main() -> int:
    """Validate one release environment and report only bounded status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("release_sha")
    parser.add_argument("public_port", type=int)
    parser.add_argument("--test-mode", action="store_true")
    arguments = parser.parse_args()

    try:
        values = parse_environment(arguments.config)
        validate_environment(
            values,
            ReleaseContext(
                root=arguments.root,
                release_dir=arguments.release_dir,
                release_sha=arguments.release_sha,
                public_port=arguments.public_port,
                test_mode=arguments.test_mode,
            ),
        )
    except (OSError, ReleaseConfigurationError) as error:
        parser.error(str(error))
    print("Release configuration is complete and safe.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
