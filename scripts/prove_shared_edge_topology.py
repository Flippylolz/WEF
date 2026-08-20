"""Prove the inert shared-edge Compose policy and renderer guarantees."""

from __future__ import annotations

# ruff: noqa: C901, PLR0912, PLR0915, PLR2004, PT018, S101, S108, T201, TRY003, EM101, EM102
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from scripts.deploy.shared_edge_release import NGINX_IMAGE as RELEASE_NGINX_IMAGE
from scripts.deploy.shared_edge_render import (
    BOOTSTRAP_CONFIG,
    HOOK_FILENAME,
    ISSUANCE_FILENAME,
    TLS_CONFIG,
    TLS_REDIRECT_CONFIG,
    EdgeConfiguration,
    SharedEdgeRenderError,
    write_release,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EDGE_COMPOSE_FILE = REPOSITORY_ROOT / "infra" / "compose.shared-edge.yaml"
FIXTURES_COMPOSE_FILE = REPOSITORY_ROOT / "infra" / "compose.shared-edge-fixtures.yaml"
PRODUCTION_COMPOSE_FILE = REPOSITORY_ROOT / "infra" / "compose.production.yaml"
NGINX_TEMPLATES_DIR = REPOSITORY_ROOT / "infra" / "nginx"
NGINX_IMAGE = (
    "nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236"
)
CERTBOT_IMAGE = (
    "certbot/certbot:v4.2.0@sha256:9626d72120577cf72da4fc7948806e9993598981720a4cbe04340a502468d67b"
)
FIXTURE_IMAGE = (
    "python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d"
)
PEBBLE_IMAGE = (
    "ghcr.io/letsencrypt/pebble:latest@sha256:ddf230642b1a584f519f32e347de1b0"
    "5a6e4c1f6c35c1863b33effeab5f78199"
)
EDGE_PROJECT = "wef-shared-edge"
EDGE_NETWORK_NAME = "wef-edge"
FORBIDDEN_SCRIPT_FRAGMENTS = (
    "docker network prune",
    "docker system prune",
    "docker volume prune",
    "down -v",
    "/home/nuc",
)
FORBIDDEN_INFRA_FRAGMENTS = (
    "duckdns",
    "PRIVATE KEY",
)


def fixture_configuration() -> EdgeConfiguration:
    """Return the complete fixture edge configuration used by proofs."""
    return EdgeConfiguration(
        wef_hostname="wef.test",
        forecast_hostname="forecast.test",
        wef_api_upstream="fixture-wef-api:8080",
        wef_media_upstream="fixture-wef-media:8080",
        wef_web_upstream="fixture-wef-web:8080",
        forecast_upstream="fixture-forecast:8080",
        client_max_body_size="1m",
        fixture_mode=True,
    )


def render_edge_compose(*, include_fixtures: bool = True) -> dict[str, Any]:
    """Render the shared-edge Compose model with proof environment values."""
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker is required to prove the shared edge")
    command = [
        docker,
        "compose",
        "--file",
        str(EDGE_COMPOSE_FILE),
    ]
    if include_fixtures:
        command += ["--file", str(FIXTURES_COMPOSE_FILE)]
    command += ["--profile", "renew", "config", "--format", "json"]
    result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        command,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **proof_environment()},
    )
    if result.returncode != 0:
        raise RuntimeError(f"shared-edge compose render failed: {result.stderr}")
    return cast("dict[str, Any]", json.loads(result.stdout))


def proof_environment() -> dict[str, str]:
    """Return the fixed proof environment for compose renders."""
    return {
        "WEF_EDGE_HTTP_PORT": "18080",
        "WEF_EDGE_HTTPS_PORT": "18443",
        "WEF_SHARED_EDGE_FIXTURES": str(NGINX_TEMPLATES_DIR / "fixtures"),
        "WEF_SHARED_EDGE_ROOT": "/tmp/wef-edge-proof/root",
    }


def assert_deterministic_compose_render() -> None:
    """Prove two renders produce byte-identical Compose output."""
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker is required to prove the shared edge")
    environment = proof_environment()
    renders = []
    for _ in range(2):
        result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
            [
                docker,
                "compose",
                "--file",
                str(EDGE_COMPOSE_FILE),
                "--file",
                str(FIXTURES_COMPOSE_FILE),
                "--profile",
                "renew",
                "config",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **environment},
        )
        if result.returncode != 0:
            raise RuntimeError(f"shared-edge compose render failed: {result.stderr}")
        renders.append(result.stdout)
    assert renders[0] == renders[1], "compose render is not deterministic"


