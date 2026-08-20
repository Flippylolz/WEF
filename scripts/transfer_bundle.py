"""CLI for historical transfer bundle dry-run, pack, and verify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.transfer.bundle import (
    BUNDLE_MANIFEST_NAME,
    dry_run_source,
    pack_bundle,
    verify_bundle,
)
from scripts.transfer.terminal_state import TerminalState


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Historical transfer bundle tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run = subparsers.add_parser("dry-run", help="Summarize one bundle source")
    dry_run.add_argument("source_root", type=Path)

    pack = subparsers.add_parser("pack", help="Create one immutable bundle directory")
    pack.add_argument("source_root", type=Path)
    pack.add_argument("output_dir", type=Path)
    pack.add_argument("--source-checksum", required=True)
    pack.add_argument("--release-sha", required=True)

    verify = subparsers.add_parser("verify", help="Verify one bundle directory")
    verify.add_argument("bundle_dir", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one transfer bundle subcommand."""
    arguments = _build_parser().parse_args(argv)

    if arguments.command == "dry-run":
        _, summary = dry_run_source(arguments.source_root)
        payload = {
            "table_row_counts": summary.table_row_counts,
            "media_object_count": summary.media_object_count,
            "media_bytes": summary.media_bytes,
            "expected_bundle_bytes": summary.expected_bundle_bytes,
            "minimum_headroom_bytes": summary.minimum_headroom_bytes,
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    if arguments.command == "pack":
        result = pack_bundle(
            source_root=arguments.source_root,
            output_dir=arguments.output_dir,
            source_checksum=arguments.source_checksum,
            release_sha=arguments.release_sha,
            terminal_state=TerminalState(
                active_import_lease=False,
                open_geocode_claims=0,
                pending_provider_work=0,
                reconciliation_complete=True,
            ),
        )
        sys.stdout.write(
            json.dumps(
                {
                    "bundle_dir": str(result.bundle_dir),
                    "manifest": str(result.manifest_path),
                    "expected_bundle_bytes": result.dry_run.expected_bundle_bytes,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        return 0

    verify_bundle(arguments.bundle_dir)
    sys.stdout.write(
        json.dumps(
            {
                "bundle_dir": str(arguments.bundle_dir.resolve()),
                "manifest": BUNDLE_MANIFEST_NAME,
                "status": "verified",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
