"""Operator CLI: dry-run or apply property-type backfill from retained sources."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.infrastructure.property_type_backfill import (
    backfill_property_types,
)
from wef_backend.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for property-type backfill."""
    parser = argparse.ArgumentParser(
        description=(
            "Re-extract offer property types from retained primary source revisions. "
            "Dry-run by default; pass --apply to persist changed values only."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max offers to process in this run",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changed property_type values",
    )
    return parser


async def run(*, limit: int | None, apply: bool) -> dict[str, int | str]:
    """Run one bounded backfill and return JSON-serializable counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        summary = await backfill_property_types(
            database.session_factory,
            limit=limit,
            apply=apply,
        )
        return asdict(summary)
    finally:
        await database.engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print backfill counts as JSON; exit 2 on failure."""
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(run(limit=args.limit, apply=args.apply))
    except Exception:  # noqa: BLE001
        sys.stderr.write("Property type backfill failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