def assert_base_edge_compose_policy() -> None:
    """Assert the production edge model mounts exactly the boundary trees."""
    model = render_edge_compose(include_fixtures=False)
    services = model["services"]
    assert set(services) == {"nginx", "certbot"}, (
        "the base edge model contains only nginx and certbot"
    )
    certbot = services["certbot"]
    certbot_mounts = {mount["target"]: mount for mount in certbot["volumes"]}
    assert set(certbot_mounts) == {
        "/etc/letsencrypt",
        "/var/www/certbot",
        "/var/lib/wef-edge",
        "/edge-hooks",
        "/var/log/letsencrypt",
    }, "certbot mounts exactly the persistent state and webroot trees"
    assert certbot_mounts["/edge-hooks"].get("read_only") is True, "hooks ro"
    assert set(certbot["networks"]) == {"edge"}, "certbot networks"
    assert set(services["nginx"]["networks"]) == {"edge"}, "nginx networks"


def assert_edge_compose_policy(model: dict[str, Any]) -> None:
    """Assert project, image, privilege, mount, network, and log policy."""
    assert model["name"] == EDGE_PROJECT, "edge project must be wef-shared-edge"
    services = model["services"]
    nginx = services["nginx"]
    certbot = services["certbot"]
    assert nginx["image"] == NGINX_IMAGE, "nginx image must be digest-pinned"
    assert certbot["image"] == CERTBOT_IMAGE, "certbot image must be digest-pinned"
    for name in (
        "fixture-wef-api",
        "fixture-wef-media",
        "fixture-wef-web",
        "fixture-forecast",
    ):
        assert services[name]["image"] == FIXTURE_IMAGE, f"{name} image pin"
    assert services["pebble"]["image"] == PEBBLE_IMAGE, "pebble image pin"
    for name, service in services.items():
        assert "container_name" not in service, f"{name} must not set a name"
    assert nginx["user"] == "1000:1000", "nginx must run as the edge uid"
    assert nginx["cap_drop"] == ["ALL"], "nginx must drop all capabilities"
    assert nginx["cap_add"] == ["NET_BIND_SERVICE"], "nginx bind capability"
    assert nginx["read_only"] is True, "nginx root filesystem must be read-only"
    assert nginx["init"] is True, "nginx must run with init"
    assert "no-new-privileges:true" in nginx["security_opt"], "nginx no-new-privs"
    assert "host.docker.internal=host-gateway" in nginx.get("extra_hosts", []), (
        "nginx must map host.docker.internal through the Linux host-gateway"
    )
    tmpfs_targets = {entry.split(":")[0] for entry in nginx["tmpfs"]}
    assert "/var/cache/nginx" in tmpfs_targets, "nginx temp dir must be tmpfs"
    assert "/var/run" in tmpfs_targets, "nginx pid dir must be tmpfs"
    assert "healthcheck" in nginx, "nginx must have a health check"
    assert certbot["cap_drop"] == ["ALL"], "certbot must drop all capabilities"
    assert certbot["cap_add"] == ["CHOWN", "DAC_OVERRIDE", "FOWNER"], (
        "certbot keeps only the reviewed tree-administration capabilities"
    )
    assert certbot["read_only"] is True, "certbot root filesystem must be read-only"
    published_ports = {
        str(port["published"]) for service in services.values() for port in service.get("ports", [])
    }
    assert published_ports == {"18080", "18443"}, (
        "only the edge HTTP and HTTPS listeners may publish host ports"
    )
    assert "restart" in nginx and "restart" in certbot
    for service in (nginx, certbot):
        logs = service["logging"]
        assert logs["driver"] == "json-file", "bounded json-file log driver"
        assert logs["options"]["max-file"] == "3", "bounded log file count"
        assert logs["options"]["max-size"] == "10m", "bounded log file size"
    mounts = {mount["target"]: mount for mount in nginx["volumes"]}
    edge_mount = mounts.get("/etc/nginx-edge")
    assert edge_mount is not None, "nginx must mount the edge boundary"
    assert edge_mount.get("read_only") is True, "edge boundary mount is read-only"
    certbot_environment = certbot.get("environment", {})
    assert certbot_environment.get("REQUESTS_CA_BUNDLE") == ("/edge-fixtures/pebble.minica.crt"), (
        "certbot must trust only the pinned proof ACME authority"
    )
    pebble_mounts = {mount["target"]: mount for mount in certbot["volumes"]}
    assert pebble_mounts["/edge-fixtures/pebble.minica.crt"].get("read_only") is True, (
        "proof authority mount is read-only"
    )
    networks = model["networks"]
    assert networks["edge"]["name"] == EDGE_NETWORK_NAME, "edge network name"
    assert networks["upstreams"]["internal"] is True, "upstream network internal"
    assert set(nginx["networks"]) == {"edge", "upstreams"}, "nginx networks"
    assert set(certbot["networks"]) == {"edge"}, "certbot networks"
    for name in (
        "fixture-wef-api",
        "fixture-wef-media",
        "fixture-wef-web",
        "fixture-forecast",
    ):
        assert set(services[name]["networks"]) == {"upstreams"}, f"{name} networks"
    assert set(services["pebble"]["networks"]) == {"edge"}, "pebble networks"
    assert "volumes" not in model or not model.get("volumes"), "no named volumes"


