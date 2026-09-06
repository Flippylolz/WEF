"""Run deterministic critical tests and prove five faults fail in disposable copies."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = Path("apps/backend")
SEEDS = (0, 17, 91)


@dataclass(frozen=True)
class Fault:
    """One unique reviewed source replacement and the test that must reject it."""

    name: str
    path: str
    before: str
    after: str
    tests: tuple[str, ...]


FAULTS = (
    Fault(
        "password-policy",
        "features/identity/domain/model.py",
        "PASSWORD_MIN_LENGTH = 10",
        "PASSWORD_MIN_LENGTH = 0",
        ("test_identity_domain.py",),
    ),
    Fault(
        "hidden-contact",
        "features/contacts/application/reveal.py",
        "if not await self._store.offer_is_publicly_visible(offer_id):",
        "if False:",
        ("test_contacts_application.py",),
    ),
    Fault(
        "inverted-bbox",
        "features/catalog/application/map_query.py",
        "if min_lng >= max_lng or min_lat >= max_lat:",
        "if False:",
        ("test_map_query.py",),
    ),
    Fault(
        "replay-checksum",
        "features/ingestion/application/complete_import.py",
        "if existing_checksums.get(item.raw.external_message_id) != item.raw.checksum",
        "if existing_checksums.get(item.raw.external_message_id) == item.raw.checksum",
        ("test_complete_import.py",),
    ),
)


def _run(root: Path, arguments: list[str], *, seed: int, backend: bool) -> int:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(root),
        "PYTHONHASHSEED": str(seed),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            (str(root / BACKEND / "src"), str(root), str(root / BACKEND))
        ),
    }
    result = subprocess.run(  # noqa: S603 - fixed interpreter, reviewed args, disposable cwd
        [sys.executable, *arguments],
        cwd=root / BACKEND if backend else root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode not in (0, 1):
        message = (
            f"probe infrastructure failed with exit {result.returncode}: {result.stderr[-1000:]}"
        )
        raise RuntimeError(message)
    return result.returncode


def _pytest(names: tuple[str, ...]) -> list[str]:
    return ["-m", "pytest", "-q", "--no-cov", *(f"tests/{name}" for name in names)]


def main() -> int:
    """Never mutate the checkout or pass provider/database secrets to fault probes."""
    with tempfile.TemporaryDirectory(prefix="wef-critical-faults-") as directory:
        root = Path(directory)
        backend = root / BACKEND
        backend.mkdir(parents=True)
        for name in ("src", "tests"):
            shutil.copytree(
                ROOT / BACKEND / name,
                backend / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        shutil.copy2(ROOT / BACKEND / "pyproject.toml", backend / "pyproject.toml")
        shutil.copytree(
            ROOT / "scripts",
            root / "scripts",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        names = (*(fault.tests[0] for fault in FAULTS), "test_raw_replay_application.py")
        for seed in SEEDS:
            ordered = tuple(reversed(names)) if seed == SEEDS[1] else names
            if _run(root, _pytest(ordered), seed=seed, backend=True) != 0:
                message = f"unmodified critical baseline failed for seed {seed}"
                raise RuntimeError(message)
        for fault in FAULTS:
            path = backend / "src/wef_backend" / fault.path
            original = path.read_text()
            if original.count(fault.before) != 1:
                message = f"fault target drifted: {fault.name}"
                raise RuntimeError(message)
            path.write_text(original.replace(fault.before, fault.after))
            try:
                if _run(root, _pytest(fault.tests), seed=0, backend=True) != 1:
                    message = f"critical fault survived: {fault.name}"
                    raise RuntimeError(message)
            finally:
                path.write_text(original)
            sys.stdout.write(f"detected: {fault.name}\n")
        gate = [
            "-c",
            (
                "from scripts.prove_release_workflow import assert_deployment_gate; "
                "assert_deployment_gate()"
            ),
        ]
        if _run(root, gate, seed=0, backend=False) != 0:
            message = "unmodified release gate failed"
            raise RuntimeError(message)
        path = root / "scripts/deploy/evaluate_deploy_gate.py"
        original = path.read_text()
        if original.count("return any(") != 1:
            message = "release fault target drifted"
            raise RuntimeError(message)
        path.write_text(original.replace("return any(", "return True or any("))
        if _run(root, gate, seed=0, backend=False) != 1:
            message = "unassociated release fault survived"
            raise RuntimeError(message)
        sys.stdout.write("detected: unassociated-release\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
