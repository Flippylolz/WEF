"""Atomic historical-candidate activation under the WEF deploy lock."""

from __future__ import annotations

# ruff: noqa: T201
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from scripts.deploy.candidate_config import candidate_paths
from scripts.deploy.release_state import write_json_state
from scripts.deploy.validate_release import parse_environment

DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_PUBLIC_DB = "wef"
DEFAULT_CANDIDATE_DB = "wef_hist_candidate"
IDENTITY_TABLES = ("users", "auth_sessions")
ACTIVATION_STATE = "historical-activation.json"
PREVIOUS_ACTIVATION_STATE = "historical-activation.previous.json"


class HistoricalActivationError(RuntimeError):
    """Raised when historical activation cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class ActivationPointers:
    """One complete public data-plane configuration."""

    database_name: str
    database_url: str
    media_public: str
    media_originals: str
    bundle_checksum: str | None = None


@dataclass(frozen=True, slots=True)
class ActivationContext:
    """Inputs for one historical activation or rollback."""

    root: Path
    config_file: Path
    bundle_checksum: str
    candidate_database: str = DEFAULT_CANDIDATE_DB
    public_database: str = DEFAULT_PUBLIC_DB
    compose_project: str = "wef-production"
    db_container: str = "wef-production-db-1"
    postgres_user: str = "wef"


def rewrite_database_url(database_url: str, database_name: str) -> str:
    """Return a PostgreSQL URL targeting database_name on the same host."""
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        msg = f"unsafe database name: {database_name!r}"
        raise HistoricalActivationError(msg)
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
        msg = "database URL must be postgresql(+asyncpg)"
        raise HistoricalActivationError(msg)
    return urlunparse(parsed._replace(path=f"/{quote(database_name, safe='')}"))


def database_name_from_url(database_url: str) -> str:
    """Extract the database name from a PostgreSQL URL path."""
    parsed = urlparse(database_url)
    name = parsed.path.lstrip("/")
    if not name or not DATABASE_NAME_PATTERN.fullmatch(name):
        msg = "database URL path must contain a safe database name"
        raise HistoricalActivationError(msg)
    return name


def redact_database_url(database_url: str) -> str:
    """Hide credentials when emitting activation evidence."""
    parsed = urlparse(database_url)
    if parsed.password is None:
        return database_url
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    user = parsed.username or ""
    netloc = f"{user}:***@{host}" if user else f"***@{host}"
    return urlunparse(parsed._replace(netloc=netloc))


def pointers_for_evidence(pointers: ActivationPointers) -> dict[str, str | None]:
    """Return activation pointers safe for logs and state files."""
    payload = asdict(pointers)
    payload["database_url"] = redact_database_url(pointers.database_url)
    return payload


def update_environment_values(
    values: dict[str, str],
    *,
    database_name: str,
) -> dict[str, str]:
    """Return a copy of release values pointed at database_name."""
    updated = dict(values)
    updated["POSTGRES_DB"] = database_name
    updated["WEF_DATABASE_URL"] = rewrite_database_url(
        values["WEF_DATABASE_URL"],
        database_name,
    )
    return updated


def write_environment(path: Path, values: dict[str, str]) -> None:
    """Atomically rewrite one mode-0600 env file."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            for key, value in sorted(values.items()):
                stream.write(f"{key}={value}\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    path.chmod(0o600)


def media_roots_for_checksum(root: Path, bundle_checksum: str) -> tuple[Path, Path]:
    """Return candidate public/originals media roots for one checksum."""
    if not CHECKSUM_PATTERN.fullmatch(bundle_checksum):
        msg = "bundle checksum must be 64 lowercase hex characters"
        raise HistoricalActivationError(msg)
    paths = candidate_paths(root, bundle_checksum)
    return paths.public_derivatives, paths.restricted_originals


def validate_candidate_media(root: Path, bundle_checksum: str) -> None:
    """Require non-empty candidate media roots before activation."""
    public_root, originals_root = media_roots_for_checksum(root, bundle_checksum)
    if not public_root.is_dir() or not any(public_root.iterdir()):
        msg = f"candidate public media missing or empty: {public_root}"
        raise HistoricalActivationError(msg)
    if not originals_root.is_dir() or not any(originals_root.iterdir()):
        msg = f"candidate originals media missing or empty: {originals_root}"
        raise HistoricalActivationError(msg)


def _is_symlink_to(path: Path, target: Path) -> bool:
    return path.is_symlink() and path.resolve() == target.resolve()


def point_media_roots(
    root: Path,
    *,
    bundle_checksum: str,
    backup_suffix: str,
) -> ActivationPointers:
    """Point host media roots at candidate paths, retaining prior directories."""
    public_target, originals_target = media_roots_for_checksum(root, bundle_checksum)
    validate_candidate_media(root, bundle_checksum)
    media = root / "media"
    public = media / "public"
    originals = media / "originals"
    public_backup = media / f"public.{backup_suffix}"
    originals_backup = media / f"originals.{backup_suffix}"

    if public.exists() or public.is_symlink():
        if public_backup.exists() or public_backup.is_symlink():
            msg = f"media backup already exists: {public_backup}"
            raise HistoricalActivationError(msg)
        public.rename(public_backup)
    if originals.exists() or originals.is_symlink():
        if originals_backup.exists() or originals_backup.is_symlink():
            msg = f"media backup already exists: {originals_backup}"
            raise HistoricalActivationError(msg)
        originals.rename(originals_backup)

    public.symlink_to(public_target)
    originals.symlink_to(originals_target)
    if not _is_symlink_to(public, public_target) or not _is_symlink_to(
        originals,
        originals_target,
    ):
        msg = "media symlink verification failed"
        raise HistoricalActivationError(msg)
    return ActivationPointers(
        database_name="",
        database_url="",
        media_public=str(public_target),
        media_originals=str(originals_target),
        bundle_checksum=bundle_checksum,
    )


def restore_media_roots(root: Path, *, backup_suffix: str) -> None:
    """Restore host media roots from the named backup directories."""
    media = root / "media"
    public = media / "public"
    originals = media / "originals"
    public_backup = media / f"public.{backup_suffix}"
    originals_backup = media / f"originals.{backup_suffix}"
    if public.is_symlink():
        public.unlink()
    elif public.is_dir():
        shutil.rmtree(public)
    if originals.is_symlink():
        originals.unlink()
    elif originals.is_dir():
        shutil.rmtree(originals)
    if not public_backup.exists() and not public_backup.is_symlink():
        msg = f"missing media backup: {public_backup}"
        raise HistoricalActivationError(msg)
    if not originals_backup.exists() and not originals_backup.is_symlink():
        msg = f"missing media backup: {originals_backup}"
        raise HistoricalActivationError(msg)
    public_backup.rename(public)
    originals_backup.rename(originals)


def current_pointers(config_file: Path, root: Path) -> ActivationPointers:
    """Read the active database URL and resolved media root paths."""
    values = parse_environment(config_file)
    database_url = values["WEF_DATABASE_URL"]
    public = root / "media" / "public"
    originals = root / "media" / "originals"
    return ActivationPointers(
        database_name=database_name_from_url(database_url),
        database_url=database_url,
        media_public=str(public.resolve() if public.exists() else public),
        media_originals=str(originals.resolve() if originals.exists() else originals),
    )


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        msg = f"command failed ({result.returncode}): {' '.join(command)}"
        if detail:
            msg = f"{msg}\n{detail}"
        raise HistoricalActivationError(msg)
    return result


def psql(context: ActivationContext, database: str, sql: str) -> str:
    """Run one SQL statement inside the production PostGIS container."""
    result = _run(
        [
            "docker",
            "exec",
            "-i",
            context.db_container,
            "psql",
            "-U",
            context.postgres_user,
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-tAc",
            sql,
        ],
    )
    return result.stdout.strip()


def identity_fingerprint(context: ActivationContext, database: str) -> str:
    """Return a non-secret identity/session fingerprint for freshness checks."""
    return psql(
        context,
        database,
        "SELECT coalesce((SELECT count(*)::text FROM users), '0') || ':' || "
        "coalesce((SELECT count(*)::text FROM auth_sessions), '0') || ':' || "
        "coalesce((SELECT md5(string_agg(id::text, ',' ORDER BY id)) FROM users), '')",
    )


def sync_identity_tables(context: ActivationContext) -> None:
    """Replace candidate identity tables with the current production snapshot."""
    for table in IDENTITY_TABLES:
        psql(context, context.candidate_database, f"TRUNCATE {table} CASCADE")
    dump = _run(
        [
            "docker",
            "exec",
            context.db_container,
            "pg_dump",
            "-U",
            context.postgres_user,
            "-d",
            context.public_database,
            "--data-only",
            "--no-owner",
            "--no-privileges",
            *[item for table in IDENTITY_TABLES for item in ("-t", table)],
        ],
    )
    restore_command = [
        "docker",
        "exec",
        "-i",
        context.db_container,
        "psql",
        "-U",
        context.postgres_user,
        "-d",
        context.candidate_database,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    restore = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        restore_command,
        input=dump.stdout,
        check=False,
        text=True,
        capture_output=True,
    )
    if restore.returncode != 0:
        detail = (restore.stderr or restore.stdout or "").strip()
        msg = "identity sync into candidate failed"
        if detail:
            msg = f"{msg}\n{detail}"
        raise HistoricalActivationError(msg)
    if identity_fingerprint(context, context.public_database) != identity_fingerprint(
        context,
        context.candidate_database,
    ):
        msg = "identity fingerprint mismatch after sync"
        raise HistoricalActivationError(msg)


def migrate_candidate(context: ActivationContext, values: dict[str, str]) -> None:
    """Run Alembic upgrade against the candidate database URL."""
    candidate_url = rewrite_database_url(
        values["WEF_DATABASE_URL"],
        context.candidate_database,
    )
    compose_file = context.root / "releases" / "current" / "compose.production.yaml"
    if not compose_file.is_file():
        # Fallback: release dir may store compose beside current symlink target.
        compose_file = Path(values["WEF_RELEASE_DIR"]) / "compose.production.yaml"
    if not compose_file.is_file():
        msg = f"compose.production.yaml not found for migrate: {compose_file}"
        raise HistoricalActivationError(msg)
    _run(
        [
            "docker",
            "compose",
            "--project-name",
            context.compose_project,
            "--env-file",
            str(context.config_file),
            "-f",
            str(compose_file),
            "--profile",
            "operator",
            "run",
            "--rm",
            "-e",
            f"WEF_DATABASE_URL={candidate_url}",
            "migrate",
        ],
    )


def resolve_compose_files(
    context: ActivationContext, values: dict[str, str]
) -> tuple[Path, Path | None]:
    """Return base production compose and optional shared-edge cutover overlay."""
    compose_file = Path(values["WEF_RELEASE_DIR"]) / "compose.production.yaml"
    if not compose_file.is_file():
        compose_file = context.root / "releases" / "current" / "compose.production.yaml"
    if not compose_file.is_file():
        msg = f"compose.production.yaml not found: {compose_file}"
        raise HistoricalActivationError(msg)
    cutover = compose_file.parent / "compose.production-cutover.yaml"
    return compose_file, cutover if cutover.is_file() else None


def recreate_application(context: ActivationContext, values: dict[str, str]) -> None:
    """Recreate API/web/edge/media-edge and reconnect shared edge upstreams."""
    compose_file, cutover = resolve_compose_files(context, values)
    common = [
        "docker",
        "compose",
        "--project-name",
        context.compose_project,
        "--env-file",
        str(context.config_file),
        "-f",
        str(compose_file),
    ]
    _run(
        [
            *common,
            "up",
            "--detach",
            "--force-recreate",
            "--wait",
            "api",
            "web",
            "edge",
        ],
    )
    if cutover is not None:
        # media-edge only exists on the cutover overlay; recreate after media
        # symlinks change so Docker remounts the candidate public tree.
        _run(
            [
                *common,
                "-f",
                str(cutover),
                "up",
                "--detach",
                "--force-recreate",
                "--wait",
                "media-edge",
            ],
        )
    reconnect_shared_edge()


def reconnect_shared_edge() -> None:
    """Attach recreated WEF containers to the shared Nginx network when present."""
    script = Path("/home/nuc/wef-shared-edge/ops/reconnect-wef-upstreams.sh")
    if script.is_file():
        _run(["bash", str(script)])


def _probe_public_https(base_url: str, root: Path) -> str | None:
    """Return an error string when a public smoke probe fails, else None."""
    live = _run(["curl", "-fsS", f"{base_url}/api/v1/health/live"])
    if "live" not in live.stdout:
        return f"live health unexpected: {live.stdout!r}"
    ready = _run(["curl", "-fsS", f"{base_url}/api/v1/health/ready"])
    if "ready" not in ready.stdout:
        return f"ready health unexpected: {ready.stdout!r}"
    locations = _run(
        [
            "curl",
            "-fsS",
            f"{base_url}/api/v1/map/locations?bbox=20.9,52.1,21.2,52.4",
        ],
    )
    if "FeatureCollection" not in locations.stdout:
        return "map locations smoke failed"
    public = root / "media" / "public"
    sample = next(public.rglob("*.webp"), None) or next(public.rglob("*.jpg"), None)
    if sample is None:
        return "no public derivative sample found for media smoke"
    relative = sample.resolve().relative_to(public.resolve()).as_posix()
    media = _run(
        ["curl", "-fsS", "-o", "/dev/null", "-w", "%{http_code}", f"{base_url}/media/{relative}"],
    )
    if media.stdout.strip() != "200":
        return f"public media smoke failed: HTTP {media.stdout.strip()}"
    return None


def smoke_public_https(
    root: Path,
    base_url: str = "https://2fa54e2405.duckdns.org",
    *,
    attempts: int = 12,
    delay_seconds: float = 5.0,
) -> None:
    """Fail closed unless public HTTPS health, map pins, and media respond."""
    last_error = "unknown smoke failure"
    for attempt in range(1, attempts + 1):
        last_error = _probe_public_https(base_url, root) or ""
        if not last_error:
            return
        if attempt == attempts:
            break
        time.sleep(delay_seconds)
    msg = f"public HTTPS smoke failed after {attempts} attempts: {last_error}"
    raise HistoricalActivationError(msg)


def activate(context: ActivationContext, *, dry_run: bool = False) -> dict[str, object]:
    """Prepare, optionally apply, and record one historical activation."""
    validate_candidate_media(context.root, context.bundle_checksum)
    values = parse_environment(context.config_file)
    before = current_pointers(context.config_file, context.root)
    if before.database_name == context.candidate_database:
        msg = "production already points at the candidate database"
        raise HistoricalActivationError(msg)

    public_fp = identity_fingerprint(context, context.public_database)
    candidate_fp = identity_fingerprint(context, context.candidate_database)
    plan = {
        "before": pointers_for_evidence(before),
        "bundle_checksum": context.bundle_checksum,
        "candidate_database": context.candidate_database,
        "public_identity_fingerprint": public_fp,
        "candidate_identity_fingerprint": candidate_fp,
        "identity_sync_required": public_fp != candidate_fp,
        "dry_run": dry_run,
    }
    if dry_run:
        return plan

    lock = context.root / "state" / "deploy.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            msg = "another WEF deployment holds the host lock"
            raise HistoricalActivationError(msg) from error

        state_dir = context.root / "state"
        previous_path = state_dir / PREVIOUS_ACTIVATION_STATE
        current_path = state_dir / ACTIVATION_STATE
        backup_suffix = "pre-historical-activation"
        write_json_state(previous_path, plan)

        migrate_candidate(context, values)
        if public_fp != identity_fingerprint(context, context.candidate_database):
            sync_identity_tables(context)

        updated = update_environment_values(
            values,
            database_name=context.candidate_database,
        )
        write_environment(context.config_file, updated)
        point_media_roots(
            context.root,
            bundle_checksum=context.bundle_checksum,
            backup_suffix=backup_suffix,
        )
        try:
            recreate_application(context, updated)
            smoke_public_https(context.root)
        except Exception:
            write_environment(context.config_file, values)
            restore_media_roots(context.root, backup_suffix=backup_suffix)
            recreate_application(context, values)
            raise

        after = current_pointers(context.config_file, context.root)
        result = {
            **plan,
            "after": pointers_for_evidence(after),
            "backup_suffix": backup_suffix,
            "status": "activated",
        }
        write_json_state(current_path, result)
        return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for dry-run or live historical activation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--bundle-checksum", required=True)
    parser.add_argument("--candidate-database", default=DEFAULT_CANDIDATE_DB)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--activate", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.dry_run == arguments.activate:
        parser.error("exactly one of --dry-run or --activate is required")
    context = ActivationContext(
        root=arguments.root,
        config_file=arguments.config_file,
        bundle_checksum=arguments.bundle_checksum,
        candidate_database=arguments.candidate_database,
    )
    try:
        result = activate(context, dry_run=arguments.dry_run)
    except HistoricalActivationError as error:
        print(f"historical_activation: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
