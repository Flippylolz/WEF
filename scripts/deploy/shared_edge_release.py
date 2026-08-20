"""Manage atomic shared-edge release activation and rollback."""

# ruff: noqa: D107, T201
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NGINX_IMAGE = (
    "nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236"
)
RELEASE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
CONFIG_NAMES = ("bootstrap", "tls", "tls-redirect")
TLS_CONFIG_NAMES = frozenset({"tls", "tls-redirect"})
STATE_FILENAME = "edge-state.json"
CURRENT_LINK = "current"
PREVIOUS_LINK = "previous"
PROXY_UPSTREAM_PATTERN = re.compile(
    r'(?:proxy_pass http://|set \$[a-z0-9_]+ ")([a-z0-9_.-]+:[0-9]{1,5})(?:;|")'
)
EDGE_MOUNT = "/etc/nginx-edge"
EDGE_UID = "1000:1000"


class SharedEdgeReleaseError(RuntimeError):
    """Raised when an edge release cannot be validated or activated."""


class EdgeState(dict[str, str | None]):
    """Non-secret record of the active and previous edge releases."""

    def __init__(
        self,
        current_release: str,
        active_config: str,
        previous_release: str | None,
    ) -> None:
        super().__init__(
            current_release=current_release,
            active_config=active_config,
            previous_release=previous_release,
        )


def init_edge_tree(edge_root: Path) -> None:
    """Create the dedicated shared-edge filesystem boundary."""
    directories = (
        edge_root / "releases",
        edge_root / "letsencrypt",
        edge_root / "webroot" / ".well-known" / "acme-challenge",
        edge_root / "state",
        edge_root / "hooks",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    (edge_root / "letsencrypt").chmod(0o700)


def read_edge_state(edge_root: Path) -> EdgeState | None:
    """Read and validate the edge activation record if it exists."""
    path = edge_root / "state" / STATE_FILENAME
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("current_release"), str)
        or not isinstance(raw.get("active_config"), str)
        or not (raw.get("previous_release") is None or isinstance(raw.get("previous_release"), str))
    ):
        msg = "edge state has an invalid shape"
        raise TypeError(msg)
    return EdgeState(raw["current_release"], raw["active_config"], raw.get("previous_release"))


