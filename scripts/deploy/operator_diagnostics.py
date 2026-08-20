"""Redacted operator diagnostics for the WEF production host."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


class OperatorDiagnosticsError(RuntimeError):
    """Raised when diagnostics cannot be collected safely."""


SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "database_url",
    "api_key",
    "source_text",
    "contact",
)


@dataclass(frozen=True, slots=True)
class DiskUsage:
    """One filesystem usage sample for a WEF path."""

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    used_ratio: float


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"expected object JSON in {path}"
        raise OperatorDiagnosticsError(msg)
    return payload


def redact_mapping(value: object) -> object:
    """Recursively drop sensitive keys from nested JSON-like values."""
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                redacted[str(key)] = "***"
                continue
            redacted[str(key)] = redact_mapping(item)
        return redacted
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    return value


def disk_usage_for(path: Path) -> DiskUsage:
    """Return usage for the filesystem that holds path."""
    usage = shutil.disk_usage(path)
    used_ratio = 0.0 if usage.total == 0 else usage.used / usage.total
    return DiskUsage(
        path=str(path),
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
        used_ratio=round(used_ratio, 4),
    )


def load_release(root: Path) -> dict[str, Any] | None:
    """Return the active release pointer without secret paths expanded."""
    current = _read_json(root / "state" / "current.json")
    if current is None:
        return None
    return {
        "release_sha": current.get("release_sha"),
        "public_port": current.get("public_port"),
        "release_dir_name": Path(str(current.get("release_dir", ""))).name or None,
    }


def load_last_failure(root: Path) -> dict[str, Any] | None:
    """Return the last recorded deploy failure summary."""
    failure = _read_json(root / "state" / "last-failure.json")
    if failure is None:
        return None
    return redact_mapping(
        {
            "candidate_release_sha": failure.get("candidate_release_sha"),
            "failure_reason": failure.get("failure_reason"),
            "recorded_at": failure.get("recorded_at"),
            "restored_release_sha": failure.get("restored_release_sha"),
        },
    )


def query_last_successful_import(
    *,
    db_container: str,
    database: str,
    postgres_user: str,
) -> dict[str, Any] | None:
    """Return aggregate identity of the newest succeeded complete import run."""
    sql = (
        "SELECT status, stage, pipeline_version, left(source_checksum, 12), "
        "finished_at::text "
        "FROM complete_import_runs "
        "WHERE status = 'succeeded' "
        "ORDER BY finished_at DESC NULLS LAST "
        "LIMIT 1;"
    )
    docker = shutil.which("docker")
    if docker is None:
        msg = "docker executable not found on PATH"
        raise OperatorDiagnosticsError(msg)
    result = subprocess.run(  # noqa: S603 - absolute docker path with fixed argv
        [
            docker,
            "exec",
            db_container,
            "psql",
            "-U",
            postgres_user,
            "-d",
            database,
            "-tAc",
            sql,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        msg = f"import query failed ({result.returncode}): {detail}"
        raise OperatorDiagnosticsError(msg)
    line = result.stdout.strip()
    if not line:
        return None
    status, stage, pipeline_version, checksum_prefix, finished_at = line.split("|", 4)
    return {
        "status": status,
        "stage": stage,
        "pipeline_version": pipeline_version,
        "source_checksum_prefix": checksum_prefix,
        "finished_at": finished_at or None,
    }


def collect_diagnostics(
    root: Path,
    *,
    db_container: str | None = None,
    database: str = "wef_hist_candidate",
    postgres_user: str = "wef",
) -> dict[str, Any]:
    """Build one redacted diagnostics document for operators."""
    if not root.is_dir():
        msg = f"WEF root missing: {root}"
        raise OperatorDiagnosticsError(msg)
    paths = (
        root,
        root / "media",
        root / "media" / "public",
        root / "postgres",
        root / "state",
    )
    disk = [asdict(disk_usage_for(path if path.exists() else root)) for path in paths]
    payload: dict[str, Any] = {
        "schema": "wef-operator-diagnostics@1",
        "captured_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "root": str(root),
        "release": load_release(root),
        "last_failure": load_last_failure(root),
        "disk": disk,
        "last_successful_import": None,
    }
    if db_container:
        payload["last_successful_import"] = query_last_successful_import(
            db_container=db_container,
            database=database,
            postgres_user=postgres_user,
        )
    return cast("dict[str, Any]", redact_mapping(payload))


def main(argv: list[str] | None = None) -> int:
    """CLI entry for operator diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/home/nuc/wef"))
    parser.add_argument("--db-container", default="wef-production-db-1")
    parser.add_argument("--database", default="wef_hist_candidate")
    parser.add_argument("--postgres-user", default="wef")
    parser.add_argument(
        "--skip-import-query",
        action="store_true",
        help="Omit docker/psql import-run lookup (fixture/unit tests).",
    )
    arguments = parser.parse_args(argv)
    try:
        payload = collect_diagnostics(
            arguments.root,
            db_container=None if arguments.skip_import_query else arguments.db_container,
            database=arguments.database,
            postgres_user=arguments.postgres_user,
        )
    except OperatorDiagnosticsError as error:
        print(f"operator_diagnostics: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
