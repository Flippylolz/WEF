"""Rsync command construction for resumable bundle transfer."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_SSH_PORT = 22
MAX_PORT = 65535


class RsyncTransferError(ValueError):
    """Raised when rsync transfer arguments are invalid."""


@dataclass(frozen=True, slots=True)
class RsyncTarget:
    """One strict-known-host SSH destination."""

    user: str
    host: str
    port: int = DEFAULT_SSH_PORT


@dataclass(frozen=True, slots=True)
class RsyncOptions:
    """Optional SSH identity material for one rsync transfer."""

    identity_file: Path | None = None
    known_hosts_file: Path | None = None
    dry_run: bool = False


def _validate_target(target: RsyncTarget) -> None:
    if not target.user or not target.host:
        msg = "remote target requires user and host"
        raise RsyncTransferError(msg)
    if target.port < 1 or target.port > MAX_PORT:
        msg = "remote SSH port is out of range"
        raise RsyncTransferError(msg)


def build_remote_prepare_command(
    *,
    remote_incoming_dir: Path,
    target: RsyncTarget,
    options: RsyncOptions | None = None,
) -> list[str]:
    """Build one SSH command that creates the remote incoming directory."""
    _validate_target(target)
    selected = options or RsyncOptions()
    command = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes"]
    if selected.identity_file is not None:
        command.extend(["-i", str(selected.identity_file)])
    if selected.known_hosts_file is not None:
        command.extend(["-o", f"UserKnownHostsFile={selected.known_hosts_file}"])
    if target.port != DEFAULT_SSH_PORT:
        command.extend(["-p", str(target.port)])
    command.append(f"{target.user}@{target.host}")
    command.append(f"mkdir -p {shlex.quote(remote_incoming_dir.as_posix())}")
    return command


def build_rsync_command(
    *,
    local_bundle_dir: Path,
    remote_incoming_dir: Path,
    target: RsyncTarget,
    options: RsyncOptions | None = None,
) -> list[str]:
    """Build one resumable rsync command for a verified bundle directory."""
    _validate_target(target)
    selected = options or RsyncOptions()
    if not local_bundle_dir.is_dir():
        msg = "local bundle directory must exist"
        raise RsyncTransferError(msg)

    ssh_command = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes"]
    if selected.identity_file is not None:
        ssh_command.extend(["-i", str(selected.identity_file)])
    if selected.known_hosts_file is not None:
        ssh_command.extend(["-o", f"UserKnownHostsFile={selected.known_hosts_file}"])
    if target.port != DEFAULT_SSH_PORT:
        ssh_command.extend(["-p", str(target.port)])

    remote = f"{target.user}@{target.host}:{remote_incoming_dir.as_posix()}/"
    command = [
        "rsync",
        "-a",
        "--partial",
        "--progress",
        "-e",
        shlex.join(ssh_command),
        f"{local_bundle_dir.as_posix()}/",
        remote,
    ]
    if selected.dry_run:
        command.insert(1, "--dry-run")
    return command
