"""Prove production Compose isolation and deployment-script safety."""

from __future__ import annotations

# ruff: noqa: PLR2004, S101, S104, T201
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from scripts.deploy.compare_server_inventory import (
    EXPECTED_WEF_PATHS,
    InventoryMismatchError,
    compare,
)
from scripts.deploy.release_state import (
    ReleaseState,
    activate_release_links,
    read_state,
    write_state,
)
from scripts.deploy.shared_edge_preflight import validate_cutover_compose_text
from scripts.deploy.validate_release import (
    ReleaseConfigurationError,
    ReleaseContext,
    validate_environment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.production.yaml"
CANDIDATE_COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.candidate.yaml"
CUTOVER_COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.production-cutover.yaml"
SHARED_EDGE_COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.production-shared-edge.yaml"
LOCAL_COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.yaml"
RELEASE_SHA = "a" * 40
WEF_ROOT = Path("/home/nuc/wef")
RELEASE_DIR = WEF_ROOT / "releases" / RELEASE_SHA
BUNDLE_CHECKSUM = "2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d"
BACKEND_IMAGE = (
    "ghcr.io/flippylolz/wef-backend"
    "@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
WEB_IMAGE = (
    "ghcr.io/flippylolz/wef-web"
    "@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)
FORBIDDEN_SCRIPT_FRAGMENTS = (
    "alembic downgrade",
    "docker network prune",
    "docker system prune",
    "docker volume prune",
    "down -v",
    "/home/nuc/ai-forecast",
    "/home/nuc/duckdns-ddns",
    "/home/nuc/wireguard",
)


def release_environment() -> dict[str, str]:
    """Return complete non-sensitive fixture configuration."""
    return {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "fixture-password",
        "POSTGRES_USER": "wef",
        "WEF_ADMIN_SESSION_SECRET": "fixture-admin-session-secret-0123456789abcdef",
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
        "WEF_BACKEND_IMAGE": BACKEND_IMAGE,
        "WEF_BIND_ADDRESS": "0.0.0.0",
        "WEF_CONTACT_ENCRYPTION_KEY": "0123456789abcdef" * 4,
        "WEF_CONTACT_HMAC_KEY": "fedcba9876543210" * 4,
        "WEF_DATABASE_URL": ("postgresql+asyncpg://wef:fixture-password@db:5432/wef"),
        "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
        "WEF_LOG_LEVEL": "info",
        "WEF_PUBLIC_PORT": "3100",
        "WEF_RELEASE_DIR": str(RELEASE_DIR),
        "WEF_RELEASE_SHA": RELEASE_SHA,
        "WEF_ROOT": str(WEF_ROOT),
        "WEF_WEB_IMAGE": WEB_IMAGE,
    }


def render_compose(environment: dict[str, str]) -> dict[str, Any]:
    """Render production Compose as JSON without emitting substituted values."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker is required to prove production topology"
        raise RuntimeError(msg)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as env_file:
        for key, value in sorted(environment.items()):
            env_file.write(f"{key}={value}\n")
        env_file.flush()
        result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
            [
                docker,
                "compose",
                "--env-file",
                env_file.name,
                "--file",
                str(COMPOSE_FILE),
                "--profile",
                "operator",
                "--profile",
                "rehearsal",
                "config",
                "--format",
                "json",
            ],
            check=True,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
    return cast("dict[str, Any]", json.loads(result.stdout))


def render_local_compose() -> dict[str, Any]:
    """Render the local operator topology for media-boundary assertions."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker is required to prove local media topology"
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [
            docker,
            "compose",
            "--file",
            str(LOCAL_COMPOSE_FILE),
            "--profile",
            "operator",
            "config",
            "--format",
            "json",
        ],
        check=True,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    return cast("dict[str, Any]", json.loads(result.stdout))


def assert_local_media_boundary(model: dict[str, Any]) -> None:
    """Prove only the operator sees source/original roots and public mounts stay narrow."""
    services = cast("dict[str, dict[str, Any]]", model["services"])
    mounts = {
        name: {volume["target"]: volume for volume in service.get("volumes", [])}
        for name, service in services.items()
    }
    assert mounts["api"]["/app/media/public"]["read_only"] is True
    assert mounts["edge"]["/srv/media"]["read_only"] is True
    assert mounts["importer"]["/source"]["read_only"] is True
    assert mounts["importer"]["/app/media/originals"].get("read_only", False) is False
    assert mounts["importer"]["/app/media/public"].get("read_only", False) is False
    forbidden = {"/source", "/app/media/originals", "/srv/originals"}
    assert forbidden.isdisjoint(mounts["api"])
    assert forbidden.isdisjoint(mounts["edge"])


def assert_topology(model: dict[str, Any]) -> None:  # noqa: PLR0915
    """Assert ports, images, paths, networks, resources, and service hardening."""
    assert model["name"] == "wef-production"
    services = cast("dict[str, dict[str, Any]]", model["services"])
    assert set(services) == {
        "api",
        "db",
        "db-permissions",
        "edge",
        "geocoder-check",
        "migrate",
        "seed",
        "web",
    }
    assert all("build" not in service for service in services.values())
    assert services["api"]["image"] == BACKEND_IMAGE
    assert services["geocoder-check"]["image"] == BACKEND_IMAGE
    assert services["migrate"]["image"] == BACKEND_IMAGE
    assert services["seed"]["image"] == BACKEND_IMAGE
    assert services["web"]["image"] == WEB_IMAGE
    assert services["web"]["environment"]["WEF_RELEASE_SHA"] == RELEASE_SHA
    assert services["api"]["environment"]["WEF_RELEASE_SHA"] == RELEASE_SHA
    permissions = services["db-permissions"]
    assert permissions["image"] == services["db"]["image"]
    assert permissions["profiles"] == ["operator"]
    assert permissions["user"] == "0:0"
    assert permissions["entrypoint"] == ["chown"]
    assert permissions["command"] == ["999:999", "/var/lib/postgresql/data"]
    assert permissions["cap_drop"] == ["ALL"]
    assert set(permissions["cap_add"]) == {"CHOWN", "DAC_OVERRIDE"}
    assert permissions["network_mode"] == "none"

    published = [
        (name, port) for name, service in services.items() for port in service.get("ports", [])
    ]
    assert len(published) == 1
    assert published[0][0] == "edge"
    assert published[0][1]["published"] == "3100"
    assert published[0][1]["target"] == 8080

    networks = cast("dict[str, dict[str, Any]]", model["networks"])
    assert networks["application"]["internal"] is True
    assert networks["provider-egress"].get("internal", False) is False
    assert services["db"]["networks"] == {"application": None}
    assert services["geocoder-check"]["networks"] == {"provider-egress": None}
    assert services["geocoder-check"]["profiles"] == ["operator"]
    assert services["geocoder-check"]["environment"] == {
        "WEF_ENV": "production",
        "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
    }
    assert "WEF_GEOAPIFY_API_KEY" not in services["api"]["environment"]
    assert "WEF_GEOAPIFY_API_KEY" not in services["web"]["environment"]
    assert set(services["edge"]["networks"]) == {"application", "edge"}
    assert services["edge"]["user"] == "1000:1000"
    assert services["edge"]["cap_drop"] == ["ALL"]
    assert services["edge"]["cap_add"] == ["NET_BIND_SERVICE"]

    api_mounts = {volume["target"]: volume for volume in services["api"]["volumes"]}
    edge_mounts = {volume["target"]: volume for volume in services["edge"]["volumes"]}
    assert api_mounts["/app/media/public"]["source"] == f"{WEF_ROOT}/media/public"
    assert api_mounts["/app/media/public"]["read_only"] is True
    assert edge_mounts["/srv/media"]["source"] == f"{WEF_ROOT}/media/public"
    assert edge_mounts["/srv/media"]["read_only"] is True
    forbidden_targets = {"/source", "/app/media/originals", "/srv/originals"}
    assert forbidden_targets.isdisjoint(api_mounts)
    assert forbidden_targets.isdisjoint(edge_mounts)

    for name in ("api", "geocoder-check", "migrate", "seed", "web"):
        service = services[name]
        assert service["read_only"] is True
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["cap_drop"] == ["ALL"]
        assert int(service["pids_limit"]) > 0
        assert int(service["mem_limit"]) > 0

    for service in services.values():
        assert "container_name" not in service
        assert service["logging"]["options"]["max-size"] == "10m"
        for volume in service.get("volumes", []):
            source = volume.get("source")
            if isinstance(source, str) and source.startswith("/"):
                assert source == str(RELEASE_DIR / "Caddyfile.production") or source.startswith(
                    f"{WEF_ROOT}/",
                )


def assert_negative_configuration_gate() -> None:
    """Prove placeholder and mutable-image configurations are rejected."""
    valid = release_environment()
    validate_environment(
        valid,
        ReleaseContext(
            root=WEF_ROOT,
            release_dir=RELEASE_DIR,
            release_sha=RELEASE_SHA,
            public_port=3100,
        ),
    )

    invalid = dict(valid)
    invalid["WEF_BACKEND_IMAGE"] = "ghcr.io/flippylolz/wef-backend:latest"
    try:
        validate_environment(
            invalid,
            ReleaseContext(
                root=WEF_ROOT,
                release_dir=RELEASE_DIR,
                release_sha=RELEASE_SHA,
                public_port=3100,
            ),
        )
    except ReleaseConfigurationError:
        pass
    else:
        msg = "mutable production image unexpectedly passed validation"
        raise AssertionError(msg)


def assert_script_safety() -> None:
    """Reject global cleanup, downgrade, and existing-project path references."""
    deploy_directory = REPOSITORY_ROOT / "scripts/deploy"
    for path in deploy_directory.glob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_SCRIPT_FRAGMENTS:
            assert fragment not in text


def assert_atomic_release_state() -> None:
    """Prove release state is mode-0600, replaceable, and round-trippable."""
    state: ReleaseState = {
        "release_dir": str(RELEASE_DIR),
        "config_file": str(
            WEF_ROOT / "secrets" / "releases" / RELEASE_SHA / "production.env",
        ),
        "release_sha": RELEASE_SHA,
        "public_port": 3100,
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "current.json"
        write_state(path, state)
        assert read_state(path) == state
        assert path.stat().st_mode & 0o777 == 0o600

        root = Path(directory) / "wef"
        release_dir = root / "releases" / RELEASE_SHA
        config_file = root / "secrets/releases" / RELEASE_SHA / "production.env"
        release_dir.mkdir(parents=True)
        config_file.parent.mkdir(parents=True)
        activate_release_links(root, release_dir, config_file)
        assert (root / "releases/current").resolve() == release_dir.resolve()
        assert (root / "secrets/current").resolve() == config_file.parent.resolve()


def assert_inventory_non_interference_gate() -> None:
    """Prove exact existing-resource equality and WEF path checks."""
    before: dict[str, Any] = {
        "schema": "wef-server-inventory@1",
        "hostname": "example",
        "uid": 1000,
        "compose_projects": [{"Name": "existing", "Status": "running(1)"}],
        "containers": [
            {
                "name": "existing-app",
                "id": "stable",
                "image_id": "image",
                "state": "running",
            },
        ],
        "listeners": ["tcp 0.0.0.0:3000"],
        "existing_http": {"3000": 200, "8080": 200},
        "wef_paths": [],
    }
    after = {
        **before,
        "wef_paths": [
            {
                "path": path,
                "kind": "directory",
                "mode": mode,
                "uid": 1000,
                "gid": 1000,
            }
            for path, mode in EXPECTED_WEF_PATHS.items()
        ],
    }
    compare(before, after)

    changed = {
        **after,
        "containers": [{**before["containers"][0], "id": "restarted"}],
    }
    try:
        compare(before, changed)
    except InventoryMismatchError:
        pass
    else:
        msg = "existing-container mutation unexpectedly passed inventory comparison"
        raise AssertionError(msg)


def candidate_environment() -> dict[str, str]:
    """Return complete non-sensitive candidate verification configuration."""
    candidate_media = WEF_ROOT / "candidates" / BUNDLE_CHECKSUM / "media"
    return {
        **release_environment(),
        "WEF_CANDIDATE_BUNDLE_CHECKSUM": BUNDLE_CHECKSUM,
        "WEF_CANDIDATE_DATABASE_URL": (
            "postgresql+asyncpg://wef:fixture-password@db:5432/wef_hist_candidate"
        ),
        "WEF_CANDIDATE_PUBLIC_DERIVATIVES_PATH": str(candidate_media / "public"),
        "WEF_CANDIDATE_RESTRICTED_ORIGINALS_PATH": str(candidate_media / "originals"),
        "WEF_CANDIDATE_VERIFY_BIND_ADDRESS": "127.0.0.1",
        "WEF_CANDIDATE_VERIFY_PORT": "13100",
        "WEF_MIGRATION_HEAD": "20260815_0008",
    }


def render_candidate_compose(environment: dict[str, str]) -> dict[str, Any]:
    """Render candidate Compose as JSON without emitting substituted values."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker is required to prove candidate topology"
        raise RuntimeError(msg)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as env_file:
        for key, value in sorted(environment.items()):
            env_file.write(f"{key}={value}\n")
        env_file.flush()
        result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
            [
                docker,
                "compose",
                "--env-file",
                env_file.name,
                "--file",
                str(CANDIDATE_COMPOSE_FILE),
                "config",
                "--format",
                "json",
            ],
            check=True,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
    return cast("dict[str, Any]", json.loads(result.stdout))


def assert_candidate_topology(model: dict[str, Any]) -> None:
    """Prove loopback-only candidate verification boundaries."""
    assert model["name"] == "wef-candidate"
    services = cast("dict[str, dict[str, Any]]", model["services"])
    assert set(services) == {"candidate-api", "candidate-web", "candidate-edge"}
    networks = cast("dict[str, Any]", model.get("networks", {}))
    assert "provider-egress" not in networks
    assert "verify" in networks
    assert "application" in networks
    assert "production_db" in networks
    edge_ports = services["candidate-edge"].get("ports", [])
    assert edge_ports
    published = edge_ports[0]
    assert published["host_ip"] == "127.0.0.1"
    assert str(published["published"]) == "13100"
    mounts = {
        name: {volume["target"]: volume for volume in service.get("volumes", [])}
        for name, service in services.items()
    }
    assert mounts["candidate-api"]["/app/media/public"]["read_only"] is True
    assert mounts["candidate-edge"]["/srv/media"]["read_only"] is True
    forbidden = {"/source", "/app/media/originals", "/srv/originals"}
    assert forbidden.isdisjoint(mounts["candidate-api"])
    assert forbidden.isdisjoint(mounts["candidate-edge"])
    api_networks = services["candidate-api"].get("networks", {})
    web_networks = services["candidate-web"].get("networks", {})
    edge_networks = services["candidate-edge"].get("networks", {})
    assert "provider-egress" not in api_networks
    assert "production_db" in api_networks
    assert "production_db" not in web_networks
    assert "production_db" not in edge_networks
    assert "verify" in edge_networks
    assert "verify" not in api_networks
    assert "verify" not in web_networks
    # Private aliases keep Caddyfile hostnames without colliding on production DNS.
    assert "api" in api_networks["application"].get("aliases", [])
    assert "web" in web_networks["application"].get("aliases", [])


def render_cutover_compose(
    environment: dict[str, str],
    *,
    include_caddy_rehearsal: bool = False,
) -> dict[str, Any]:
    """Render the production cutover overlay merged with the rehearsal manifest."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker is required to prove cutover topology"
        raise RuntimeError(msg)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as env_file:
        for key, value in sorted(environment.items()):
            env_file.write(f"{key}={value}\n")
        env_file.flush()
        command = [
            docker,
            "compose",
            "--env-file",
            env_file.name,
            "--file",
            str(COMPOSE_FILE),
            "--file",
            str(CUTOVER_COMPOSE_FILE),
        ]
        if include_caddy_rehearsal:
            command += ["--profile", "caddy-rehearsal"]
        command += ["config", "--format", "json"]
        result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
            command,
            check=True,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
    return cast("dict[str, Any]", json.loads(result.stdout))


def assert_cutover_topology(model: dict[str, Any]) -> None:
    """Prove the cutover overlay keeps Caddy rollback material and joins wef-edge only."""
    services = cast("dict[str, dict[str, Any]]", model["services"])
    assert "edge" not in services, "default cutover must not publish Caddy"
    assert "media-edge" in services, "cutover model must add a dedicated media upstream"
    networks = cast("dict[str, Any]", model.get("networks", {}))
    shared_edge = networks["shared_edge"]
    assert shared_edge.get("external") is True
    assert shared_edge.get("name") == "wef-edge"
    api_networks = services["api"].get("networks", {})
    web_networks = services["web"].get("networks", {})
    media_networks = services["media-edge"].get("networks", {})
    assert "shared_edge" in api_networks
    assert "shared_edge" in web_networks
    assert "shared_edge" in media_networks
    assert api_networks["shared_edge"].get("aliases") == ["wef-api"]
    assert web_networks["shared_edge"].get("aliases") == ["wef-web"]
    assert media_networks["shared_edge"].get("aliases") == ["wef-media"]
    assert "application" in api_networks
    assert "application" in web_networks
    mounts = {volume["target"]: volume for volume in services["media-edge"].get("volumes", [])}
    assert mounts["/srv/media"]["read_only"] is True
    assert mounts["/etc/nginx/nginx.conf"]["read_only"] is True
    cutover_text = CUTOVER_COMPOSE_FILE.read_text(encoding="utf-8")
    validate_cutover_compose_text(cutover_text)


def assert_cutover_rollback_topology(model: dict[str, Any]) -> None:
    """Prove Caddy rollback remains available behind the caddy-rehearsal profile."""
    services = cast("dict[str, dict[str, Any]]", model["services"])
    edge = services["edge"]
    assert edge.get("profiles") == ["caddy-rehearsal"], "Caddy must stay behind caddy-rehearsal"
    assert edge.get("ports"), "Caddy rollback must still publish the rehearsal port"


def render_shared_edge_compose(environment: dict[str, str]) -> dict[str, Any]:
    """Render ordinary-release shared-edge attachment without disabling Caddy."""
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker is required to prove shared-edge attachment topology"
        raise RuntimeError(msg)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as env_file:
        for key, value in sorted(environment.items()):
            env_file.write(f"{key}={value}\n")
        env_file.flush()
        result = subprocess.run(  # noqa: S603
            [
                docker,
                "compose",
                "--env-file",
                env_file.name,
                "--file",
                str(COMPOSE_FILE),
                "--file",
                str(SHARED_EDGE_COMPOSE_FILE),
                "config",
                "--format",
                "json",
            ],
            check=True,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
    return cast("dict[str, Any]", json.loads(result.stdout))


def assert_shared_edge_attachment_topology(model: dict[str, Any]) -> None:
    """Prove shared-edge attachment keeps Caddy :3100 and joins wef-edge aliases."""
    services = cast("dict[str, dict[str, Any]]", model["services"])
    networks = cast("dict[str, dict[str, Any]]", model["networks"])
    assert "edge" in services, "ordinary shared-edge attachment must keep Caddy"
    assert "profiles" not in services["edge"], "Caddy must remain in the default profile"
    assert "media-edge" in services
    assert networks["shared_edge"].get("external") is True
    assert networks["shared_edge"].get("name") == "wef-edge"
    api_networks = services["api"]["networks"]
    web_networks = services["web"]["networks"]
    media_networks = services["media-edge"]["networks"]
    assert api_networks["shared_edge"].get("aliases") == ["wef-api"]
    assert web_networks["shared_edge"].get("aliases") == ["wef-web"]
    assert media_networks["shared_edge"].get("aliases") == ["wef-media"]
    deploy = (REPOSITORY_ROOT / "scripts/deploy/deploy.sh").read_text(encoding="utf-8")
    assert "bring_up_application_services" in deploy
    assert "smoke_public_https_origin" in deploy


def main() -> int:
    """Run the production topology proof."""
    environment = release_environment()
    model = render_compose(environment)
    assert_topology(model)
    assert_candidate_topology(render_candidate_compose(candidate_environment()))
    assert_cutover_topology(render_cutover_compose(environment))
    assert_cutover_rollback_topology(
        render_cutover_compose(environment, include_caddy_rehearsal=True)
    )
    assert_shared_edge_attachment_topology(render_shared_edge_compose(environment))
    assert_local_media_boundary(render_local_compose())
    assert_negative_configuration_gate()
    assert_script_safety()
    assert_atomic_release_state()
    assert_inventory_non_interference_gate()
    print("Production topology and deployment safety invariants pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
