"""Exercise healthy activation and unhealthy rollback with isolated fake tools."""

from __future__ import annotations

import json

# ruff: noqa: PLR0913, PLR0915, PLR2004, S101, T201
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.deploy.compare_server_inventory import EXPECTED_WEF_PATHS
from scripts.deploy.release_state import read_failure_state, read_state
from scripts.deploy.verify_rollback_rehearsal import verify

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = REPOSITORY_ROOT / "scripts/deploy/deploy.sh"
HEALTHY_SHA = "a" * 40
UNHEALTHY_SHA = "b" * 40
FORCED_FAILURE_SHA = "c" * 40
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
  {
    printf 'HTTP/1.1 200 OK\\r\\n'
    printf 'Content-Type: application/javascript\\r\\n'
    printf 'X-WEF-Release: %s\\r\\n\\r\\n' "$marker"
  } > "$headers"
fi
if [ "$output" = "/dev/null" ] || [ -z "$output" ]; then
  exit 0
fi
case "$url" in
  */api/v1/health/live)
    printf '%s\\n' '{"status":"live"}' > "$output"
    ;;
  */api/v1/health/ready)
    printf '%s\\n' '{"status":"ready"}' > "$output"
    ;;
  */api/v1/map/locations*)
    payload='{"type":"FeatureCollection","features":[{}],"meta":{"feature_count":1}}'
    printf '%s\\n' "$payload" > "$output"
    ;;
  */api/v1/filter-facets)
    printf '%s\\n' '{"districts":["wola"],"rooms":[2]}' > "$output"
    ;;
  */api/v1/locations/*/offers*)
    python3 - "$output" <<'PY'
import json
import sys

payload = {
    "matching_count": 1,
    "total_count": 1,
    "items": [
        {
            "parking_price_min_minor": 1,
            "storage_price_min_minor": 1,
        },
    ],
}
with open(sys.argv[1], "w", encoding="utf-8") as output_file:
    json.dump(payload, output_file)
PY
    ;;
  */data/warsaw-districts.geojson)
    python3 - "$output" <<'PY'
import json
import sys

feature = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": []},
    "properties": {"name": "Synthetic district"},
}
payload = {"type": "FeatureCollection", "features": [feature] * 18}
with open(sys.argv[1], "w", encoding="utf-8") as output_file:
    json.dump(payload, output_file)
