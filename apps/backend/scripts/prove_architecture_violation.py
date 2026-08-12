"""Prove import-linter rejects a temporary forbidden framework import."""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPOSITORY_ROOT / ".importlinter"
PROBE_PATH = (
    BACKEND_ROOT / "src/wef_backend/features/estates/domain/_deliberate_forbidden_import_probe.py"
)


def run_import_linter() -> subprocess.CompletedProcess[str]:
    """Run the installed linter against the repository contract."""
    environment = os.environ.copy()
    existing_python_path = environment.get("PYTHONPATH")
    source_path = str(BACKEND_ROOT / "src")
    environment["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{existing_python_path}" if existing_python_path else source_path
    )
    executable = Path(sys.executable).with_name("lint-imports")
    return subprocess.run(  # noqa: S603
        [str(executable), "--config", str(CONFIG_PATH)],
        check=False,
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def report(label: str, result: subprocess.CompletedProcess[str]) -> None:
    """Print bounded diagnostic output when a proof stage fails."""
    print(label)
    print(result.stdout)
    print(result.stderr)


def main() -> int:
    """Verify clean, deliberately broken, and cleaned architecture states."""
    baseline = run_import_linter()
    if baseline.returncode != 0:
        report("baseline architecture lint failed", baseline)
        return 1

    violation: subprocess.CompletedProcess[str] | None = None
    try:
        PROBE_PATH.write_text("import fastapi\n", encoding="utf-8")
        violation = run_import_linter()
    finally:
        PROBE_PATH.unlink(missing_ok=True)

    cleaned = run_import_linter()
    if violation is None or violation.returncode == 0:
        if violation is not None:
            report("deliberate violation was not rejected", violation)
        return 1
    if cleaned.returncode != 0:
        report("architecture lint did not recover after cleanup", cleaned)
        return 1

    print("import-linter rejected the deliberate violation and cleanup passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
