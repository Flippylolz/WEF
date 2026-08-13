"""Create a deterministic, non-secret release manifest."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def validate_timestamp(value: str) -> str:
    """Require an ISO-8601 source timestamp."""
    datetime.fromisoformat(value)
    return value


def create_manifest(
    source_sha: str,
    source_timestamp: str,
    migration_revision: str,
    backend_digest: str,
    web_digest: str,
) -> dict[str, object]:
    """Build one validated release manifest."""
    if not SHA_PATTERN.fullmatch(source_sha):
        msg = "source SHA must be 40 lowercase hexadecimal characters"
        raise ValueError(msg)
    if not DIGEST_PATTERN.fullmatch(
        backend_digest,
    ) or not DIGEST_PATTERN.fullmatch(web_digest):
        msg = "application digests must be immutable sha256 values"
        raise ValueError(msg)
    return {
        "schema": "wef-release@1",
        "source_sha": source_sha,
        "source_timestamp": validate_timestamp(source_timestamp),
        "migration_revision": migration_revision,
        "images": {
            "backend": backend_digest,
            "web": web_digest,
        },
    }


def main() -> int:
    """Write one deterministic release manifest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("source_sha")
    parser.add_argument("source_timestamp")
    parser.add_argument("migration_revision")
    parser.add_argument("backend_digest")
    parser.add_argument("web_digest")
    arguments = parser.parse_args()

    try:
        manifest = create_manifest(
            arguments.source_sha,
            arguments.source_timestamp,
            arguments.migration_revision,
            arguments.backend_digest,
            arguments.web_digest,
        )
    except ValueError as error:
        parser.error(str(error))
    arguments.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