PY
    ;;
  */vendor/maplibre/maplibre-gl-worker.mjs)
    printf '%s\\n' 'import "./maplibre-gl-shared.mjs";' > "$output"
    ;;
  */vendor/maplibre/maplibre-gl-shared.mjs)
    printf '%s\\n' 'export {};' > "$output"
    ;;
  https://tiles.openfreemap.org/styles/liberty)
    printf '%s\\n' '{"version":8,"sources":{"openmaptiles":{}},"layers":[{}]}' > "$output"
    ;;
  */)
    short_sha=$(printf '%.7s' "$WEF_RELEASE_SHA")
    page='<h1>Apartments and houses for sale in Warsaw</h1>'
    page="${page}<p>synthetic MVP fixtures</p>"
    page="${page}<div>version: <code>${short_sha}</code></div>"
    printf '%s\\n' "$page" > "$output"
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
    (release_dir / "release-manifest.json").write_text(
        json.dumps(
            {
                "schema": "wef-release@1",
                "source_sha": release_sha,
                "source_timestamp": "2026-08-13T00:00:00+00:00",
                "migration_revision": "20260812_0001",
                "images": {
                    "backend": f"sha256:{'a' * 64}",
                    "web": f"sha256:{'b' * 64}",
                },
            },
        ),
        encoding="utf-8",
    )
    config_file = config_dir / "production.env"
    values = {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "proof-password",
        "POSTGRES_USER": "wef",
        "WEF_ADMIN_SESSION_SECRET": "rollback-proof-admin-session-secret-0123456789",
        "WEF_ALLOW_SYNTHETIC_SEED": "true",
        "WEF_BACKEND_IMAGE": "wef-backend:local",
        "WEF_BIND_ADDRESS": "127.0.0.1",
        "WEF_DATABASE_URL": "postgresql+asyncpg://wef:proof-password@db:5432/wef",
        "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
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
        sentinels = {
            root / "postgres/persistence.sentinel": "postgres-survives\n",
            root / "media/persistence.sentinel": "media-survives\n",
            root / "caddy-data/persistence.sentinel": "caddy-survives\n",
        }
        for path, value in sentinels.items():
            path.write_text(value, encoding="utf-8")

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
        assert (root / "releases/current").resolve() == healthy_dir.resolve()
        assert (root / "secrets/current").resolve() == healthy_config.parent.resolve()
        for relative in ("media/originals", "media/public", "media/reports"):
            runtime_directory = root / relative
            assert runtime_directory.is_dir()
            assert not runtime_directory.is_symlink()
            assert runtime_directory.stat().st_mode & 0o777 == 0o750

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
        failure = read_failure_state(root / "state/last-failure.json")
        assert failure["candidate_release_sha"] == UNHEALTHY_SHA
        assert failure["restored_release_sha"] == HEALTHY_SHA
        assert (root / "releases/current").resolve() == healthy_dir.resolve()
        assert (root / "secrets/current").resolve() == healthy_config.parent.resolve()

        forced_dir, forced_config = prepare_release(root, FORCED_FAILURE_SHA)
        forced_failure = run_deploy(
            root,
            forced_dir,
            forced_config,
            FORCED_FAILURE_SHA,
            {**environment, "WEF_FORCE_ROLLBACK_REHEARSAL": "1"},
            check=False,
        )
        assert forced_failure.returncode == 42
        assert "Forcing the reviewed rollback rehearsal" in forced_failure.stderr
        assert "Previous WEF application release restored" in forced_failure.stderr
        assert read_state(root / "state/current.json")["release_sha"] == HEALTHY_SHA
        failure = read_failure_state(root / "state/last-failure.json")
        assert failure["candidate_release_sha"] == FORCED_FAILURE_SHA
        assert failure["restored_release_sha"] == HEALTHY_SHA

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
        for path, value in sentinels.items():
            assert path.read_text(encoding="utf-8") == value
        docker_log = (Path(directory) / "docker.log").read_text(encoding="utf-8")
        assert "down -v" not in docker_log
        assert "alembic downgrade" not in docker_log

        uid = os.getuid()
        common_inventory = {
            "schema": "wef-server-inventory@1",
            "hostname": "proof-host",
            "uid": uid,
            "containers": [],
            "listeners": ["tcp 0.0.0.0:3000"],
            "existing_http": {"3000": 200, "8080": 200},
            "resources": {"disk_free_bytes": 1, "memory_available_kb": 1},
            "wef_paths": [
                {
                    "path": path,
                    "kind": "directory",
                    "mode": mode,
                    "uid": uid,
                    "gid": os.getgid(),
                }
                for path, mode in EXPECTED_WEF_PATHS.items()
            ],
        }
        before_inventory = {**common_inventory, "compose_projects": []}
        after_inventory = {
            **common_inventory,
            "compose_projects": [{"Name": "wef-production"}],
            "containers": [
                {
                    "name": f"wef-production-{service}-1",
                    "state": "running",
                    "health": "healthy",
                }
                for service in ("api", "db", "edge", "web")
            ],
            "listeners": ["tcp 0.0.0.0:3000", "tcp 0.0.0.0:3100"],
        }
        before_path = Path(directory) / "before.json"
        after_path = Path(directory) / "after.json"
        before_path.write_text(json.dumps(before_inventory), encoding="utf-8")
        after_path.write_text(json.dumps(after_inventory), encoding="utf-8")
        verify(
            root,
            HEALTHY_SHA,
            FORCED_FAILURE_SHA,
            before_path,
            after_path,
        )

    print("Healthy activation and unhealthy application rollback pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
