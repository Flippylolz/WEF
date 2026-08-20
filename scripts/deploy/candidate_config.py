"""Candidate release configuration for non-public historical verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from scripts.transfer.constants import MIGRATION_HEAD

CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DATABASE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9_.~!%^*+:/=,?-]{24,128}$")
FORBIDDEN_VALUE_FRAGMENTS = ("change-me", "changeme", "local-only", "replace-for")
MIN_VERIFY_PORT = 1024
MAX_VERIFY_PORT = 65535
DEFAULT_VERIFY_PORT = 13100
CANDIDATE_REQUIRED_KEYS = frozenset(
    {
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "WEF_BACKEND_IMAGE",
        "WEF_CANDIDATE_BUNDLE_CHECKSUM",
        "WEF_CANDIDATE_DATABASE_URL",
        "WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH",
        "WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH",
        "WEF_CANDIDATE_VERIFY_BIND_ADDRESS",
        "WEF_CANDIDATE_VERIFY_PORT",
        "WEF_MIGRATION_HEAD",
        "WEF_ROOT",
        "WEF_WEB_IMAGE",
    },
)


class CandidateConfigurationError(ValueError):
    """Raised for an unsafe or incomplete candidate environment."""


@dataclass(frozen=True, slots=True)
class CandidatePaths:
    """Checksum-scoped candidate media roots beneath one WEF root."""

    root: Path
    bundle_checksum: str
    restricted_originals: Path
    public_derivatives: Path


@dataclass(frozen=True, slots=True)
class CandidateContext:
    """Non-secret inputs for one candidate verification release."""

    root: Path
    bundle_checksum: str
    candidate_database: str
    backend_image: str
    web_image: str
    verify_port: int = DEFAULT_VERIFY_PORT
    test_mode: bool = False


def candidate_paths(root: Path, bundle_checksum: str) -> CandidatePaths:
    """Return the canonical checksum-scoped candidate media roots."""
    _validate_bundle_checksum(bundle_checksum)
    resolved = root.resolve()
    candidate_root = resolved / "candidates" / bundle_checksum
    return CandidatePaths(
        root=resolved,
        bundle_checksum=bundle_checksum,
        restricted_originals=candidate_root / "media" / "originals",
        public_derivatives=candidate_root / "media" / "public",
    )


def build_candidate_values(
    *,
    context: CandidateContext,
    postgres_user: str,
    postgres_password: str,
) -> dict[str, str]:
    """Construct and validate one complete candidate verification environment."""
    _validate_bundle_checksum(context.bundle_checksum)
    if not DATABASE_IDENTIFIER.fullmatch(context.candidate_database):
        msg = "candidate database name must use a safe PostgreSQL identifier"
        raise CandidateConfigurationError(msg)
    if not DATABASE_IDENTIFIER.fullmatch(postgres_user):
        msg = "database username must use a safe PostgreSQL identifier"
        raise CandidateConfigurationError(msg)
    if not SAFE_PASSWORD.fullmatch(postgres_password):
        msg = "database password is not safe for a Compose environment file"
        raise CandidateConfigurationError(msg)
    if not MIN_VERIFY_PORT <= context.verify_port <= MAX_VERIFY_PORT:
        msg = "candidate verify port is outside the safe range"
        raise CandidateConfigurationError(msg)

    paths = candidate_paths(context.root, context.bundle_checksum)
    encoded_username = quote(postgres_user, safe="")
    encoded_password = quote(postgres_password, safe="")
    encoded_database = quote(context.candidate_database, safe="")
    values = {
        "POSTGRES_PASSWORD": postgres_password,
        "POSTGRES_USER": postgres_user,
        "WEF_BACKEND_IMAGE": context.backend_image,
        "WEF_CANDIDATE_BUNDLE_CHECKSUM": context.bundle_checksum,
        "WEF_CANDIDATE_DATABASE_URL": (
            f"postgresql+asyncpg://{encoded_username}:{encoded_password}@db:5432/{encoded_database}"
        ),
        "WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH": str(paths.public_derivatives),
        "WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH": str(paths.restricted_originals),
        "WEF_CANDIDATE_VERIFY_BIND_ADDRESS": "127.0.0.1",
        "WEF_CANDIDATE_VERIFY_PORT": str(context.verify_port),
        "WEF_MIGRATION_HEAD": MIGRATION_HEAD,
        "WEF_ROOT": str(context.root),
        "WEF_WEB_IMAGE": context.web_image,
    }
    validate_candidate_environment(values, context)
    return values


def validate_candidate_environment(
    values: dict[str, str],
    context: CandidateContext,
) -> None:
    """Validate candidate identity, containment, and loopback-only boundaries."""
    _validate_required_keys(values)
    _validate_identity(values, context)
    _validate_paths_and_bind(values, context)
    _validate_database_url(values, context)


def _validate_required_keys(values: dict[str, str]) -> None:
    missing = CANDIDATE_REQUIRED_KEYS.difference(values)
    if missing:
        msg = f"candidate configuration is missing {len(missing)} required value(s)"
        raise CandidateConfigurationError(msg)
    if any(
        fragment in value.lower()
        for value in values.values()
        for fragment in FORBIDDEN_VALUE_FRAGMENTS
    ):
        msg = "candidate configuration contains a placeholder value"
        raise CandidateConfigurationError(msg)


def _validate_identity(values: dict[str, str], context: CandidateContext) -> None:
    _validate_bundle_checksum(values["WEF_CANDIDATE_BUNDLE_CHECKSUM"])
    if values["WEF_CANDIDATE_BUNDLE_CHECKSUM"] != context.bundle_checksum:
        msg = "candidate bundle checksum does not match deployment context"
        raise CandidateConfigurationError(msg)
    if values["WEF_ROOT"] != str(context.root):
        msg = "candidate root does not match deployment context"
        raise CandidateConfigurationError(msg)
    if values["WEF_MIGRATION_HEAD"] != MIGRATION_HEAD:
        msg = "candidate migration head does not match the released bundle head"
        raise CandidateConfigurationError(msg)
    if not context.test_mode and context.root != Path("/home/nuc/wef"):
        msg = "production root must be /home/nuc/wef"
        raise CandidateConfigurationError(msg)


def _validate_paths_and_bind(
    values: dict[str, str],
    context: CandidateContext,
) -> None:
    expected_paths = candidate_paths(context.root, context.bundle_checksum)
    if values["WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH"] != str(
        expected_paths.restricted_originals,
    ):
        msg = "restricted originals path must use the canonical candidate layout"
        raise CandidateConfigurationError(msg)
    if values["WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH"] != str(
        expected_paths.public_derivatives,
    ):
        msg = "public derivatives path must use the canonical candidate layout"
        raise CandidateConfigurationError(msg)
    if values["WEF_CANDIDATE_VERIFY_BIND_ADDRESS"] != "127.0.0.1":
        msg = "candidate verification must bind to loopback only"
        raise CandidateConfigurationError(msg)
    if values["WEF_CANDIDATE_VERIFY_PORT"] != str(context.verify_port):
        msg = "candidate verify port does not match deployment context"
        raise CandidateConfigurationError(msg)
    _validate_containment(
        Path(values["WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH"]),
        context.root,
    )
    _validate_containment(
        Path(values["WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH"]),
        context.root,
    )


def _validate_database_url(values: dict[str, str], context: CandidateContext) -> None:
    database_url = values["WEF_CANDIDATE_DATABASE_URL"]
    if not database_url.startswith("postgresql+asyncpg://") or "@db:5432/" not in database_url:
        msg = "candidate database URL must target the internal PostGIS service"
        raise CandidateConfigurationError(msg)
    if not database_url.endswith(f"/{context.candidate_database}"):
        msg = "candidate database URL must target the configured candidate database"
        raise CandidateConfigurationError(msg)


def _validate_bundle_checksum(value: str) -> None:
    if not CHECKSUM_PATTERN.fullmatch(value):
        msg = "bundle checksum must be 64 lowercase hexadecimal characters"
        raise CandidateConfigurationError(msg)


def _validate_containment(path: Path, root: Path) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved == root_resolved or root_resolved not in resolved.parents:
        msg = "candidate path must stay beneath the WEF root"
        raise CandidateConfigurationError(msg)
