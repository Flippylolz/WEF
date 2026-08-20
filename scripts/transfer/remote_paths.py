"""Remote path layout for historical transfer bundles on the NUC."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_WEF_ROOT = "/home/nuc/wef"


class RemotePathError(ValueError):
    """Raised when a remote transfer path is invalid."""


@dataclass(frozen=True, slots=True)
class RemoteBundlePaths:
    """Checksum-scoped remote directories for one bundle transfer."""

    root: Path
    bundle_checksum: str
    incoming_dir: Path
    extracted_dir: Path


def _validate_checksum(bundle_checksum: str) -> None:
    if not CHECKSUM_PATTERN.fullmatch(bundle_checksum):
        msg = "bundle checksum must be 64 lowercase hexadecimal characters"
        raise RemotePathError(msg)


def _normalize_remote_root(root: Path) -> Path:
    """Normalize one remote absolute POSIX path without local filesystem resolution."""
    posix = root.as_posix()
    if not posix.startswith("/"):
        msg = "remote WEF root must be an absolute POSIX path"
        raise RemotePathError(msg)
    return Path(posix.rstrip("/") or "/")


def remote_bundle_paths(root: Path, bundle_checksum: str) -> RemoteBundlePaths:
    """Return canonical incoming and extracted paths for one bundle."""
    _validate_checksum(bundle_checksum)
    normalized = _normalize_remote_root(root)
    return RemoteBundlePaths(
        root=normalized,
        bundle_checksum=bundle_checksum,
        incoming_dir=normalized / "imports" / "incoming" / bundle_checksum,
        extracted_dir=normalized / "imports" / "extracted" / bundle_checksum,
    )
