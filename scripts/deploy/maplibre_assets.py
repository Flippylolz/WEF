"""Validate served MapLibre worker assets across supported bundle layouts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_CLI_ARGUMENT_COUNT = 4
_SHARED_IMPORT = re.compile(r"\b(?:from|import)\s*[\"'][^\"']*maplibre-gl-shared\.mjs[\"']")


class MapLibreAssetsError(ValueError):
    """A served asset cannot satisfy the module worker smoke contract."""


def validate_maplibre_assets(headers: str, worker: str, shared: str) -> None:
    """Reject fallback pages or invalid worker entrypoints in either bundle layout."""
    content_types = [
        line.partition(":")[2].strip().casefold()
        for line in headers.splitlines()
        if line.casefold().startswith("content-type:")
    ]
    if not any("javascript" in value for value in content_types):
        message = "MapLibre worker must be served as JavaScript"
        raise MapLibreAssetsError(message)
    if "<!doctype html" in worker.casefold() or "<!doctype html" in shared.casefold():
        message = "MapLibre assets must not be HTML fallback pages"
        raise MapLibreAssetsError(message)
    linked_worker = _SHARED_IMPORT.search(worker) is not None
    bundled_worker = (
        "self" in worker
        and "postMessage" in worker
        and ("addEventListener" in worker or "onmessage" in worker)
    )
    if not (linked_worker or bundled_worker):
        message = "MapLibre asset lacks a shared-module import or a worker message entrypoint"
        raise MapLibreAssetsError(message)
    if linked_worker and "export" not in shared:
        message = "MapLibre shared asset must contain module exports"
        raise MapLibreAssetsError(message)


def main() -> int:
    """Read the downloaded smoke assets without executing their JavaScript."""
    if len(sys.argv) != _CLI_ARGUMENT_COUNT:
        message = "usage: maplibre_assets.py HEADERS WORKER SHARED"
        raise SystemExit(message)
    headers, worker, shared = (Path(value).read_text(encoding="utf-8") for value in sys.argv[1:])
    validate_maplibre_assets(headers, worker, shared)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
