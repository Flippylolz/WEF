"""Remote path layout for historical transfer bundles on the NUC."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


def remote_bundle_paths(root: Path, bundle_checksum: str) -> RemoteBundlePaths:
    """Return canonical incoming and extracted paths for one bundle."""
    _validate_checksum(bundle_checksum)
    resolved = root.resolve()
    return RemoteBundlePaths(
        root=resolved,
        bundle_checksum=bundle_checksum,
        incoming_dir=resolved / "imports" / "incoming" / bundle_checksum,
        extracted_dir=resolved / "imports" / "extracted" / bundle_checksum,
    )
