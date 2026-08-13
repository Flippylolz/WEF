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
from scripts.deploy.validate_release import (
    ReleaseConfigurationError,
    ReleaseContext,
    validate_environment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPOSITORY_ROOT / "infra/compose.production.yaml"
RELEASE_SHA = "a" * 40
WEF_ROOT = Path("/home/nuc/wef")
RELEASE_DIR = WEF_ROOT / "releases" / RELEASE_SHA
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
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
        "WEF_BACKEND_IMAGE": BACKEND_IMAGE,
        "WEF_BIND_ADDRESS": "0.0.0.0",
        "WEF_DATABASE_URL": ("postgresql+asyncpg://wef:fixture-password@db:5432/wef"),
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


def assert_topology(model: dict[str, Any]) -> None:
    """Assert ports, images, paths, networks, resources, and service hardening."""
    assert model["name"] == "wef-production"
    services = cast("dict[str, dict[str, Any]]", model["services"])
    assert set(services) == {
        "api",
        "db",
        "db-permissions",
        "edge",
        "migrate",
        "seed",
        "web",
    }
    assert all("build" not in service for service in services.values())
    assert services["api"]["image"] == BACKEND_IMAGE
    assert services["migrate"]["image"] == BACKEND_IMAGE
    assert services["seed"]["image"] == BACKEND_IMAGE
    assert services["web"]["image"] == WEB_IMAGE
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
    assert services["db"]["networks"] == {"application": None}
    assert set(services["edge"]["networks"]) == {"application", "edge"}
    assert services["edge"]["user"] == "1000:1000"
    assert services["edge"]["cap_drop"] == ["ALL"]
    assert services["edge"]["cap_add"] == ["NET_BIND_SERVICE"]

    for name in ("api", "migrate", "seed", "web"):
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


def main() -> int:
    """Run the production topology proof."""
    environment = release_environment()
    model = render_compose(environment)
    assert_topology(model)
    assert_negative_configuration_gate()
    assert_script_safety()
    assert_atomic_release_state()
    assert_inventory_non_interference_gate()
    print("Production topology and deployment safety invariants pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
