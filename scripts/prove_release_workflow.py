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
    remote_uses = [line for line in uses_lines if "uses: ./" not in line]
    assert len(PINNED_ACTION.findall(source)) == len(remote_uses)
    assert "pull_request_target:" not in source
    assert "branches:\n      - main" in source
    assert "workflow_dispatch:" in source
    assert "cancel-in-progress: false" in source
    assert "AUTO_DEPLOY_ENABLED" in source
    assert "environment: production" in source
    assert "if: needs.resolve.outputs.should_deploy == 'true'" in source
    assert "force_rollback_rehearsal" in source
    assert "WEF_FORCE_ROLLBACK_REHEARSAL=1" in source
    assert '"$deploy_status" -eq 42' in source
    assert "PUBLIC_PORT: ${{ vars.WEF_PUBLIC_PORT }}" in source
    assert "WEF_GEOAPIFY_API_KEY: ${{ secrets.WEF_GEOAPIFY_API_KEY }}" in source
    assert "WEF_TELEGRAM_API_ID: ${{ secrets.WEF_TELEGRAM_API_ID }}" in source
    assert "WEF_TELEGRAM_API_HASH: ${{ secrets.WEF_TELEGRAM_API_HASH }}" in source
    assert "WEF_TELEGRAM_PHONE: ${{ secrets.WEF_TELEGRAM_PHONE }}" in source
    assert "WEF_TELEGRAM_SESSION: ${{ secrets.WEF_TELEGRAM_SESSION }}" in source
    assert "WEF_ADMIN_SESSION_SECRET: ${{ secrets.WEF_ADMIN_SESSION_SECRET }}" in source
    assert "WEF_CONTACT_ENCRYPTION_KEY: ${{ secrets.WEF_CONTACT_ENCRYPTION_KEY }}" in source
    assert "WEF_CONTACT_HMAC_KEY: ${{ secrets.WEF_CONTACT_HMAC_KEY }}" in source
    assert "release_sha: ${{ needs.resolve.outputs.release_sha }}" in source
    assert_shared_verification(source)
    assert "name: Release outcome" in source
    assert "needs: [resolve, verify, build-backend, build-web, publish, deploy]" in source
    assert "retention-days: 90" in source
    assert "RELEASE_NEEDS: ${{ toJSON(needs) }}" in source
    assert "WEF_RELEASE_OBSERVATION=$observation_file" in source
    deploy_script = (REPOSITORY_ROOT / "scripts/deploy/deploy.sh").read_text(encoding="utf-8")
    assert "run --rm geocoder-check" in deploy_script
    assert "WEF_DEPLOY_TEST_MODE" in deploy_script
    assert re.search(
        r'deploy_command\+=\(\s*"\$release_dir/scripts/deploy/deploy\.sh"'
        r'\s*/home/nuc/wef\s*"\$release_dir"\s*"\$config_file"'
        r'\s*"\$RELEASE_SHA"\s*"\$PUBLIC_PORT"\s*\)',
        source,
    )
    assert "sha256sum --check SHA256SUMS" in source
    assert "StrictHostKeyChecking=yes" in source
    assert "compose.candidate.yaml" in source
    assert "compose.production-shared-edge.yaml" in source
    assert "scripts/transfer_candidate.py" in source
    assert all(
        "secrets." not in line for line in source.splitlines() if line.lstrip().startswith("if:")
    )


def assert_shared_verification(source: str) -> None:
    """Preserve check parity, immutable builds, and the full production lock boundary."""
    shared = (REPOSITORY_ROOT / ".github/workflows/verify.yml").read_text()
    ci = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text()
    image = (REPOSITORY_ROOT / ".github/actions/runtime-image/action.yml").read_text()
    assert "workflow_call:" in shared
    assert "uses: ./.github/workflows/verify.yml" in ci
    assert "uses: ./.github/workflows/verify.yml" in source
    assert "  push:" not in ci
    assert "check: [Backend, Frontend and contract, Repository safety, Coverage badge]" in ci
    assert "name: Runtime images" in ci
    assert "secrets:" not in ci
    assert "packages: write" not in ci
    assert "secrets:" not in shared
    assert "packages: write" not in shared
    assert "ref: ${{ inputs.source_sha }}" in shared
    assert "env -u TEST_DATABASE_URL make test" not in source
    for command in (
        "ruff format --check",
        "ruff check",
        "mypy",
        "lint-imports",
        "prove_architecture_violation.py",
        "--cov-fail-under=90",
        "--cov-branch",
        "wef-export-openapi",
        "pip-audit",
        "test:coverage",
        "format:check",
        "typecheck",
        "contract:check",
        "contract:lint",
        "contract:docs",
        "prove_contract_drift.py",
        "breaking --fail-on ERR",
        "openapi-breaking-probe.json",
        "test:e2e",
        "pnpm audit --prod --audit-level high",
        "make compose-config",
        "make production-proof",
        "check_markdown_links.py",
        "git ls-files",
        "render_coverage_badge.py",
        "scripts.test_release_report",
        "scripts.test_release_order",
    ):
        assert command in shared, command
    assert "make production-runtime-proof" in source
    assert "load: true" in image
    assert "docker push" in image
    assert "Config.User" in image
    assert "! command -v pytest" in image
    assert "test ! -e /app/contracts" in image
    assert "scope=${{ inputs.component }}-production" in image
    assert (
        "    concurrency:\n      group: wef-production\n      cancel-in-progress: false" in source
    )
    assert "group: wef-release-${{ inputs.release_sha || github.sha }}" in source
    assert "needs: [resolve, build-backend, build-web]" in source
    assert "needs.runtime.result == 'success'" in source
    assert "needs.build-backend.result == 'success'" in source
    assert "needs.build-web.result == 'success'" in source
    assert "reuse_release validate" in source
    assert "release_order decide" in source
    assert "WEF_EXPECTED_CURRENT_SHA=$expected_current" in source
    assert source.index("release_order decide") < source.index('"install -m 0750 -d')
    assert source.index("docker logout ghcr.io") < source.index('rm -f "$ssh_dir/key"')


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


