"""Prove the shared edge end to end with local containers only."""

from __future__ import annotations

# ruff: noqa: C901, EM101, EM102, ISC004, PLR0912, PLR0915, PLR2004, S603, S607, T201, TRY003
import dataclasses
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, cast

from scripts.deploy.shared_edge_cutover import CutoverContext, run_cutover_stages
from scripts.deploy.shared_edge_release import (
    SharedEdgeReleaseError,
    activate_release,
    graceful_reload,
    init_edge_tree,
    read_edge_state,
    rollback_release,
    validate_release_config,
    verify_upstreams,
)
from scripts.deploy.shared_edge_render import write_release
from scripts.deploy.shared_edge_smoke import build_fixture_smoke_target
from scripts.prove_shared_edge_topology import (
    EDGE_COMPOSE_FILE,
    FIXTURE_IMAGE,
    FIXTURES_COMPOSE_FILE,
    fixture_configuration,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPOSITORY_ROOT / "infra" / "nginx" / "fixtures"
RENEW_SCRIPT = REPOSITORY_ROOT / "scripts" / "deploy" / "shared_edge_renew.sh"
HTTP_PORT = 18080
HTTPS_PORT = 18443
EDGE_NETWORK = "wef-edge"
UPSTREAM_NETWORK = "wef-shared-edge_upstreams"
WEF_HOST = "wef.test"
FORECAST_HOST = "forecast.test"


class ProofError(AssertionError):
    """Raised when a shared-edge runtime expectation is not met."""


def compose_files() -> list[Path]:
    """Return the merged base-plus-fixtures compose file pair."""
    return [EDGE_COMPOSE_FILE, FIXTURES_COMPOSE_FILE]


def compose_command() -> list[str]:
    """Return the fixed docker compose prefix for the proof project."""
    command = ["docker", "compose"]
    for file in compose_files():
        command += ["--file", str(file)]
    return command


def compose(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one docker compose command with the proof environment."""
    environment = proof_environment()
    result = subprocess.run(
        compose_command() + arguments,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ProofError(f"compose {arguments} failed: {message}")
    return result


def proof_environment() -> dict[str, str]:
    """Return the proof environment for compose and docker commands."""
    return {
        **os.environ,
        "WEF_EDGE_BIND_ADDRESS": "127.0.0.1",
        "WEF_EDGE_HTTP_PORT": str(HTTP_PORT),
        "WEF_EDGE_HTTPS_PORT": str(HTTPS_PORT),
        "WEF_SHARED_EDGE_FIXTURES": str(FIXTURES_DIR),
        "WEF_SHARED_EDGE_ROOT": str(CURRENT_EDGE_ROOT),
    }


CURRENT_EDGE_ROOT = Path("/nonexistent")


def curl(
    url: str,
    *,
    resolve: str | None = None,
    cacert: Path | None = None,
    data: Path | None = None,
    method: str | None = None,
) -> tuple[int, dict[str, str], str]:
    """Perform one HTTP request and return status, headers, and body."""
    executable = shutil.which("curl")
    if executable is None:
        raise ProofError("curl is required for the shared-edge runtime proof")
    command = [
        executable,
        "--silent",
        "--show-error",
        "--max-time",
        "20",
        "--dump-header",
        "-",
    ]
    if resolve is not None:
        command += ["--resolve", resolve]
    if cacert is not None:
        command += ["--cacert", str(cacert)]
    if method is not None:
        command += ["--request", method]
    if data is not None:
        command += ["--data-binary", f"@{data}"]
    command.append(url)
    output = ""
    stderr = ""
    for _ in range(5):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = result.stdout.replace("\r\n", "\n")
        stderr = result.stderr
        if "\n\n" in output:
            break
        # The published listener can lag a healthy container briefly.
        time.sleep(2)
    split = output.split("\n\n", 1)
    if len(split) != 2:
        raise ProofError(f"malformed curl response for {url}: {stderr}")
    status_line, header_block = split[0].split("\n", 1)
    headers: dict[str, str] = {}
    for line in header_block.split("\n"):
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    try:
        status = int(status_line.split(" ", 2)[1])
    except (IndexError, ValueError) as error:
        raise ProofError(f"malformed status line: {status_line!r}") from error
    return status, headers, split[1]


def wait_for_healthy(service: str, *, timeout: float = 90.0) -> None:
    """Wait until a compose service reports a healthy container."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = compose(["ps", "--format", "json", service], check=False)
        entries: list[dict[str, Any]] = []
        stripped = result.stdout.strip()
        if stripped.startswith("["):
            entries = json.loads(stripped)
        elif stripped:
            entries = [json.loads(line) for line in stripped.splitlines()]
        if entries and entries[-1].get("Health") == "healthy":
            return
        time.sleep(2)
    raise ProofError(f"{service} did not become healthy in time")


def fixture_payload(body: str) -> dict[str, Any]:
    """Parse the JSON body returned by a header-echo fixture upstream."""
    return cast("dict[str, Any]", json.loads(body))


def assert_static_validation(edge_root: Path) -> None:
    """Prove nginx -t accepts bootstrap and rejects unusable configurations."""
    validate_release_config(edge_root, "r-001", "bootstrap")
    try:
        validate_release_config(edge_root, "r-001", "tls")
    except SharedEdgeReleaseError:
        pass
    else:
        raise ProofError("tls config must be rejected while certificates miss")
    for release, corruption in (
        (
            "broken-syntax",
            "\n        bogus_directive_for_proof definitely_broken;\n",
        ),
        (
            "broken-path",
            "",
        ),
    ):
        broken = edge_root / "releases" / release
        shutil.copytree(edge_root / "releases" / "r-001", broken)
        tls_conf = broken / "tls.conf"
        text = tls_conf.read_text(encoding="utf-8")
        if corruption:
            tls_conf.write_text(text + corruption, encoding="utf-8")
        else:
            tls_conf.write_text(
                text.replace(
                    f"/etc/nginx-edge/letsencrypt/live/{WEF_HOST}/fullchain.pem",
                    "/etc/nginx-edge/letsencrypt/live/../../escape.pem",
                ),
                encoding="utf-8",
            )
        try:
            validate_release_config(edge_root, release, "tls")
        except SharedEdgeReleaseError:
            pass
        else:
            raise ProofError(f"{release} must be rejected by nginx -t")


def assert_duplicate_default_rejected(edge_root: Path) -> None:
    """Prove nginx -t rejects two default servers on the same listener."""
    duplicate = edge_root / "releases" / "broken-duplicate"
    shutil.copytree(edge_root / "releases" / "r-001", duplicate)
    tls_conf = duplicate / "tls.conf"
    tls_conf.write_text(
        tls_conf.read_text(encoding="utf-8").replace(
            "listen 443 ssl;\n        listen [::]:443 ssl;",
            "listen 443 ssl default_server;\n        listen [::]:443 ssl default_server;",
        ),
        encoding="utf-8",
    )
    try:
        validate_release_config(
            edge_root, "broken-duplicate", "tls", upstream_network=UPSTREAM_NETWORK
        )
    except SharedEdgeReleaseError:
        pass
    else:
        raise ProofError("duplicate default servers must be rejected")


def issue_fixture_certificates(edge_root: Path) -> None:
    """Run the rendered non-interactive webroot issuance commands."""
    issuance = (edge_root / "releases" / "r-001" / "certbot-issuance.txt").read_text(
        encoding="utf-8"
    )
    commands = [
        line.strip() for line in issuance.splitlines() if line.startswith("certbot certonly")
    ]
    if len(commands) != 2:
        raise ProofError("expected exactly two issuance commands")
    for command in commands:
        result = compose(
            ["--profile", "renew", "run", "--rm", "certbot", *shlex.split(command)[1:]],
            check=False,
        )
        if result.returncode != 0:
            # Registry pull progress dominates compose output; the decisive
            # error is always at the end.
            combined = (result.stderr + result.stdout).strip().splitlines()
            message = "\n".join(combined[-30:])
            raise ProofError(f"issuance failed: {message}")
    for hostname in (WEF_HOST, FORECAST_HOST):
        lineage = edge_root / "letsencrypt" / "live" / hostname
        for name in ("fullchain.pem", "privkey.pem"):
            path = lineage / name
            if not path.is_symlink():
                raise ProofError(f"missing Certbot symlink {path}")


def assert_bootstrap_behaviour(edge_root: Path) -> None:
    """Prove the bootstrap serves only ACME challenges without redirects."""
    challenge_dir = edge_root / "webroot" / ".well-known" / "acme-challenge"
    challenge_dir.mkdir(parents=True, exist_ok=True)
    (challenge_dir / "proof-token").write_text("proof-ok", encoding="utf-8")
    status, headers, body = curl(
        f"http://127.0.0.1:{HTTP_PORT}/.well-known/acme-challenge/proof-token"
    )
    if status != 200 or body != "proof-ok":
        raise ProofError("ACME challenge was not served from the webroot")
    deadline = time.monotonic() + 20.0
    while True:
        status, headers, _ = curl(f"http://127.0.0.1:{HTTP_PORT}/")
        if status == 404 and "location" not in headers:
            return
        if time.monotonic() > deadline:
            raise ProofError("bootstrap must answer 404 without redirect")
        time.sleep(1)


def fetch_pebble_root(workspace: Path) -> Path:
    """Fetch Pebble's ephemeral root certificate for response verification."""
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            EDGE_NETWORK,
            FIXTURE_IMAGE,
            "python3",
            "-c",
            "import urllib.request, ssl;"
            "print(urllib.request.urlopen("
            "'https://pebble:15000/roots/0',"
            "context=ssl._create_unverified_context()"
            ").read().decode())",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or "BEGIN CERTIFICATE" not in result.stdout:
        raise ProofError("could not fetch the Pebble root certificate")
    root_cert = workspace / "pebble-root.crt"
    root_cert.write_text(result.stdout, encoding="utf-8")
    return root_cert


def assert_tls_behaviour(root_cert: Path, *, body_limit: str) -> None:
    """Prove two-host TLS routing, headers, and body limits."""
    wef_resolve = f"{WEF_HOST}:{HTTPS_PORT}:127.0.0.1"
    forecast_resolve = f"{FORECAST_HOST}:{HTTPS_PORT}:127.0.0.1"
    status, _, body = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    payload = fixture_payload(body)
    if status != 200 or payload["fixture"] != "wef-web":
        raise ProofError("WEF web route is not served")
    if payload["headers"].get("host") != WEF_HOST:
        raise ProofError("proxy must rewrite Host to the original hostname")
    if payload["headers"].get("x-forwarded-proto") != "https":
        raise ProofError("proxy must set X-Forwarded-Proto")
    status, _, body = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/api/v1/estates",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    if status != 200 or fixture_payload(body)["fixture"] != "wef-api":
        raise ProofError("WEF API route is not proxied")
    status, _, body = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/media/derivatives/x.webp",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    if status != 200 or fixture_payload(body)["fixture"] != "wef-media":
        raise ProofError("WEF media route is not proxied")
    status, _, body = curl(
        f"https://{FORECAST_HOST}:{HTTPS_PORT}/",
        resolve=forecast_resolve,
        cacert=root_cert,
    )
    if status != 200 or fixture_payload(body)["fixture"] != "forecast":
        raise ProofError("AI Forecast virtual host is not served")
    status, _, _ = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/.hidden",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    if status != 404:
        raise ProofError("hidden paths must be refused")
    status, _, _ = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/media/.env",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    if status != 404:
        raise ProofError("hidden media paths must be refused")
    _, headers, _ = curl(
        f"https://{WEF_HOST}:{HTTPS_PORT}/",
        resolve=wef_resolve,
        cacert=root_cert,
    )
    for header in ("content-security-policy", "x-frame-options", "x-content-type-options"):
        if header not in headers:
            raise ProofError(f"security header {header} is missing")
    with tempfile.NamedTemporaryFile(delete=False) as oversize:
        oversize.write(b"x" * (1536 * 1024))
        oversize_path = Path(oversize.name)
    expected = 413 if body_limit == "1m" else 200
    try:
        # A graceful reload is asynchronous: old workers may still answer
        # briefly, so poll until the expected limit converges.
        deadline = time.monotonic() + 20.0
        status = 0
        while True:
            status, _, _ = curl(
                f"https://{WEF_HOST}:{HTTPS_PORT}/",
                resolve=wef_resolve,
                cacert=root_cert,
                data=oversize_path,
                method="POST",
            )
            if status == expected or time.monotonic() > deadline:
                break
            time.sleep(1)
    finally:
        oversize_path.unlink()
    if status != expected:
        raise ProofError(f"body limit {body_limit}: expected {expected}, got {status}")


def wait_for_upstream(upstream: str, *, timeout: float = 30.0) -> None:
    """Wait until one upstream answers TCP again after a restart."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            verify_upstreams([upstream], UPSTREAM_NETWORK)
        except SharedEdgeReleaseError:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)
        else:
            return


def assert_redirect_behaviour(root_cert: Path) -> None:
    """Prove HTTP redirects while HTTPS routes remain healthy."""
    wef_http = f"{WEF_HOST}:{HTTP_PORT}:127.0.0.1"
    forecast_http = f"{FORECAST_HOST}:{HTTP_PORT}:127.0.0.1"
    for hostname, resolve in ((WEF_HOST, wef_http), (FORECAST_HOST, forecast_http)):
        status, headers, _ = curl(
            f"http://{hostname}:{HTTP_PORT}/",
            resolve=resolve,
        )
        if status != 301:
            raise ProofError(f"{hostname} HTTP must redirect with 301, got {status}")
        location = headers.get("location", "")
        if not location.startswith(f"https://{hostname}"):
            raise ProofError(f"{hostname} redirect Location is unsafe: {location!r}")
    status, _, body = curl(f"http://127.0.0.1:{HTTP_PORT}/.well-known/acme-challenge/proof-token")
    if status != 200 or body != "proof-ok":
        raise ProofError("ACME challenge must remain reachable after redirect activation")
    assert_tls_behaviour(root_cert, body_limit="1m")


def assert_state(edge_root: Path, current: str, config: str) -> None:
    """Assert the recorded activation state matches the expectation."""
    state = read_edge_state(edge_root)
    if state is None:
        raise ProofError("edge state is missing")
    if state["current_release"] != current or state["active_config"] != config:
        raise ProofError(f"unexpected edge state: {state}")


def run_renewal(
    edge_root: Path, merged_compose: Path, *certbot_args: str
) -> subprocess.CompletedProcess[str]:
    """Run the renewal orchestrator with proof arguments."""
    environment = {
        **proof_environment(),
        "WEF_EDGE_UPSTREAM_NETWORK": UPSTREAM_NETWORK,
    }
    return subprocess.run(
        [
            "sh",
            str(RENEW_SCRIPT),
            str(edge_root),
            str(merged_compose),
            *certbot_args,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def merged_compose_file(workspace: Path) -> Path:
    """Materialize the merged proof compose model for single-file tools."""
    rendered = compose(["--profile", "renew", "config"], check=True).stdout
    merged = workspace / "merged.compose.yaml"
    merged.write_text(rendered, encoding="utf-8")
    return merged


def pull_proof_images() -> None:
    """Pull every pinned proof image, retrying transient registry errors."""
    services = [
        "nginx",
        "certbot",
        "pebble",
        "fixture-wef-api",
        "fixture-wef-media",
        "fixture-wef-web",
        "fixture-forecast",
    ]
    result = compose(["pull", "--quiet", *services], check=False)
    for _ in range(3):
        if result.returncode == 0:
            return
        time.sleep(10)
        result = compose(["pull", "--quiet", *services], check=False)
    message = result.stderr.strip() or result.stdout.strip()
    raise ProofError(f"could not pull the pinned proof images: {message}")


def main() -> int:
    """Run the complete local shared-edge lifecycle proof."""
    global CURRENT_EDGE_ROOT  # noqa: PLW0603
    docker = shutil.which("docker")
    if docker is None:
        print("shared-edge runtime proof: docker is required", file=sys.stderr)
        return 1
    workspace = Path(tempfile.mkdtemp(prefix="wef-shared-edge-proof-"))
    edge_root = workspace / "edge"
    CURRENT_EDGE_ROOT = edge_root.resolve()
    try:
        init_edge_tree(edge_root)
        write_release(fixture_configuration(), edge_root / "releases" / "r-001")
        write_release(
            dataclasses.replace(fixture_configuration(), client_max_body_size="2m"),
            edge_root / "releases" / "r-002",
        )
        assert_static_validation(edge_root)
        pull_proof_images()

        compose(
            [
                "up",
                "--detach",
                "--wait",
                "pebble",
                "fixture-wef-api",
                "fixture-wef-media",
                "fixture-wef-web",
                "fixture-forecast",
            ]
        )
        # The bootstrap release installs the deploy hook and starts the
        # HTTP-only edge exactly as a fresh production boundary would.
        activate_release(edge_root, "r-001", "bootstrap", reload_callback=None)
        compose(["up", "--detach", "nginx"])
        wait_for_healthy("nginx")
        assert_bootstrap_behaviour(edge_root)

        issue_fixture_certificates(edge_root)
        validate_release_config(edge_root, "r-001", "tls", upstream_network=UPSTREAM_NETWORK)
        assert_duplicate_default_rejected(edge_root)
        merged_compose = merged_compose_file(workspace)

        activate_release(
            edge_root,
            "r-001",
            "tls",
            upstream_network=UPSTREAM_NETWORK,
            reload_callback=graceful_reload,
        )
        assert_state(edge_root, "r-001", "tls")
        root_cert = fetch_pebble_root(workspace)
        assert_tls_behaviour(root_cert, body_limit="1m")

        compose(["stop", "fixture-wef-web"])
        try:
            activate_release(
                edge_root,
                "r-002",
                "tls",
                upstream_network=UPSTREAM_NETWORK,
                reload_callback=None,
            )
        except SharedEdgeReleaseError:
            pass
        else:
            raise ProofError("activation must fail while an upstream is down")
        assert_state(edge_root, "r-001", "tls")
        compose(["start", "fixture-wef-web"])
        wait_for_upstream("fixture-wef-web:8080")

        activate_release(
            edge_root,
            "r-002",
            "tls",
            upstream_network=UPSTREAM_NETWORK,
            reload_callback=graceful_reload,
        )
        assert_state(edge_root, "r-002", "tls")
        assert_tls_behaviour(root_cert, body_limit="2m")

        broken = edge_root / "releases" / "r-invalid"
        shutil.copytree(edge_root / "releases" / "r-002", broken)
        (broken / "tls.conf").write_text(
            (broken / "tls.conf").read_text(encoding="utf-8")
            + "\n        bogus_directive_for_proof definitely_broken;\n",
            encoding="utf-8",
        )
        try:
            activate_release(
                edge_root,
                "r-invalid",
                "tls",
                upstream_network=UPSTREAM_NETWORK,
                reload_callback=graceful_reload,
            )
        except SharedEdgeReleaseError:
            pass
        else:
            raise ProofError("invalid configuration must not activate")
        assert_state(edge_root, "r-002", "tls")
        assert_tls_behaviour(root_cert, body_limit="2m")

        rollback_release(edge_root, upstream_network=UPSTREAM_NETWORK)
        graceful_reload()
        assert_state(edge_root, "r-001", "tls")
        assert_tls_behaviour(root_cert, body_limit="1m")

        # Redirect is a gated stage after both HTTPS routes already pass.
        challenge_dir = edge_root / "webroot" / ".well-known" / "acme-challenge"
        challenge_dir.mkdir(parents=True, exist_ok=True)
        (challenge_dir / "proof-token").write_text("proof-ok", encoding="utf-8")
        cutover = run_cutover_stages(
            CutoverContext(
                edge_root=edge_root,
                release_name="r-001",
                smoke_target=build_fixture_smoke_target(
                    http_port=HTTP_PORT,
                    https_port=HTTPS_PORT,
                ),
                curl=curl,
                upstream_network=UPSTREAM_NETWORK,
                cacert=root_cert,
                reload_callback=graceful_reload,
            )
        )
        if cutover.state["active_config"] != "tls-redirect":
            raise ProofError("cutover must finish on tls-redirect")
        assert_state(edge_root, "r-001", "tls-redirect")
        assert_redirect_behaviour(root_cert)

        compose(["stop", "fixture-forecast"])
        try:
            activate_release(
                edge_root,
                "r-002",
                "tls-redirect",
                upstream_network=UPSTREAM_NETWORK,
                reload_callback=None,
            )
        except SharedEdgeReleaseError:
            pass
        else:
            raise ProofError("redirect activation must fail while Forecast is down")
        assert_state(edge_root, "r-001", "tls-redirect")
        compose(["start", "fixture-forecast"])
        wait_for_upstream("fixture-forecast:8080")

        broken_redirect = edge_root / "releases" / "r-bad-redirect"
        shutil.copytree(edge_root / "releases" / "r-001", broken_redirect)
        redirect_conf = broken_redirect / "tls-redirect.conf"
        redirect_conf.write_text(
            redirect_conf.read_text(encoding="utf-8")
            + "\n        bogus_directive_for_proof definitely_broken;\n",
            encoding="utf-8",
        )
        try:
            activate_release(
                edge_root,
                "r-bad-redirect",
                "tls-redirect",
                upstream_network=UPSTREAM_NETWORK,
                reload_callback=graceful_reload,
            )
        except SharedEdgeReleaseError:
            pass
        else:
            raise ProofError("invalid tls-redirect must not activate")
        assert_state(edge_root, "r-001", "tls-redirect")
        assert_redirect_behaviour(root_cert)

        # Drop redirect by switching active.conf back to tls on the same release.
        activate_release(
            edge_root,
            "r-001",
            "tls",
            upstream_network=UPSTREAM_NETWORK,
            reload_callback=graceful_reload,
        )
        assert_state(edge_root, "r-001", "tls")
        assert_bootstrap_behaviour(edge_root)
        assert_tls_behaviour(root_cert, body_limit="1m")

        marker = edge_root / "state" / "reload-requested"
        marker.unlink(missing_ok=True)
        renewal = run_renewal(
            edge_root,
            merged_compose,
            "--dry-run",
            "--run-deploy-hooks",
            "--no-random-sleep-on-renew",
            "--server",
            "https://pebble:14000/dir",
        )
        if renewal.returncode != 0:
            raise ProofError(f"dry-run renewal failed: {renewal.stderr or renewal.stdout}")
        if marker.exists():
            raise ProofError("successful renewal must consume the marker")
        assert_tls_behaviour(root_cert, body_limit="1m")
        compose(["stop", "pebble"])
        marker.write_text("stale\n", encoding="utf-8")
        failed = run_renewal(
            edge_root,
            merged_compose,
            "--dry-run",
            "--run-deploy-hooks",
            "--no-random-sleep-on-renew",
            "--server",
            "https://pebble:14000/dir",
        )
        if failed.returncode == 0:
            raise ProofError("unreachable ACME must fail the renewal")
        if marker.exists():
            raise ProofError("failed renewal must not leave a marker")
        assert_tls_behaviour(root_cert, body_limit="1m")

        compose(["start", "pebble"])
        time.sleep(2)
        active_tls = edge_root / "releases" / "r-001" / "tls.conf"
        original_tls = active_tls.read_text(encoding="utf-8")
        active_tls.write_text(
            original_tls + "\n        bogus_directive_for_proof broken;\n",
            encoding="utf-8",
        )
        invalid_reload = run_renewal(
            edge_root,
            merged_compose,
            "--dry-run",
            "--run-deploy-hooks",
            "--no-random-sleep-on-renew",
            "--server",
            "https://pebble:14000/dir",
        )
        if invalid_reload.returncode == 0:
            raise ProofError("failed validation must fail the reload chain")
        assert_tls_behaviour(root_cert, body_limit="1m")
        active_tls.write_text(original_tls, encoding="utf-8")

        print("shared-edge runtime proof: all assertions passed")
        return 0
    finally:
        compose(["down", "--remove-orphans"], check=False)
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
