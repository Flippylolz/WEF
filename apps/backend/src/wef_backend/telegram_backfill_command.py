"""Operator CLI: bounded live Telegram backfill (requires worker secrets)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.application.telegram_backfill import (
    LiveBackfillRequest,
    LiveTelegramBackfill,
)
from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramSecretError,
    load_telegram_worker_secrets,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import TelethonLiveClient
from wef_backend.settings import load_settings

if TYPE_CHECKING:
    from wef_backend.features.ingestion.application.telegram_live import LiveBackfillResult


def _identity_from_settings() -> TelegramChannelIdentity:
    settings = load_settings()
    return TelegramChannelIdentity(
        username=settings.telegram_channel_username,
        channel_id=settings.telegram_channel_id,
        channel_title=settings.telegram_channel_title,
        message_link_template=settings.telegram_message_link_template,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for bounded live backfill."""
    parser = argparse.ArgumentParser(
        description=(
            "Bounded live Telegram backfill through shared ingestion persistence. "
            "Requires worker-only api_id/api_hash/session files (mode 0600)."
        ),
    )
    parser.add_argument(
        "--resume-after",
        type=int,
        default=0,
        help="Durable checkpoint: highest already-committed external message id",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=25,
        help="Re-process this many message ids below the resume checkpoint",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max messages to fetch from Telegram in this run",
    )
    return parser


async def run_backfill(
    *,
    resume_after: int,
    overlap: int,
    limit: int | None,
) -> LiveBackfillResult:
    """Load secrets, connect Telethon, and run one bounded backfill window."""
    settings = load_settings()
    secrets = load_telegram_worker_secrets(
        api_id_file=settings.telegram_api_id_file,
        api_hash_file=settings.telegram_api_hash_file,
        session_file=settings.telegram_session_file,
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SQLAlchemyIngestionPersistence(session_factory)
    client = TelethonLiveClient(secrets)
    try:
        return await LiveTelegramBackfill(store=store, client=client)(
            LiveBackfillRequest(
                identity=_identity_from_settings(),
                resume_after_external_id=resume_after,
                overlap=overlap,
                limit=limit,
                release_sha=settings.release_sha,
            ),
        )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print a redacted JSON summary; exit 2 on secret or backfill failure."""
    args = build_parser().parse_args(argv)
    try:
        result = asyncio.run(
            run_backfill(
                resume_after=args.resume_after,
                overlap=args.overlap,
                limit=args.limit,
            ),
        )
    except TelegramSecretError:
        sys.stderr.write("Telegram worker secrets unavailable or invalid\n")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram live backfill failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(asdict(result), sort_keys=True) + "\n")
