"""Operator CLI: backfill parse-issue ledger rows for historical non-offer messages."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import (
    backfill_parse_issues,
)
from wef_backend.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for bounded parse-issue backfill."""
    parser = argparse.ArgumentParser(
        description=(
            "Classify retained current source revisions, including linked offers. "
            "Record evidence and issue lifecycle without canonical or provider writes. "
            "Completed source/parser/policy evaluations are skipped."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Optional max messages to process in this run",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Commit batch size (default/max: 10)",
    )
    return parser


async def run(*, limit: int | None, batch_size: int) -> dict[str, int]:
    """Run one bounded backfill and return JSON-serializable counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        summary = await backfill_parse_issues(
            database.session_factory,
            limit=limit,
            batch_size=batch_size,
        )
        return asdict(summary)
    finally:
        await database.engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print backfill counts as JSON; exit 2 on failure."""
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(run(limit=args.limit, batch_size=args.batch_size))
    except Exception:  # noqa: BLE001
        sys.stderr.write("Parse issue backfill failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