def _build_fixture_values(extra_environment: dict[str, str]) -> dict[str, str]:
    """Build one validated release environment from fixture inputs."""
    previous = {key: os.environ.get(key) for key in extra_environment}
    os.environ.update(extra_environment)
    try:
        return build_values(
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


def _assert_blank_groq_batch_defaults(groq_environment: dict[str, str]) -> None:
    """Prove unset GitHub batch vars fall back to code defaults."""
    with_blank_batch = _build_fixture_values(
        {
            **groq_environment,
            "WEF_GROQ_USE_BATCH_API": "false",
            "WEF_GROQ_BATCH_CHUNK_SIZE": "",
            "WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS": "",
            "WEF_GROQ_BATCH_MAX_WAIT_SECONDS": "",
        },
    )
    assert with_blank_batch["WEF_GROQ_USE_BATCH_API"] == "false"
    assert with_blank_batch["WEF_GROQ_BATCH_CHUNK_SIZE"] == "2"
    assert with_blank_batch["WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS"] == "2"
    assert with_blank_batch["WEF_GROQ_BATCH_MAX_WAIT_SECONDS"] == "3600"


def assert_release_configuration() -> None:
    """Prove complete validation and mode-0600 secret material."""
    environment = {
        "POSTGRES_DB": "wef",
        "POSTGRES_PASSWORD": "safe:/password-0123456789abcdef",
        "POSTGRES_USER": "wef",
        "WEF_ADMIN_SESSION_SECRET": "fixture-admin-session-secret-0123456789abcdef",
        "WEF_ALLOW_SYNTHETIC_SEED": "false",
        "WEF_CONTACT_ENCRYPTION_KEY": "0123456789abcdef" * 4,
        "WEF_CONTACT_HMAC_KEY": "fedcba9876543210" * 4,
        "WEF_GEOAPIFY_API_KEY": "fixture-geoapify-key-0123456789",
        "WEF_LOG_LEVEL": "INFO",
        "WEF_TELEGRAM_API_HASH": "0123456789abcdef0123456789abcdef",
        "WEF_TELEGRAM_API_ID": "12345678",
    }
    values = _build_fixture_values(environment)

    assert "safe%3A%2Fpassword-0123456789abcdef" in values["WEF_DATABASE_URL"]
    assert values["WEF_GEOAPIFY_API_KEY"] == "fixture-geoapify-key-0123456789"
    assert "WEF_GROQ_API_KEY" not in values
    assert values["WEF_PARSER_REPLAY_ENABLED"] == "false"
    assert values["WEF_PARSER_REPLAY_AUTO_APPLY"] == "false"
    replay_values = _build_fixture_values({**environment, "WEF_PARSER_REPLAY_ENABLED": "true"})
    assert replay_values["WEF_PARSER_REPLAY_ENABLED"] == "true"
    assert "WEF_GROQ_API_KEY" not in replay_values

    groq_environment = {
        **environment,
        "WEF_GROQ_API_KEY": "gsk_fixture-groq-key-0123456789abcdef",
        "WEF_AI_CURATION_ENABLED": "false",
        "WEF_GROQ_MODEL": "openai/gpt-oss-20b",
        "WEF_GROQ_ZDR_VERIFIED": "false",
        "WEF_GROQ_TIMEOUT_SECONDS": "30",
    }
    with_groq = _build_fixture_values(groq_environment)
    assert with_groq["WEF_GROQ_API_KEY"].startswith("gsk_fixture")
    assert with_groq["WEF_AI_CURATION_ENABLED"] == "false"
    assert with_groq["WEF_GROQ_ZDR_VERIFIED"] == "false"
    assert with_groq["WEF_GROQ_USE_BATCH_API"] == "true"
    assert with_groq["WEF_GROQ_BATCH_CHUNK_SIZE"] == "20"
    _assert_blank_groq_batch_defaults(groq_environment)
    recovery_flags = (
        "WEF_AI_RECOVERY_ENABLED",
        "WEF_AI_RECOVERY_ACTIVATION_VERIFIED",
        "WEF_AI_RECOVERY_AUTO_APPLY",
    )
    assert all(with_groq[name] == "false" for name in recovery_flags)
    enabled = _build_fixture_values(
        {
            **groq_environment,
            **dict.fromkeys(recovery_flags, "true"),
            "WEF_AI_RECOVERY_OWNER_ID": "12345678-1234-1234-1234-123456789abc",
        }
    )
    assert all(enabled[name] == "true" for name in recovery_flags)
    assert enabled["WEF_AI_RECOVERY_OWNER_ID"] == "12345678-1234-1234-1234-123456789abc"
    for name, value in (
        ("WEF_AI_RECOVERY_ENABLED", "maybe"),
        ("WEF_AI_RECOVERY_OWNER_ID", "not-a-uuid"),
    ):
        try:
            _build_fixture_values({**groq_environment, name: value})
        except ValueError:
            pass
        else:
            message = f"Invalid recovery configuration accepted: {name}"
            raise AssertionError(message)

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