def assert_edge_boundary_ownership() -> None:
    """Prove ordinary WEF releases never own or tear down the edge project."""
    production = PRODUCTION_COMPOSE_FILE.read_text(encoding="utf-8")
    assert EDGE_NETWORK_NAME not in production, (
        "the production project must not own the shared edge network"
    )
    assert "shared-edge" not in production, (
        "the production project must not reference the shared edge"
    )
    manifest = REPOSITORY_ROOT / "scripts" / "deploy" / "create_release_manifest.py"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "shared-edge" not in manifest_text, "ordinary WEF releases must not ship the shared edge"
    deploy = REPOSITORY_ROOT / "scripts" / "deploy" / "deploy.sh"
    deploy_text = deploy.read_text(encoding="utf-8")
    assert "compose.shared-edge" not in deploy_text, (
        "ordinary WEF deploys must not manage the shared-edge Compose project"
    )
    assert "bring_up_application_services" in deploy_text
    assert "smoke_public_https_origin" in deploy_text
    common = (REPOSITORY_ROOT / "scripts" / "deploy" / "production-common.sh").read_text(
        encoding="utf-8"
    )
    assert "reconnect_shared_edge_upstreams" in common
    assert "compose.production-shared-edge.yaml" in common
    reconnect = REPOSITORY_ROOT / "scripts" / "deploy" / "reconnect-wef-upstreams.sh"
    assert reconnect.is_file(), "reconnect script must ship in application releases"
    reconnect_text = reconnect.read_text(encoding="utf-8")
    assert "docker kill -s HUP" in reconnect_text
    assert "nginx -s reload" not in reconnect_text
    assert "wef-media" in reconnect_text
    assert "compose.shared-edge" not in reconnect_text
    assert "docker compose" not in reconnect_text


def assert_script_safety() -> None:
    """Scan edge-owned scripts for forbidden destructive or host-path bits."""
    scripts = [
        *sorted((REPOSITORY_ROOT / "scripts" / "deploy").glob("shared_edge_*.sh")),
        NGINX_TEMPLATES_DIR / HOOK_FILENAME,
    ]
    assert scripts, "edge scripts must exist to be scanned"
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_SCRIPT_FRAGMENTS:
            assert fragment not in text, f"{script.name} contains {fragment!r}"


