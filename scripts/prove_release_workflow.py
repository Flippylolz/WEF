"""Prove release workflow gates, metadata, and secret-file handling."""

from __future__ import annotations

# ruff: noqa: PLR2004, S101, S104, T201
import os
import re
import tempfile
from pathlib import Path

from scripts.deploy.build_release_config import (
    ConfigBuildContext,
    build_values,
    write_environment,
)
from scripts.deploy.create_release_manifest import create_manifest
from scripts.deploy.evaluate_deploy_gate import automatic_deploy_allowed
from scripts.deploy.validate_release import ReleaseContext

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/deploy-production.yml"
RELEASE_SHA = "a" * 40
BACKEND_DIGEST = f"sha256:{'b' * 64}"
WEB_DIGEST = f"sha256:{'c' * 64}"
PINNED_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)


def assert_workflow_boundaries() -> None:
    """Prove immutable actions and explicit deployment gates statically."""
    source = WORKFLOW.read_text(encoding="utf-8")
    uses_lines = [line for line in source.splitlines() if line.lstrip().startswith("uses:")]
    assert uses_lines
    assert len(PINNED_ACTION.findall(source)) == len(uses_lines)
    assert "pull_request_target:" not in source
    assert "branches:\n      - main" in source
    assert "workflow_dispatch:" in source
    assert "cancel-in-progress: false" in source
    assert "AUTO_DEPLOY_ENABLED" in source
    assert "environment: production" in source
    assert "if: needs.resolve.outputs.should_deploy == 'true'" in source
    assert "sha256sum --check SHA256SUMS" in source
    assert "StrictHostKeyChecking=yes" in source
    assert all(
        "secrets." not in line for line in source.splitlines() if line.lstrip().startswith("if:")
    )


def assert_deployment_gate() -> None:
    """Prove direct pushes and disabled automation cannot deploy."""
    merged_pull_request = {
        "state": "closed",
        "merged_at": "2026-08-12T20:00:00Z",
        "merge_commit_sha": RELEASE_SHA,
        "base": {"ref": "main"},
    }
    assert automatic_deploy_allowed(
        event_name="workflow_dispatch",
        ref="refs/heads/main",
        release_sha=RELEASE_SHA,
        auto_deploy_enabled=False,
        associated_pull_requests=[],
    )
    assert not automatic_deploy_allowed(
        event_name="push",
        ref="refs/heads/main",
        release_sha=RELEASE_SHA,
        auto_deploy_enabled=False,
        associated_pull_requests=[merged_pull_request],
    )
    assert not automatic_deploy_allowed(
        event_name="push",
        ref="refs/heads/main",
        release_sha=RELEASE_SHA,
        auto_deploy_enabled=True,
        associated_pull_requests=[],
    )
    assert automatic_deploy_allowed(
        event_name="push",
        ref="refs/heads/main",
        release_sha=RELEASE_SHA,
        auto_deploy_enabled=True,
        associated_pull_requests=[merged_pull_request],
    )


def assert_release_configuration() -> None:
    """Prove complete validation and mode-0600 secret material."""
    environment = {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "safe:/password-0123456789abcdef",
        "POSTGRES_USER": "wef",
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
        "WEF_LOG_LEVEL": "INFO",
    }
    previous = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    try:
        values = build_values(
            ConfigBuildContext(
                release=ReleaseContext(
                    root=Path("/home/nuc/wef"),
                    release_dir=Path(f"/home/nuc/wef/releases/{RELEASE_SHA}"),
                    release_sha=RELEASE_SHA,
                    public_port=3100,
                ),
                bind_address="0.0.0.0",
                backend_image=f"ghcr.io/flippylolz/wef-backend@{BACKEND_DIGEST}",
                web_image=f"ghcr.io/flippylolz/wef-web@{WEB_DIGEST}",
            ),
        )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    assert "safe%3A%2Fpassword-0123456789abcdef" in values["WEF_DATABASE_URL"]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "production.env"
        write_environment(path, values)
        assert path.stat().st_mode & 0o777 == 0o600
        assert "POSTGRES_PASSWORD=safe:/password-0123456789abcdef" in path.read_text(
            encoding="utf-8",
        )


def assert_release_manifest() -> None:
    """Prove source, migration, and image identities are immutable."""
    manifest = create_manifest(
        RELEASE_SHA,
        "2026-08-12T20:00:00+00:00",
        "20260812_0001",
        BACKEND_DIGEST,
        WEB_DIGEST,
    )
    assert manifest["source_sha"] == RELEASE_SHA
    assert manifest["migration_revision"] == "20260812_0001"
    assert manifest["images"] == {
        "backend": BACKEND_DIGEST,
        "web": WEB_DIGEST,
    }


def main() -> int:
    """Run all release workflow proofs."""
    assert_workflow_boundaries()
    assert_deployment_gate()
    assert_release_configuration()
    assert_release_manifest()
    print("Release workflow proof passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