def write_edge_state(edge_root: Path, state: EdgeState) -> None:
    """Atomically write the edge activation record."""
    path = edge_root / "state" / STATE_FILENAME
    temporary = path.with_name(STATE_FILENAME + ".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_release_name(release_name: str) -> None:
    if not RELEASE_NAME_PATTERN.fullmatch(release_name):
        msg = f"release name is invalid: {release_name!r}"
        raise SharedEdgeReleaseError(msg)


def _resolve_release_dir(edge_root: Path, release_name: str) -> Path:
    """Resolve a release directory inside the edge boundary only."""
    _validate_release_name(release_name)
    release_dir = (edge_root / "releases" / release_name).resolve()
    releases_root = (edge_root / "releases").resolve()
    if releases_root not in release_dir.parents:
        msg = "release directory escapes the shared-edge boundary"
        raise SharedEdgeReleaseError(msg)
    if not release_dir.is_dir():
        msg = f"release directory does not exist: {release_dir}"
        raise SharedEdgeReleaseError(msg)
    return release_dir


def set_active_config(release_dir: Path, config: str) -> None:
    """Point the release's active.conf at a validated configuration file."""
    if config not in CONFIG_NAMES:
        msg = f"unknown edge configuration name: {config!r}"
        raise SharedEdgeReleaseError(msg)
    config_file = release_dir / f"{config}.conf"
    if not config_file.is_file():
        msg = f"configuration file is missing: {config_file}"
        raise SharedEdgeReleaseError(msg)
    active = release_dir / "active.conf"
    temporary = release_dir / ".active.conf.tmp"
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(f"{config}.conf")
    temporary.replace(active)


def read_active_config(release_dir: Path) -> str:
    """Return the configuration the release currently points at."""
    active = release_dir / "active.conf"
    if not active.is_symlink():
        msg = f"release has no active.conf pointer: {release_dir}"
        raise SharedEdgeReleaseError(msg)
    target = active.readlink().as_posix()
    if target not in {f"{name}.conf" for name in CONFIG_NAMES}:
        msg = f"active.conf points outside the release: {target}"
        raise SharedEdgeReleaseError(msg)
    return target.removesuffix(".conf")


def _docker(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a docker command without shell interpolation."""
    executable = shutil.which("docker")
    if executable is None:
        msg = "docker is required to manage the shared edge"
        raise SharedEdgeReleaseError(msg)
    return subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_release_config(
    edge_root: Path,
    release_name: str,
    config: str,
    *,
    upstream_network: str | None = None,
) -> None:
    """Prove a candidate configuration with nginx -t before activation.

    Validation runs as the exact uid:gid of the serving Nginx container with
    the same writable temp paths, so unreadable certificates or unusable
    temp directories fail here instead of at reload time. TLS configurations
    resolve their upstream hosts at parse time, so their validation joins the
    upstream network.
    """
    _resolve_release_dir(edge_root, release_name)
    if config not in CONFIG_NAMES:
        msg = f"unknown edge configuration name: {config!r}"
        raise SharedEdgeReleaseError(msg)
    command = [
        "run",
        "--rm",
        "--user",
        EDGE_UID,
        "--tmpfs",
        "/var/cache/nginx:rw,noexec,nosuid,size=64m,mode=1777",
        "--tmpfs",
        "/var/run:rw,noexec,nosuid,size=1m,mode=1777",
    ]
    if upstream_network is not None:
        command += ["--network", upstream_network]
    command += [
        "--volume",
        f"{edge_root.resolve()}:{EDGE_MOUNT}:ro",
        NGINX_IMAGE,
        "nginx",
        "-t",
        "-c",
        f"{EDGE_MOUNT}/releases/{release_name}/{config}.conf",
    ]
    result = _docker(command)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        msg = f"nginx -t rejected {release_name}/{config}.conf: {message}"
        raise SharedEdgeReleaseError(msg)


def extract_upstreams(
    edge_root: Path,
    release_name: str,
    *,
    config: str = "tls",
) -> list[str]:
    """Return the unique upstream targets referenced by a rendered config."""
    if config not in TLS_CONFIG_NAMES:
        msg = f"upstreams are only defined for TLS configurations: {config!r}"
        raise SharedEdgeReleaseError(msg)
    release_dir = _resolve_release_dir(edge_root, release_name)
    conf_path = release_dir / f"{config}.conf"
    if not conf_path.is_file():
        msg = f"configuration file is missing: {conf_path}"
        raise SharedEdgeReleaseError(msg)
    text = conf_path.read_text(encoding="utf-8")
    return sorted(set(PROXY_UPSTREAM_PATTERN.findall(text)))


def verify_upstreams(upstreams: list[str], network: str) -> None:
    """Prove every upstream answers TCP before an activation switch."""
    for upstream in upstreams:
        host, _, port = upstream.rpartition(":")
        result = _docker(
            [
                "run",
                "--rm",
                "--network",
                network,
                NGINX_IMAGE,
                "nc",
                "-z",
                host,
                port,
            ]
        )
        if result.returncode != 0:
            msg = f"upstream {upstream} is unreachable on network {network}"
            raise SharedEdgeReleaseError(msg)


def _swap_symlink(link: Path, target: str) -> None:
    """Atomically repoint a symlink without an unlinked window."""
    temporary = link.with_name("." + link.name + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(target)
    temporary.replace(link)


def activate_release(
    edge_root: Path,
    release_name: str,
    config: str,
    *,
    upstream_network: str = "wef-edge",
    reload_callback: Callable[[], None] | None = None,
) -> EdgeState:
    """Validate, switch to, and record one edge release configuration."""
    release_dir = _resolve_release_dir(edge_root, release_name)
    needs_upstreams = config in TLS_CONFIG_NAMES
    validate_release_config(
        edge_root,
        release_name,
        config,
        upstream_network=upstream_network if needs_upstreams else None,
    )
    if needs_upstreams:
        verify_upstreams(
            extract_upstreams(edge_root, release_name, config=config),
            upstream_network,
        )
    previous_state = read_edge_state(edge_root)
    previous_release = previous_state["current_release"] if previous_state else None
    hook_source = release_dir / "deploy-hook.sh"
    if not hook_source.is_file():
        msg = f"deploy hook is missing: {hook_source}"
        raise SharedEdgeReleaseError(msg)
    hooks_target = edge_root / "hooks" / "deploy-hook.sh"
    shutil.copyfile(hook_source, hooks_target)
    # World-executable for the same capped-root validation as the release.
    hooks_target.chmod(0o755)
    set_active_config(release_dir, config)
    _swap_symlink(edge_root / CURRENT_LINK, f"releases/{release_name}")
    if reload_callback is not None:
        try:
            reload_callback()
        except Exception:
            # A failed reload leaves the running workers on the previous
            # configuration; restore the pointer so state matches reality.
            if previous_release is not None:
                _swap_symlink(edge_root / CURRENT_LINK, f"releases/{previous_release}")
            raise
    if previous_release is not None and previous_release != release_name:
        _swap_symlink(edge_root / PREVIOUS_LINK, f"releases/{previous_release}")
    state = EdgeState(release_name, config, previous_release)
    write_edge_state(edge_root, state)
    return state


def rollback_release(edge_root: Path, *, upstream_network: str = "wef-edge") -> EdgeState:
    """Restore the previous validated release as current."""
    state = read_edge_state(edge_root)
    if state is None or state["previous_release"] is None:
        msg = "no previous release is available for rollback"
        raise SharedEdgeReleaseError(msg)
    previous_release = state["previous_release"]
    release_dir = _resolve_release_dir(edge_root, previous_release)
    config = read_active_config(release_dir)
    needs_upstreams = config in TLS_CONFIG_NAMES
    validate_release_config(
        edge_root,
        previous_release,
        config,
        upstream_network=upstream_network if needs_upstreams else None,
    )
    _swap_symlink(edge_root / CURRENT_LINK, f"releases/{previous_release}")
    _swap_symlink(edge_root / PREVIOUS_LINK, f"releases/{state['current_release']}")
    rolled_back = EdgeState(previous_release, config, state["current_release"])
    write_edge_state(edge_root, rolled_back)
    return rolled_back


def graceful_reload() -> None:
    """Ask the running edge Nginx to reload its validated configuration."""
    listing = _docker(
        [
            "ps",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=wef-shared-edge",
            "--filter",
            "label=com.docker.compose.service=nginx",
        ]
    )
    containers = listing.stdout.strip().splitlines()
    if not containers:
        msg = "no running edge nginx container was found for reload"
        raise SharedEdgeReleaseError(msg)
    result = _docker(
        [
            "exec",
            containers[0],
            "nginx",
            "-c",
            f"{EDGE_MOUNT}/current/active.conf",
            "-s",
            "reload",
        ]
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        msg = f"graceful nginx reload failed: {message}"
        raise SharedEdgeReleaseError(msg)


def main(argv: list[str] | None = None) -> int:
    """Activate or roll back a shared-edge release from CLI arguments."""
    parser = argparse.ArgumentParser(description="Manage shared-edge releases.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("--edge-root", type=Path, required=True)
    activate_parser.add_argument("--release", required=True)
    activate_parser.add_argument("--config", choices=CONFIG_NAMES, required=True)
    activate_parser.add_argument("--upstream-network", default="wef-edge")
    activate_parser.add_argument("--reload", action="store_true")
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--edge-root", type=Path, required=True)
    rollback_parser.add_argument("--upstream-network", default="wef-edge")
    rollback_parser.add_argument("--reload", action="store_true")
    arguments = parser.parse_args(argv)
    edge_root = arguments.edge_root
    try:
        if arguments.command == "activate":
            state = activate_release(
                edge_root,
                arguments.release,
                arguments.config,
                upstream_network=arguments.upstream_network,
                reload_callback=graceful_reload if arguments.reload else None,
            )
        else:
            state = rollback_release(edge_root, upstream_network=arguments.upstream_network)
            if arguments.reload:
                graceful_reload()
        print(
            "shared_edge_release: "
            f"current={state['current_release']} "
            f"config={state['active_config']} "
            f"previous={state['previous_release']}"
        )
    except SharedEdgeReleaseError as error:
        print(f"shared_edge_release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
