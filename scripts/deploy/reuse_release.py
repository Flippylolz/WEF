"""Reuse only a successful main-push release with exact source and verification identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts.deploy.release_report import read_api

REQUIRED_JOBS = {
    "Backend",
    "Frontend and contract",
    "Repository safety",
    "Coverage badge",
    "Build backend image",
    "Build web image",
    "Runtime proof",
    "Publish immutable images",
}
REQUIRED_FILES = {
    "release-manifest.json",
    "compose.production.yaml",
    "Caddyfile.production",
    "scripts/deploy/deploy.sh",
    "scripts/deploy/rollback.sh",
    "scripts/deploy/release_order.py",
    "scripts/deploy/verify_current.sh",
}
FINGERPRINT_PATHS = (
    ".github/workflows/verify.yml",
    ".github/workflows/deploy-production.yml",
    ".github/actions/runtime-image/action.yml",
    "Makefile",
    ".tool-versions",
    "scripts/prove_release_workflow.py",
    "apps/backend/uv.lock",
    "pnpm-lock.yaml",
)
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def fingerprint(revision: str) -> str:
    """Bind evidence to the caller's verification definitions, not an old requested checkout."""
    git = shutil.which("git")
    if git is None or not SHA.fullmatch(revision):
        msg = "trusted workflow revision is unavailable"
        raise ValueError(msg)
    digest = hashlib.sha256()
    for path in FINGERPRINT_PATHS:
        content = subprocess.check_output([git, "show", f"{revision}:{path}"])  # noqa: S603
        digest.update(path.encode() + b"\0" + content + b"\0")
    return digest.hexdigest()


def trusted_run(run: dict[str, Any], jobs: list[dict[str, Any]], sha: str, repo: str) -> bool:
    """Reject foreign, manual, partial, cancelled, or missing verification evidence."""
    if not (
        run.get("event") == "push"
        and run.get("conclusion") == "success"
        and run.get("status") == "completed"
        and run.get("head_sha") == sha
        and run.get("head_branch") == "main"
        and run.get("repository", {}).get("full_name") == repo
        and run.get("head_repository", {}).get("full_name") == repo
        and run.get("path") == ".github/workflows/deploy-production.yml"
    ):
        return False
    observed = {job.get("name", "").split(" / ")[-1]: job for job in jobs}
    return observed.keys() >= REQUIRED_JOBS and all(
        job.get("status") == "completed" and job.get("conclusion") == "success" for job in jobs
    )


def validate_bundle(root: Path, sha: str, expected_fingerprint: str) -> dict[str, Any]:
    """Verify source, immutable image identities, definition identity, and every artifact file."""
    manifest = json.loads((root / "release-manifest.json").read_text())
    if (
        not SHA.fullmatch(sha)
        or manifest.get("source_sha") != sha
        or manifest.get("schema") != "wef-release@1"
        or manifest.get("verification_fingerprint") != expected_fingerprint
        or not re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint)
    ):
        msg = "release source or verification fingerprint mismatch"
        raise ValueError(msg)
    images = manifest.get("images", {})
    if not all(
        isinstance(images.get(k), str) and DIGEST.fullmatch(images[k]) for k in ("backend", "web")
    ):
        msg = "release image digest evidence is incomplete"
        raise ValueError(msg)
    if any(path.is_symlink() for path in root.rglob("*")):
        msg = "release artifacts cannot contain symlinks"
        raise ValueError(msg)
    covered: set[str] = set()
    for line in (root / "SHA256SUMS").read_text().splitlines():
        checksum, relative = line.split("  ", 1)
        path = root / relative
        if (
            not re.fullmatch(r"[0-9a-f]{64}", checksum)
            or relative in covered
            or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
        ):
            msg = "release artifact checksum or path mismatch"
            raise ValueError(msg)
        covered.add(relative)
    files = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != root / "SHA256SUMS"
    }
    if files != covered or not covered.issuperset(REQUIRED_FILES):
        msg = "release checksum inventory is incomplete"
        raise ValueError(msg)
    return dict(manifest)


def find_reusable(repo: str, sha: str, expected_fingerprint: str) -> str:
    """Search at most twenty completed push runs and validate a bounded artifact download."""
    gh = shutil.which("gh")
    if gh is None:
        return ""
    runs = read_api(
        f"repos/{repo}/actions/workflows/deploy-production.yml/runs?event=push&head_sha={sha}&status=success&per_page=20"
    )
    for run in runs.get("workflow_runs", []):
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        attempt = run.get("run_attempt", 1)
        jobs = read_api(f"repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
        if not trusted_run(run, jobs.get("jobs", []), sha, repo):
            continue
        artifacts = read_api(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100")
        if not any(
            a.get("name") == f"release-{sha}" and a.get("expired") is False
            for a in artifacts.get("artifacts", [])
        ):
            continue
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(  # noqa: S603 - fixed gh command, trusted run id and exact SHA
                [
                    gh,
                    "run",
                    "download",
                    str(run_id),
                    "--repo",
                    repo,
                    "--name",
                    f"release-{sha}",
                    "--dir",
                    directory,
                ],
                capture_output=True,
                check=False,
                timeout=60,
            )
            if result.returncode:
                continue
            try:
                validate_bundle(Path(directory), sha, expected_fingerprint)
            except (ValueError, KeyError, TypeError, OSError):
                continue
        return str(run_id)
    return ""


def main() -> int:
    """Emit only validated reuse outputs or fall back to full verification."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("find", "validate"))
    parser.add_argument("sha")
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if not SHA.fullmatch(args.sha):
        parser.error("release SHA must be full hexadecimal identity")
    expected = os.environ.get("VERIFICATION_FINGERPRINT") or fingerprint(
        os.environ["GITHUB_WORKFLOW_SHA"]
    )
    outputs: dict[str, str] = {"fingerprint": expected}
    if args.command == "find":
        try:
            outputs["reuse_run_id"] = (
                find_reusable(repo, args.sha, expected)
                if os.environ.get("ALLOW_REUSE") == "true"
                else ""
            )
        except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
            outputs["reuse_run_id"] = ""
    else:
        if args.root is None:
            parser.error("validation requires an artifact root")
        manifest = validate_bundle(args.root, args.sha, expected)
        for component in ("backend", "web"):
            outputs[f"{component}_digest"] = manifest["images"][component]
            outputs[f"{component}_image"] = f"ghcr.io/{repo.lower()}-{component}"
        outputs["reused_verified"] = str(bool(os.environ.get("REUSE_RUN_ID"))).lower()
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.writelines(f"{key}={value}\n" for key, value in outputs.items())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
