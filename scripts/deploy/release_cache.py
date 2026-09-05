"""Extract non-sensitive cache counters from the exact Buildx build record."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def cache_metrics(record: dict[str, Any]) -> dict[str, Any]:
    """Describe cache reuse only when Buildx supplies complete, consistent counters."""
    total, cached = record.get("NumTotalSteps"), record.get("NumCachedSteps")
    if (
        type(total) is not int
        or type(cached) is not int
        or total <= 0
        or not 0 <= cached <= total
        or record.get("Status") != "completed"
    ):
        return {"state": "unknown", "cached_steps": None, "total_steps": None}
    return {"state": "warm" if cached else "cold", "cached_steps": cached, "total_steps": total}


def collect_cache(metadata: dict[str, Any]) -> dict[str, Any]:
    """Read one exact build reference; cache observation failure cannot fail the release."""
    docker = shutil.which("docker")
    ref = metadata.get("buildx.build.ref")
    if (
        docker is None
        or not isinstance(ref, str)
        or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./-]{0,199}", ref)
    ):
        return cache_metrics({})
    try:
        result = subprocess.run(  # noqa: S603 - fixed Docker command and validated build ref
            [docker, "buildx", "history", "inspect", "--format", "json", ref],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        record = json.loads(result.stdout) if result.returncode == 0 else {}
        return cache_metrics(record if isinstance(record, dict) else {})
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return cache_metrics({})


def main() -> int:
    """Publish only cache counts, never the build record's inputs or environment."""
    try:
        metadata = json.loads(os.environ.get("BUILD_METADATA", "{}"))
    except ValueError:
        metadata = {}
    metrics = collect_cache(metadata if isinstance(metadata, dict) else {})
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write("cache_metrics=" + json.dumps(metrics, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
