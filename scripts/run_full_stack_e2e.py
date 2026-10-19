"""Build, seed, exercise and remove one isolated synthetic browser stack."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from http import HTTPStatus
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TRACE_ENTRIES = 2000

PROFILES = ("chromium", "firefox", "webkit", "mobile-chrome", "mobile-safari")


def run(command: list[str], environment: dict[str, str], log: Path, *, timeout: int = 1200) -> int:
    """Run repository-owned argv without a shell; keep raw logs out of artifacts."""
    with log.open("a") as output:
        return subprocess.run(  # noqa: S603 - fixed repository argv, no shell
            command,
            cwd=ROOT,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        ).returncode


def safe_artifacts(results: Path, destination: Path, forbidden: tuple[str, ...]) -> int:
    """Fail closed on credential/contact payloads before selecting failure evidence."""
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in results.rglob("*"):
        if not source.is_file() or source.suffix not in {".png", ".zip"}:
            continue
        if source.stat().st_size > 50 * 1024 * 1024:
            msg = "Oversized browser artifact"
            raise ValueError(msg)
        blobs = [source.read_bytes()]
        if source.suffix == ".zip":
            with zipfile.ZipFile(source) as archive:
                if (
                    len(archive.infolist()) > MAX_TRACE_ENTRIES
                    or sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024
                ):
                    msg = "Oversized browser trace"
                    raise ValueError(msg)
                blobs.extend(archive.read(item) for item in archive.namelist())
        if any(value.encode() in blob for value in forbidden for blob in blobs):
            msg = "Browser artifact contains forbidden private material"
            raise ValueError(msg)
        target = destination / source.relative_to(results)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        count += 1
    return count


def wait_for_web(base_url: str) -> None:
    """Wait only for the generated loopback web address."""
    deadline = time.monotonic() + 60
    while True:
        try:
            with urllib.request.urlopen(base_url, timeout=2) as response:  # noqa: S310 - generated loopback URL only
                if response.status == HTTPStatus.OK:
                    break
        except (OSError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                msg = "Disposable web server did not become ready"
                raise RuntimeError(msg) from None
            time.sleep(1)


def main() -> int:
    """Exercise the required matrix; all exits clean up only the generated project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=PROFILES, action="append")
    args = parser.parse_args()
    project = f"wef-e2e-{secrets.token_hex(6)}"
    if re.fullmatch(r"wef-e2e-[a-f0-9]{12}", project) is None:
        msg = "Invalid disposable project"
        raise ValueError(msg)
    release = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()  # noqa: S607 - fixed local Git query
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    workspace = ROOT / "tmp" / project
    workspace.mkdir(parents=True, exist_ok=False)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("WEF_", "COMPOSE_", "POSTGRES_", "TEST_DATABASE_"))
    }
    environment.pop("NO_COLOR", None)
    environment.update(
        {
            "WEF_E2E_PROJECT": project,
            "WEF_E2E_CONTACT_KEY": secrets.token_hex(32),
            "WEF_E2E_HMAC_KEY": secrets.token_hex(32),
            "WEF_E2E_PASSWORD": secrets.token_urlsafe(24),
            "WEF_E2E_RELEASE": release,
            "WEF_E2E_PORT": str(port),
            "WEF_E2E_BASE_URL": f"http://127.0.0.1:{port}",
            "WEF_E2E_OUTPUT_DIR": str(workspace / "results"),
        }
    )
    compose = ["docker", "compose", "-p", project, "-f", "infra/e2e/compose.yaml"]
    log = workspace / "private-run.log"
    artifact_root = ROOT / "tmp" / "e2e-artifacts"
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    result = 1
    try:
        print("Building isolated PostGIS/API/web browser stack…", flush=True)  # noqa: T201
        result = run(
            [*compose, "up", "--build", "--detach", "--wait", "--wait-timeout", "180"],
            environment,
            log,
        )
        if result:
            return result
        wait_for_web(environment["WEF_E2E_BASE_URL"])
        print("Running real browser matrix with no critical route mocks…", flush=True)  # noqa: T201
        command = [
            "pnpm",
            "--filter",
            "web",
            "exec",
            "playwright",
            "test",
            "--config",
            "playwright.full-stack.config.ts",
        ]
        for profile in args.project or []:
            command.extend(["--project", profile])
        result = run(command, environment, log)
        forbidden = (
            environment["WEF_E2E_PASSWORD"],
            environment["WEF_E2E_CONTACT_KEY"],
            environment["WEF_E2E_HMAC_KEY"],
            "+12025550123",
            "wef_session",
            "value_ciphertext",
            "hashed_password",
            "raw_payload_json",
        )
        count = safe_artifacts(workspace / "results", artifact_root, forbidden)
        artifact_root.mkdir(parents=True, exist_ok=True)
        (artifact_root / "run.json").write_text(
            json.dumps(
                {
                    "release": release,
                    "profiles": args.project or list(PROFILES),
                    "exit_code": result,
                    "failure_artifacts": count,
                    "dataset": "e14-synthetic-v1",
                },
                indent=2,
            )
            + "\n"
        )
        print(f"Browser matrix exit {result}; {count} scanned failure artifacts.", flush=True)  # noqa: T201
        return result
    finally:
        cleanup = run(
            [*compose, "down", "--volumes", "--remove-orphans"], environment, log, timeout=120
        )
        if cleanup:
            msg = f"Disposable project cleanup failed: {project}"
            raise RuntimeError(msg)
        if result:
            print(f"Private diagnostic log: {log}", flush=True)  # noqa: T201


if __name__ == "__main__":
    raise SystemExit(main())
