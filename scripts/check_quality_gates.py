"""Fail closed when the checked-in local and required-job quality mappings drift."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

COVERAGE_FLOOR = 90
ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    "Backend",
    "Frontend and contract",
    "Repository safety",
    "Runtime images",
    "Coverage badge",
}
FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/verify.yml",
    ".github/workflows/deploy-production.yml",
    ".github/dependabot-required-checks.json",
    "apps/backend/pyproject.toml",
    "apps/web/package.json",
    "apps/web/vitest.config.mts",
    "Makefile",
    "AI/governance/REPOSITORY_RULES.md",
)


def _workflow_checks(files: dict[str, str]) -> list[str]:
    """Validate names and active workflow commands."""
    errors: list[str] = []
    ci = files[FILES[0]]
    shared = files[FILES[1]]
    matrix = re.search(r"check: \[([^\]]+)\]", ci)
    checks = {item.strip() for item in matrix[1].split(",")} if matrix else set()
    checks.update(re.findall(r"^    name: (Runtime images)$", ci, re.MULTILINE))
    if checks != CHECKS:
        errors.append("required CI names differ from the five reviewed checks")
    if set(json.loads(files[FILES[3]])["required_check_names"]) != CHECKS:
        errors.append("Dependabot required checks drifted")
    errors.extend(
        f"repository rules omit {name}" for name in CHECKS if f"- `{name}`" not in files[FILES[8]]
    )
    errors.extend(
        f"{path} bypasses shared verification"
        for path in FILES[:3]
        if path != FILES[1] and "uses: ./.github/workflows/verify.yml" not in files[path]
    )
    errors.extend(
        f"shared workflow omits {name}"
        for name in CHECKS - {"Runtime images"}
        if f"    name: {name}\n" not in shared
    )
    required = (
        "ruff format --check .",
        "ruff check .",
        "run mypy",
        "lint-imports --config",
        "prove_architecture_violation.py",
        "--cov-fail-under=90",
        "wef-export-openapi",
        "pnpm --filter web test:coverage",
        "contract:check",
        "contract:lint",
        "contract:docs",
        "prove_contract_drift.py",
        "breaking --fail-on ERR",
        "pnpm --filter web build",
        "check_markdown_links.py",
        "make production-proof",
        "make quality-gates",
    )
    # Ignore whole-line comments so commenting out a command cannot keep its gate green.
    active = "\n".join(line for line in shared.splitlines() if not line.lstrip().startswith("#"))
    errors.extend(
        f"shared workflow omits {command}" for command in required if command not in active
    )
    if "continue-on-error: true" in shared or re.search(r"if:\s*(?:false|\$\{\{\s*false)", shared):
        errors.append("shared verification contains an unconditional bypass")
    if 'run: test "$RESULT" = success' not in ci or "if: always()" not in ci:
        errors.append("required aliases do not fail closed on incomplete shared verification")
    return errors


def _configuration_checks(files: dict[str, str]) -> list[str]:
    """Validate coverage and the no-suppression warning policy."""
    errors: list[str] = []
    backend = tomllib.loads(files[FILES[4]])["tool"]
    filters = backend["pytest"]["ini_options"].get("filterwarnings", [])
    if filters != ["error"]:
        errors.append("unexpected backend warnings must fail without blanket exceptions")
    if backend["coverage"]["report"].get("fail_under", 0) < COVERAGE_FLOOR:
        errors.append("backend coverage floor is missing or below 90")
    if "error" not in backend["pytest"]["ini_options"].get("filterwarnings", []):
        errors.append("unexpected backend warnings are not fatal")
    for metric in ("lines", "branches"):
        match = re.search(rf"{metric}:\s*(\d+)", files[FILES[6]])
        if not match or int(match[1]) < COVERAGE_FLOOR:
            errors.append(f"frontend {metric} coverage floor is missing or below 90")
    scripts = json.loads(files[FILES[5]])["scripts"]
    if "--max-warnings 0" not in scripts["lint"]:
        errors.append("frontend lint warnings are not fatal")
    return errors


def _local_checks(files: dict[str, str]) -> list[str]:
    """Validate the complete local mapping."""
    errors: list[str] = []
    makefile = files[FILES[7]]
    required = (
        "format-check lint typecheck test contract-check",
        "python3 -m unittest discover -s scripts -t .",
        "quality-gates",
        "prove_architecture_violation.py",
        "check_markdown_links.py",
        "contract-compatibility",
        "production-proof",
        "build",
    )
    errors.extend(
        f"local verification omits {command}" for command in required if command not in makefile
    )
    if not re.search(r"^verify:.*\n(?:\t.*\n)+", makefile, re.MULTILINE):
        errors.append("canonical make verify entry point is missing")
    return errors


def validate(files: dict[str, str]) -> list[str]:
    """Run every independent policy family without treating partial success as green."""
    return _workflow_checks(files) + _configuration_checks(files) + _local_checks(files)


def main() -> int:
    """Read only repository-owned configuration and print actionable failures."""
    errors = validate({path: (ROOT / path).read_text() for path in FILES})
    for error in errors:
        sys.stderr.write(error + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
