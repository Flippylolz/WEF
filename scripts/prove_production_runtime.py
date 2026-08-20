"""Run the production topology twice and prove bind-mounted catalog persistence."""

from __future__ import annotations

# ruff: noqa: T201
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_SHA = "c" * 40


def available_port() -> int:
    """Reserve and return an available loopback TCP port for the bounded proof."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def run(
    command: list[str],
    *,
    environment: dict[str, str],
    capture_output: bool = True,
) -> None:
    """Run one proof command without exposing the fixture environment."""
    subprocess.run(  # noqa: S603 - command starts with trusted absolute executable
        command,
        check=True,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=capture_output,
        text=True,
    )


def start_application(
    compose: list[str],
    *,
    environment: dict[str, str],
) -> None:
    """Start the application and expose bounded edge diagnostics on failure."""
    try:
        run(
            [*compose, "up", "--detach", "--wait", "api", "web", "edge"],
            environment=environment,
        )
    except subprocess.CalledProcessError:
        subprocess.run(  # noqa: S603 - trusted docker command
            [*compose, "logs", "--no-color", "--tail", "50", "edge"],
            check=False,
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
        )
        raise


def main() -> int:
    """Start, seed, recreate, and re-smoke the isolated production model."""
    docker = shutil.which("docker")
    shell = shutil.which("sh")
    if docker is None or shell is None:
        msg = "docker and a POSIX shell are required"
        raise RuntimeError(msg)

    for image in ("wef-backend:local", "wef-web:local"):
        run([docker, "image", "inspect", image], environment=os.environ.copy())

    runtime_parent = REPOSITORY_ROOT / "tmp"
    runtime_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="production-runtime-proof-",
        dir=runtime_parent,
    ) as directory:
        root = Path(directory) / "wef"
        release_dir = root / "releases" / RELEASE_SHA
        config_dir = root / "secrets" / "releases" / RELEASE_SHA
        for relative in ("postgres", "media", "caddy-data", "state"):
            (root / relative).mkdir(parents=True)
        (root / "media/public").mkdir(parents=True)
        release_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        shutil.copy2(REPOSITORY_ROOT / "infra/compose.production.yaml", release_dir)
        shutil.copy2(REPOSITORY_ROOT / "infra/Caddyfile.production", release_dir)

        public_port = available_port()
        config_file = config_dir / "production.env"
        values = {
            "POSTGRES_DB": "wef",
            "POSTGRES_PASSWORD": "runtime-proof-password",
            "POSTGRES_USER": "wef",
            "WEF_ADMIN_SESSION_SECRET": "runtime-proof-admin-session-secret-0123456789",
            "WEF_CONTACT_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "WEF_CONTACT_HMAC_KEY": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            "WEF_ALLOW_SYNTHETIC_SEED": "true",
            "WEF_BACKEND_IMAGE": "wef-backend:local",
            "WEF_BIND_ADDRESS": "127.0.0.1",
            "WEF_DATABASE_URL": ("postgresql+asyncpg://wef:runtime-proof-password@db:5432/wef"),
            "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
            "WEF_LOG_LEVEL": "info",
            "WEF_PUBLIC_PORT": str(public_port),
            "WEF_RELEASE_DIR": str(release_dir),
            "WEF_RELEASE_SHA": RELEASE_SHA,
            "WEF_ROOT": str(root),
            "WEF_WEB_IMAGE": "wef-web:local",
        }
        config_file.write_text(
            "".join(f"{key}={value}\n" for key, value in sorted(values.items())),
            encoding="utf-8",
        )
        config_file.chmod(0o600)

        project = f"wef-production-proof-{os.getpid()}"
        compose = [
            docker,
            "compose",
            "--project-name",
            project,
            "--env-file",
            str(config_file),
            "--file",
            str(release_dir / "compose.production.yaml"),
        ]
        environment = os.environ.copy()

        try:
            run(
                [*compose, "--profile", "operator", "run", "--rm", "db-permissions"],
                environment=environment,
            )
            run([*compose, "up", "--detach", "--wait", "db"], environment=environment)
            run(
                [*compose, "--profile", "operator", "run", "--rm", "migrate"],
                environment=environment,
            )
            run(
                [*compose, "--profile", "rehearsal", "run", "--rm", "seed"],
                environment=environment,
            )
            start_application(compose, environment=environment)
            run(
                [
                    shell,
                    str(REPOSITORY_ROOT / "scripts/deploy/smoke.sh"),
                    f"http://127.0.0.1:{public_port}",
                    RELEASE_SHA,
                ],
                environment=environment,
                capture_output=False,
            )

            run([*compose, "down", "--remove-orphans"], environment=environment)
            run(
                [*compose, "--profile", "operator", "run", "--rm", "db-permissions"],
                environment=environment,
            )
            run([*compose, "up", "--detach", "--wait", "db"], environment=environment)
            run(
                [*compose, "--profile", "operator", "run", "--rm", "migrate"],
                environment=environment,
            )
            start_application(compose, environment=environment)
            run(
                [
                    shell,
                    str(REPOSITORY_ROOT / "scripts/deploy/smoke.sh"),
                    f"http://127.0.0.1:{public_port}",
                    RELEASE_SHA,
                ],
                environment=environment,
                capture_output=False,
            )
        finally:
            subprocess.run(  # noqa: S603 - trusted docker command
                [*compose, "down", "--remove-orphans"],
                check=False,
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            subprocess.run(  # noqa: S603 - trusted bounded ownership reset
                [
                    *compose,
                    "--profile",
                    "operator",
                    "run",
                    "--rm",
                    "db-permissions",
                    "-R",
                    f"{os.getuid()}:{os.getgid()}",
                    "/var/lib/postgresql/data",
                ],
                check=False,
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )

    print("Production runtime and bind-mounted catalog persistence pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
