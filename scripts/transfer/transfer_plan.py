"""Transfer plan generation for verified historical bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.transfer.bundle import BUNDLE_MANIFEST_NAME, verify_bundle
from scripts.transfer.checksums import sha256_file
from scripts.transfer.manifest import validate_manifest
from scripts.transfer.remote_paths import remote_bundle_paths

if TYPE_CHECKING:
    from pathlib import Path


class TransferPlanError(ValueError):
    """Raised when a transfer plan cannot be built."""


@dataclass(frozen=True, slots=True)
class TransferComponent:
    """One immutable bundle artifact to transfer."""

    name: str
    local_path: Path
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class TransferPlan:
    """Non-sensitive plan for one verified bundle transfer."""

    bundle_checksum: str
    source_checksum: str
    migration_head: str
    remote_incoming_dir: Path
    remote_extracted_dir: Path
    components: tuple[TransferComponent, ...]

    @property
    def total_bytes(self) -> int:
        """Return the total byte size of all bundle components."""
        return sum(component.size_bytes for component in self.components)


def build_transfer_plan(*, bundle_dir: Path, wef_root: Path) -> TransferPlan:
    """Verify one local bundle and build a remote transfer plan."""
    verify_bundle(bundle_dir)
    manifest_path = bundle_dir / BUNDLE_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)

    bundle_checksum = str(manifest["source_checksum"])
    remote_paths = remote_bundle_paths(wef_root, bundle_checksum)
    components: list[TransferComponent] = []
    for entry in manifest["components"]:
        name = str(entry["name"])
        component_path = bundle_dir / name
        if not component_path.is_file():
            msg = f"bundle component is missing locally: {name}"
            raise TransferPlanError(msg)
        actual_size = component_path.stat().st_size
        expected_size = int(entry["size_bytes"])
        if actual_size != expected_size:
            msg = f"bundle component size mismatch: {name}"
            raise TransferPlanError(msg)
        actual_sha = sha256_file(component_path)
        expected_sha = str(entry["sha256"])
        if actual_sha != expected_sha:
            msg = f"bundle component checksum mismatch: {name}"
            raise TransferPlanError(msg)
        components.append(
            TransferComponent(
                name=name,
                local_path=component_path,
                size_bytes=actual_size,
                sha256=actual_sha,
            )
        )

    return TransferPlan(
        bundle_checksum=bundle_checksum,
        source_checksum=bundle_checksum,
        migration_head=str(manifest["migration_head"]),
        remote_incoming_dir=remote_paths.incoming_dir,
        remote_extracted_dir=remote_paths.extracted_dir,
        components=tuple(sorted(components, key=lambda item: item.name)),
    )