def assert_infra_secret_exclusion() -> None:
    """Prove no production hostname, private key, or secret ships in infra/."""
    for path in sorted(NGINX_TEMPLATES_DIR.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            for fragment in FORBIDDEN_INFRA_FRAGMENTS:
                assert fragment not in text, f"{path} contains {fragment!r}"


def assert_renderer_positive() -> dict[str, str]:
    """Render fixture releases deterministically and return their content."""
    with tempfile.TemporaryDirectory() as workspace:
        first = Path(workspace) / "r-001"
        second = Path(workspace) / "r-002"
        write_release(fixture_configuration(), first)
        write_release(fixture_configuration(), second)
        rendered: dict[str, str] = {}
        for name in (
            BOOTSTRAP_CONFIG,
            TLS_CONFIG,
            TLS_REDIRECT_CONFIG,
            ISSUANCE_FILENAME,
            HOOK_FILENAME,
        ):
            first_bytes = (first / name).read_bytes()
            second_bytes = (second / name).read_bytes()
            assert first_bytes == second_bytes, f"{name} render is not deterministic"
            rendered[name] = first_bytes.decode("utf-8")
        return rendered


def assert_generated_configuration_policy(rendered: dict[str, str]) -> None:
    """Assert bootstrap, TLS, and redirect fixture configuration invariants."""
    bootstrap = rendered[BOOTSTRAP_CONFIG]
    assert "proxy_pass" not in bootstrap, "bootstrap must not proxy traffic"
    assert "301" not in bootstrap and "302" not in bootstrap, "no redirects"
    assert "return 404" in bootstrap, "bootstrap must refuse non-ACME traffic"
    assert "/.well-known/acme-challenge/" in bootstrap, "ACME location missing"
    tls = rendered[TLS_CONFIG]
    assert "server_name wef.test;" in tls, "WEF virtual host missing"
    assert "server_name forecast.test;" in tls, "forecast virtual host missing"
    assert "client_max_body_size 1m;" in tls, "body limit missing"
    assert "proxy_connect_timeout 5s;" in tls, "connect timeout missing"
    assert "proxy_read_timeout 60s;" in tls, "read timeout missing"
    assert "proxy_send_timeout 60s;" in tls, "send timeout missing"
    assert "X-Forwarded-For" in tls, "forwarded-for header missing"
    assert "X-Forwarded-Proto" in tls, "forwarded-proto header missing"
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in tls, "TLS protocol policy missing"
    assert "Content-Security-Policy" in tls, "WEF security headers missing"
    assert "Strict-Transport-Security" in tls, "WEF HSTS header missing"
    assert 'Strict-Transport-Security "max-age=31536000"' in tls, "WEF HSTS max-age missing"
    assert (
        "preload"
        not in tls.lower()
        .split("strict-transport-security", 1)[-1]
        .split(
            "\n",
            1,
        )[0]
    ), "HSTS preload requires separate approval"
    assert "return 404" in tls, "tls stage must keep HTTP non-ACME as 404"
    assert "return 301" not in tls, "tls stage must not enable redirects"
    redirect = rendered[TLS_REDIRECT_CONFIG]
    assert "return 301 https://$host$request_uri;" in redirect, "redirect stage missing"
    assert "return 404" not in redirect.split("location / {", 1)[1].split("}", 1)[0], (
        "redirect HTTP / must not keep 404"
    )
    assert "/.well-known/acme-challenge/" in redirect, "redirect must keep ACME"
    issuance = rendered[ISSUANCE_FILENAME]
    assert "--webroot" in issuance, "issuance must use webroot"
    assert "--non-interactive" in issuance, "issuance must be unattended"
    assert issuance.count("certbot certonly") == 2, "two independent certificates"
    assert "duckdns" not in issuance, "no production hostname in issuance"


def assert_wef_only_renderer() -> None:
    """Prove WEF-only releases omit Forecast TLS and issuance."""
    with tempfile.TemporaryDirectory() as workspace:
        target = Path(workspace) / "r-wef-only"
        write_release(
            EdgeConfiguration(
                wef_hostname="wef.test",
                wef_api_upstream="fixture-wef-api:8080",
                wef_media_upstream="fixture-wef-media:8080",
                wef_web_upstream="fixture-wef-web:8080",
                fixture_mode=True,
            ),
            target,
        )
        tls = (target / TLS_CONFIG).read_text(encoding="utf-8")
        issuance = (target / ISSUANCE_FILENAME).read_text(encoding="utf-8")
        assert "server_name wef.test;" in tls, "WEF virtual host missing"
        assert "server_name forecast.test;" not in tls, "forecast vhost must be absent"
        assert issuance.count("certbot certonly") == 1, "WEF-only issuance is one cert"
        assert "forecast.test" not in issuance, "forecast must not appear in issuance"


def assert_renderer_negative() -> None:
    """Prove the renderer rejects unsafe or non-deterministic inputs."""
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        base = fixture_configuration()
        duplicates = EdgeConfiguration(
            wef_hostname="wef.test",
            forecast_hostname="wef.test",
            wef_api_upstream=base.wef_api_upstream,
            wef_media_upstream=base.wef_media_upstream,
            wef_web_upstream=base.wef_web_upstream,
            forecast_upstream=base.forecast_upstream,
            fixture_mode=True,
        )
        try:
            write_release(duplicates, root / "dup")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("duplicate hostnames must be rejected")
        production_host = EdgeConfiguration(
            wef_hostname="wef.example.com",
            forecast_hostname=base.forecast_hostname,
            wef_api_upstream=base.wef_api_upstream,
            wef_media_upstream=base.wef_media_upstream,
            wef_web_upstream=base.wef_web_upstream,
            forecast_upstream=base.forecast_upstream,
            fixture_mode=True,
        )
        try:
            write_release(production_host, root / "prod-host")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("non-.test hostnames must be rejected in fixtures")
        try:
            write_release(base, root / "traversal" / ".." / "escape")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("path traversal must be rejected")
        no_port = EdgeConfiguration(
            wef_hostname=base.wef_hostname,
            forecast_hostname=base.forecast_hostname,
            wef_api_upstream="fixture-wef-api",
            wef_media_upstream=base.wef_media_upstream,
            wef_web_upstream=base.wef_web_upstream,
            forecast_upstream=base.forecast_upstream,
            fixture_mode=True,
        )
        try:
            write_release(no_port, root / "no-port")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("upstreams without a port must be rejected")
        oversize = EdgeConfiguration(
            wef_hostname=base.wef_hostname,
            forecast_hostname=base.forecast_hostname,
            wef_api_upstream=base.wef_api_upstream,
            wef_media_upstream=base.wef_media_upstream,
            wef_web_upstream=base.wef_web_upstream,
            forecast_upstream=base.forecast_upstream,
            client_max_body_size="999999999m",
            fixture_mode=True,
        )
        try:
            write_release(oversize, root / "oversize")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("unbounded body sizes must be rejected")
        with_email = EdgeConfiguration(
            wef_hostname=base.wef_hostname,
            forecast_hostname=base.forecast_hostname,
            wef_api_upstream=base.wef_api_upstream,
            wef_media_upstream=base.wef_media_upstream,
            wef_web_upstream=base.wef_web_upstream,
            forecast_upstream=base.forecast_upstream,
            email="owner@example.test",
            fixture_mode=True,
        )
        try:
            write_release(with_email, root / "email")
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("fixture mode must reject real account emails")
        occupied = root / "occupied"
        occupied.mkdir()
        (occupied / "stowaway").write_text("x", encoding="utf-8")
        try:
            write_release(base, occupied)
        except SharedEdgeRenderError:
            pass
        else:
            raise AssertionError("non-empty release directories must be rejected")


def assert_image_pin_consistency() -> None:
    """Prove the nginx pin matches across compose, release, and renew tools."""
    assert RELEASE_NGINX_IMAGE == NGINX_IMAGE, (
        "the release tool must use the same pinned nginx image as compose"
    )
    renew = (REPOSITORY_ROOT / "scripts" / "deploy" / "shared_edge_renew.sh").read_text(
        encoding="utf-8"
    )
    assert NGINX_IMAGE in renew, "renew tool must use the pinned image"
    assert "kill -s HUP nginx" in renew, "renew must HUP nginx rather than nginx -s reload"
    assert "nginx -s reload" not in renew, "renew must not use nginx -s reload"


def main() -> int:
    """Run every repository-level shared-edge policy proof."""
    model = render_edge_compose()
    assert_edge_compose_policy(model)
    assert_base_edge_compose_policy()
    assert_deterministic_compose_render()
    assert_edge_boundary_ownership()
    assert_script_safety()
    assert_infra_secret_exclusion()
    rendered = assert_renderer_positive()
    assert_generated_configuration_policy(rendered)
    assert_wef_only_renderer()
    assert_renderer_negative()
    assert_image_pin_consistency()
    print("shared-edge topology proof: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
