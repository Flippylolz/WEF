"""Create deterministic SHA-256 checksums for a non-secret release bundle."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    """Hash one release file in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    """Write a sorted sha256sum-compatible bundle manifest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    arguments = parser.parse_args()
    bundle = arguments.bundle.resolve()
    output = bundle / "SHA256SUMS"
    files = sorted(path for path in bundle.rglob("*") if path.is_file() and path != output)
    output.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(bundle)}\n" for path in files),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
