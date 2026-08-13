"""Exercise healthy activation and unhealthy rollback with isolated fake tools."""

from __future__ import annotations

# ruff: noqa: PLR0913, S101, T201
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.deploy.release_state import read_state

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = REPOSITORY_ROOT / "scripts/deploy/deploy.sh"
HEALTHY_SHA = "a" * 40
UNHEALTHY_SHA = "b" * 40
MIGRATION_FAILURE_SHA = "d" * 40
FAKE_DOCKER = """#!/bin/sh
if [ "${1:-}" = "info" ]; then
  exit 0
fi
if [ "${1:-}" = "compose" ]; then
  case " $* " in
    *" run "*" migrate "*)
      if [ "${WEF_FAKE_MIGRATION_FAIL:-0}" = "1" ]; then
        exit 1
      fi
      ;;
  esac
  case " $* " in
    *" ps "*) printf 'fake-edge-id\\n' ;;
  esac
  printf '%s\\n' "$*" >> "${WEF_FAKE_DOCKER_LOG}"
  exit 0
fi
exit 1
"""
FAKE_CURL = """#!/bin/sh
headers=""
output=""
url=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dump-header) shift; headers=$1 ;;
    --output) shift; output=$1 ;;
    --fail|--silent|--show-error) ;;
    *) url=$1 ;;
  esac
  shift
done
if [ -n "$headers" ]; then
  marker=$WEF_RELEASE_SHA
  if [ "$WEF_RELEASE_SHA" = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" ]; then
    marker=unhealthy
  fi
  printf 'HTTP/1.1 200 OK\\r\\nX-WEF-Release: %s\\r\\n\\r\\n' "$marker" > "$headers"
fi
if [ "$output" = "/dev/null" ] || [ -z "$output" ]; then
  exit 0
fi
case "$url" in
  */api/v1/map/locations*)
    payload='{"type":"FeatureCollection","features":[{}],"meta":{"feature_count":1}}'
    printf '%s\\n' "$payload" > "$output"
    ;;
  */)
    printf '%s\\n' '<h1>Find a place in Warsaw</h1><p>synthetic MVP fixtures</p>' > "$output"
    ;;
  *) printf '%s\\n' '{}' > "$output" ;;
esac
"""


def write_executable(path: Path, content: str) -> None:
    """Create one isolated fake command."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def prepare_release(root: Path, release_sha: str) -> tuple[Path, Path]:
    """Create inert release/config files accepted by the test-mode boundary."""
    release_dir = root / "releases" / release_sha
    config_dir = root / "secrets" / "releases" / release_sha
    release_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    shutil.copy2(REPOSITORY_ROOT / "infra/compose.production.yaml", release_dir)
    shutil.copy2(REPOSITORY_ROOT / "infra/Caddyfile.production", release_dir)
    config_file = config_dir / "production.env"
    values = {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "proof-password",
        "POSTGRES_USER": "wef",
        "WEF_ALLOW_SYNTHETIC_SEED": "true",
        "WEF_BACKEND_IMAGE": "wef-backend:local",
        "WEF_BIND_ADDRESS": "127.0.0.1",
        "WEF_DATABASE_URL": "postgresql+asyncpg://wef:proof-password@db:5432/wef",
        "WEF_LOG_LEVEL": "info",
        "WEF_PUBLIC_PORT": "43100",
        "WEF_RELEASE_DIR": str(release_dir),
        "WEF_RELEASE_SHA": release_sha,
        "WEF_ROOT": str(root),
        "WEF_WEB_IMAGE": "wef-web:local",
    }
    config_file.write_text(
        "".join(f"{key}={value}\n" for key, value in sorted(values.items())),
        encoding="utf-8",
    )
    config_file.chmod(0o600)
    return release_dir, config_file


def run_deploy(
    root: Path,
    release_dir: Path,
    config_file: Path,
    release_sha: str,
    environment: dict[str, str],
    *,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Run the real deploy/rollback control flow against isolated fake tools."""
    shell = shutil.which("sh")
    if shell is None:
        msg = "a POSIX shell is required"
        raise RuntimeError(msg)
    return subprocess.run(  # noqa: S603 - shell resolved from trusted PATH
        [
            shell,
            str(DEPLOY_SCRIPT),
            str(root),
            str(release_dir),
            str(config_file),
            release_sha,
            "43100",
        ],
        check=check,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def main() -> int:
    """Prove activation and restoration without Docker or host mutation."""
    with tempfile.TemporaryDirectory(prefix="wef-deploy-proof-") as directory:
        root = Path(directory) / "wef"
        fake_bin = Path(directory) / "bin"
        for relative in (
            "postgres",
            "media",
            "caddy-data",
            "state",
            "secrets/releases",
            "releases",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)
        fake_bin.mkdir()
        write_executable(fake_bin / "docker", FAKE_DOCKER)
        write_executable(fake_bin / "curl", FAKE_CURL)
        write_executable(fake_bin / "flock", "#!/bin/sh\nexit 0\n")
        write_executable(fake_bin / "ss", "#!/bin/sh\nexit 0\n")
        meminfo = Path(directory) / "meminfo"
        meminfo.write_text("MemAvailable: 8388608 kB\n", encoding="utf-8")

        environment = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "WEF_DEPLOY_SKIP_PULL": "1",
            "WEF_DEPLOY_TEST_MODE": "1",
            "WEF_FAKE_DOCKER_LOG": str(Path(directory) / "docker.log"),
            "WEF_MEMINFO_FILE": str(meminfo),
            "WEF_MIN_AVAILABLE_MEMORY_KB": "1",
            "WEF_MIN_FREE_KB": "1",
            "WEF_SEED_REHEARSAL": "1",
        }

        healthy_dir, healthy_config = prepare_release(root, HEALTHY_SHA)
        healthy = run_deploy(
            root,
            healthy_dir,
            healthy_config,
            HEALTHY_SHA,
            environment,
            check=True,
        )
        assert "Activated WEF release" in healthy.stdout
        assert read_state(root / "state/current.json")["release_sha"] == HEALTHY_SHA

        unhealthy_dir, unhealthy_config = prepare_release(root, UNHEALTHY_SHA)
        unhealthy = run_deploy(
            root,
            unhealthy_dir,
            unhealthy_config,
            UNHEALTHY_SHA,
            environment,
            check=False,
        )
        assert unhealthy.returncode == 1
        assert "Previous WEF application release restored" in unhealthy.stderr
        assert read_state(root / "state/current.json")["release_sha"] == HEALTHY_SHA
        assert read_state(root / "state/previous.json")["release_sha"] == HEALTHY_SHA

        migration_dir, migration_config = prepare_release(root, MIGRATION_FAILURE_SHA)
        migration_failure = run_deploy(
            root,
            migration_dir,
            migration_config,
            MIGRATION_FAILURE_SHA,
            {**environment, "WEF_FAKE_MIGRATION_FAIL": "1"},
            check=False,
        )
        assert migration_failure.returncode == 1
        assert "existing application release was not replaced" in migration_failure.stderr
        assert read_state(root / "state/current.json")["release_sha"] == HEALTHY_SHA

    print("Healthy activation and unhealthy application rollback pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
