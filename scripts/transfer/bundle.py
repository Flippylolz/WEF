"""Historical transfer bundle packaging and verification."""

from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.transfer.checksums import sha256_file
from scripts.transfer.constants import INCLUDED_TABLES
from scripts.transfer.dry_run import DryRunSummary, build_dry_run_summary
from scripts.transfer.manifest import (
    BundleComponent,
    create_manifest,
    render_manifest,
    validate_manifest,
)
from scripts.transfer.source_layout import BundleSourceSnapshot, inspect_source
from scripts.transfer.terminal_state import TerminalState, packaging_refusal_reasons

if TYPE_CHECKING:
    from pathlib import Path


class BundlePackagingError(Exception):
    """Base error for bundle packaging failures."""


class BundleExistsError(BundlePackagingError):
    """Raised when a target bundle directory already exists."""


class BundleRefusalError(BundlePackagingError):
    """Raised when terminal-state gates block packaging."""


class BundleVerificationError(Exception):
    """Raised when one on-disk bundle fails verification."""


BUNDLE_MANIFEST_NAME = "manifest.json"
BUNDLE_CHECKSUMS_NAME = "SHA256SUMS"
DATABASE_COMPONENT = "database.sql"
RESTRICTED_TAR = "restricted-originals.tar"
PUBLIC_TAR = "public-derivatives.tar"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class PackResult:
    """Non-sensitive result of one successful bundle pack."""

    bundle_dir: Path
    manifest_path: Path
    dry_run: DryRunSummary


def dry_run_source(source_root: Path) -> tuple[BundleSourceSnapshot, DryRunSummary]:
    """Inspect one source root and return aggregate packaging estimates."""
    snapshot = inspect_source(source_root)
    summary = build_dry_run_summary(
        table_row_counts=snapshot.table_row_counts,
        media_object_count=snapshot.media_object_count,
        media_bytes=snapshot.media_bytes,
        database_dump_bytes=snapshot.database_bytes,
    )
    return snapshot, summary


def _ensure_terminal_state_allows_packaging(state: TerminalState) -> None:
    reasons = packaging_refusal_reasons(state)
    if reasons:
        msg = f"packaging refused: {', '.join(reasons)}"
        raise BundleRefusalError(msg)


def _write_tar(source_dir: Path, output_tar: Path) -> None:
    with tarfile.open(output_tar, "w") as archive:
        if not source_dir.exists():
            return
        for path in sorted(source_dir.rglob("*")):
            if path.is_file() and not path.is_symlink():
                archive.add(path, arcname=path.relative_to(source_dir).as_posix())


def _copy_component(source: Path, destination: Path) -> BundleComponent:
    shutil.copy2(source, destination)
    destination.chmod(PRIVATE_FILE_MODE)
    return BundleComponent(
        name=destination.name,
        sha256=sha256_file(destination),
        size_bytes=destination.stat().st_size,
        mode=f"{PRIVATE_FILE_MODE:04o}",
    )


def pack_bundle(
    *,
    source_root: Path,
    output_dir: Path,
    source_checksum: str,
    release_sha: str,
    terminal_state: TerminalState | None = None,
) -> PackResult:
    """Create one immutable bundle directory from a validated source layout."""
    _ensure_terminal_state_allows_packaging(
        terminal_state
        or TerminalState(
            active_import_lease=False,
            open_geocode_claims=0,
            pending_provider_work=0,
            reconciliation_complete=True,
        )
    )

    snapshot, summary = dry_run_source(source_root)
    if output_dir.exists():
        msg = f"bundle output already exists: {output_dir}"
        raise BundleExistsError(msg)

    output_dir.mkdir(parents=True)
    output_dir.chmod(PRIVATE_DIR_MODE)

    components: list[BundleComponent] = []
    components.append(
        _copy_component(snapshot.root / DATABASE_COMPONENT, output_dir / DATABASE_COMPONENT)
    )

    restricted_source = snapshot.root / "media" / "originals"
    if snapshot.restricted_originals.object_count > 0:
        restricted_tar = output_dir / RESTRICTED_TAR
        _write_tar(restricted_source, restricted_tar)
        restricted_tar.chmod(PRIVATE_FILE_MODE)
        components.append(
            BundleComponent(
                name=RESTRICTED_TAR,
                sha256=sha256_file(restricted_tar),
                size_bytes=restricted_tar.stat().st_size,
                mode=f"{PRIVATE_FILE_MODE:04o}",
            )
        )

    public_source = snapshot.root / "media" / "public"
    if snapshot.public_derivatives.object_count > 0:
        public_tar = output_dir / PUBLIC_TAR
        _write_tar(public_source, public_tar)
        public_tar.chmod(PRIVATE_FILE_MODE)
        components.append(
            BundleComponent(
                name=PUBLIC_TAR,
                sha256=sha256_file(public_tar),
                size_bytes=public_tar.stat().st_size,
                mode=f"{PRIVATE_FILE_MODE:04o}",
            )
        )

    manifest = create_manifest(
        source_checksum=source_checksum,
        release_sha=release_sha,
        table_row_counts={
            table: snapshot.table_row_counts.get(table, 0) for table in INCLUDED_TABLES
        },
        media=snapshot.media_summary,
        components=tuple(components),
    )
    manifest_path = output_dir / BUNDLE_MANIFEST_NAME
    manifest_path.write_text(render_manifest(manifest), encoding="utf-8")
    manifest_path.chmod(PRIVATE_FILE_MODE)

    checksums_path = output_dir / BUNDLE_CHECKSUMS_NAME
    checksum_lines = [
        f"{component.sha256}  {component.name}\n"
        for component in sorted(components, key=lambda item: item.name)
    ]
    checksums_path.write_text("".join(checksum_lines), encoding="utf-8")
    checksums_path.chmod(PRIVATE_FILE_MODE)

    return PackResult(bundle_dir=output_dir, manifest_path=manifest_path, dry_run=summary)


def verify_bundle(bundle_dir: Path) -> None:
    """Verify one on-disk bundle against its manifest and checksum file."""
    resolved = bundle_dir.resolve()
    manifest_path = resolved / BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        msg = "bundle is missing manifest.json"
        raise BundleVerificationError(msg)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)

    for entry in manifest["components"]:
        name = str(entry["name"])
        expected_size = int(entry["size_bytes"])
        expected_sha = str(entry["sha256"])
        component_path = resolved / name
        if not component_path.is_file():
            msg = f"bundle component is missing: {name}"
            raise BundleVerificationError(msg)
        if component_path.stat().st_size != expected_size:
            msg = f"bundle component size mismatch: {name}"
            raise BundleVerificationError(msg)
        if sha256_file(component_path) != expected_sha:
            msg = f"bundle component checksum mismatch: {name}"
            raise BundleVerificationError(msg)

    checksums_path = resolved / BUNDLE_CHECKSUMS_NAME
    if not checksums_path.is_file():
        msg = "bundle is missing SHA256SUMS"
        raise BundleVerificationError(msg)
