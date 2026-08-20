"""Preflight gates for shared-edge cutover rehearsals."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.deploy.shared_edge_release import (
    SharedEdgeReleaseError,
    extract_upstreams,
    validate_release_config,
    verify_upstreams,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

EDGE_NETWORK_NAME = "wef-edge"
EDGE_ROOT_ENV = "WEF_SHARED_EDGE_ROOT"
DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443
WATCHED_FORECAST_PORT = 3000
WATCHED_REHEARSAL_PORT = 3100
REQUIRED_EDGE_SUBDIRS = ("releases", "letsencrypt", "webroot", "state", "hooks")
LETSENCRYPT_MODE = 0o700
FORBIDDEN_COMMAND_FRAGMENTS = (
    "docker network " + "prune",
    "docker system " + "prune",
    "docker volume " + "prune",
    "down -" + "v",
)


class SharedEdgePreflightError(RuntimeError):
    """Raised when cutover preflight checks fail before mutation."""


def validate_listener_plan(
    occupied_ports: Iterable[int],
    *,
    edge_http_port: int = DEFAULT_HTTP_PORT,
    edge_https_port: int = DEFAULT_HTTPS_PORT,
) -> None:
    """Reject occupied standard edge listeners before cutover rehearsal."""
    occupied = set(occupied_ports)
    for port in (edge_http_port, edge_https_port):
        if port in occupied:
            msg = f"edge listener port is already occupied: {port}"
            raise SharedEdgePreflightError(msg)


def validate_edge_root(edge_root: Path) -> None:
    """Require the dedicated shared-edge filesystem boundary."""
    resolved = edge_root.resolve()
    if not resolved.is_dir():
        msg = f"shared-edge root is missing: {resolved}"
        raise SharedEdgePreflightError(msg)
    for name in REQUIRED_EDGE_SUBDIRS:
        path = resolved / name
        if not path.is_dir():
            msg = f"shared-edge subdirectory is missing: {path}"
            raise SharedEdgePreflightError(msg)
    letsencrypt = resolved / "letsencrypt"
    if letsencrypt.stat().st_mode & 0o777 != LETSENCRYPT_MODE:
        msg = "letsencrypt directory must be mode 0700"
        raise SharedEdgePreflightError(msg)


def validate_forecast_listener_present(occupied_ports: Iterable[int]) -> None:
    """Require the retained AI Forecast host listener during cutover planning."""
    if WATCHED_FORECAST_PORT not in set(occupied_ports):
        msg = (
            "AI Forecast host listener is unavailable; cutover planning requires "
            f"port {WATCHED_FORECAST_PORT} to remain reachable via host-gateway"
        )
        raise SharedEdgePreflightError(msg)


def scan_forbidden_commands(text: str, *, label: str) -> None:
    """Reject scripts that target destructive Docker commands."""
    lowered = text.lower()
    for fragment in FORBIDDEN_COMMAND_FRAGMENTS:
        if fragment in lowered:
            msg = f"{label} contains a forbidden command fragment"
            raise SharedEdgePreflightError(msg)


def validate_cutover_compose_text(text: str) -> None:
    """Assert the cutover overlay keeps Caddy rollback material and edge isolation."""
    if EDGE_NETWORK_NAME not in text:
        msg = "cutover compose must join the external wef-edge network"
        raise SharedEdgePreflightError(msg)
    if "caddy-rehearsal" not in text:
        msg = "cutover compose must keep Caddy behind the caddy-rehearsal profile"
        raise SharedEdgePreflightError(msg)
    if "ai-forecast" in text.lower():
        msg = "cutover compose must not reference the AI Forecast Compose project"
        raise SharedEdgePreflightError(msg)
    scan_forbidden_commands(text, label="cutover compose")


def _docker(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("docker")
    if executable is None:
        msg = "docker is required for shared-edge preflight"
        raise SharedEdgePreflightError(msg)
    return subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def network_exists(network_name: str) -> bool:
    """Return whether a Docker network already exists."""
    result = _docker(["network", "inspect", network_name])
    return result.returncode == 0


def occupied_tcp_ports() -> set[int]:
    """Return host TCP ports with an active listener."""
    ss = shutil.which("ss")
    if ss is None:
        msg = "ss is required to inspect host listeners"
        raise SharedEdgePreflightError(msg)
    result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [ss, "-H", "-ltn"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or "failed to inspect host listeners"
        raise SharedEdgePreflightError(msg)
    ports: set[int] = set()
    for line in result.stdout.splitlines():
        local = line.split()[3]
        if ":" not in local:
            continue
        port_text = local.rsplit(":", maxsplit=1)[-1]
        if port_text.isdigit():
            ports.add(int(port_text))
    return ports


def run_preflight(  # noqa: PLR0913 - explicit cutover gate inputs stay visible at call sites
    *,
    edge_root: Path,
    release_name: str,
    config: str,
    upstream_network: str,
    edge_http_port: int = DEFAULT_HTTP_PORT,
    edge_https_port: int = DEFAULT_HTTPS_PORT,
    require_forecast_listener: bool = True,
) -> None:
    """Run repository-safe preflight checks before a cutover rehearsal."""
    validate_edge_root(edge_root)
    if not network_exists(EDGE_NETWORK_NAME):
        msg = f"required Docker network is missing: {EDGE_NETWORK_NAME}"
        raise SharedEdgePreflightError(msg)
    ports = occupied_tcp_ports()
    validate_listener_plan(ports, edge_http_port=edge_http_port, edge_https_port=edge_https_port)
    if require_forecast_listener:
        validate_forecast_listener_present(ports)
    try:
        validate_release_config(
            edge_root,
            release_name,
            config,
            upstream_network=upstream_network,
        )
        verify_upstreams(extract_upstreams(edge_root, release_name), upstream_network)
    except SharedEdgeReleaseError as error:
        msg = f"edge release validation failed: {error}"
        raise SharedEdgePreflightError(msg) from error


def main(argv: list[str] | None = None) -> int:
    """Validate shared-edge cutover preconditions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-root", type=Path, required=True)
    parser.add_argument("--release-name", required=True)
    parser.add_argument("--config", choices=("bootstrap", "tls", "tls-redirect"), default="tls")
    parser.add_argument("--upstream-network", default=EDGE_NETWORK_NAME)
    parser.add_argument("--edge-http-port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument("--edge-https-port", type=int, default=DEFAULT_HTTPS_PORT)
    parser.add_argument(
        "--skip-forecast-listener-check",
        action="store_true",
        help="Fixture-only mode without a host Forecast listener.",
    )
    arguments = parser.parse_args(argv)
    try:
        run_preflight(
            edge_root=arguments.edge_root,
            release_name=arguments.release_name,
            config=arguments.config,
            upstream_network=arguments.upstream_network,
            edge_http_port=arguments.edge_http_port,
            edge_https_port=arguments.edge_https_port,
            require_forecast_listener=not arguments.skip_forecast_listener_check,
        )
    except SharedEdgePreflightError as error:
        print(f"shared-edge preflight failed: {error}", file=sys.stderr)
        return 1
    print("shared-edge preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
