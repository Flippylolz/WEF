"""Prove generated frontend contract checks reject a stale OpenAPI consumer."""

# ruff: noqa: T201

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPOSITORY_ROOT / "contracts/openapi/v1.json"
GENERATED = REPOSITORY_ROOT / "apps/web/src/generated/api.ts"
PNPM = shutil.which("pnpm")


def contract_check() -> subprocess.CompletedProcess[str]:
    """Run the generated-contract currentness check."""
    if PNPM is None:
        msg = "pnpm is required to verify generated contracts"
        raise RuntimeError(msg)
    return subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [PNPM, "--filter", "web", "contract:check"],
        check=False,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


def main() -> int:
    """Mutate the contract temporarily and require the currentness check to fail."""
    original_contract = CONTRACT.read_bytes()
    original_generated = GENERATED.read_bytes()

    failure: subprocess.CompletedProcess[str] | None = None
    try:
        document: dict[str, Any] = json.loads(original_contract)
        schemas = document["components"]["schemas"]
        schemas["E1T4DeliberateDrift"] = {
            "properties": {"probe": {"type": "string"}},
            "required": ["probe"],
            "type": "object",
        }
        CONTRACT.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        failure = contract_check()
    finally:
        CONTRACT.write_bytes(original_contract)
        GENERATED.write_bytes(original_generated)

    clean = contract_check()
    if failure is None or failure.returncode == 0:
        print("Deliberate OpenAPI drift was not rejected.")
        return 1
    if clean.returncode != 0:
        print(clean.stdout)
        print(clean.stderr)
        print("Contract check did not recover after restoring committed artifacts.")
        return 1

    print("Generated-contract check rejected deliberate drift and cleanup passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
