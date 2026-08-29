"""Operator CLI: replay archived raw events through the current parser (E17-T2)."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.raw_replay import RawParserReplayer
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)
from wef_backend.settings import load_settings


async def run() -> dict[str, int]:
    """Replay stale archived messages and return JSON-serializable counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        replayer = RawParserReplayer(
            store=SQLAlchemyIngestionPersistence(database.session_factory),
            source=SQLAlchemyRawEventArchive(database.session_factory),
            identity=default_live_channel_identity(),
        )
        result = await replayer(release_sha=settings.release_sha)
        return asdict(result)
    finally:
        await database.engine.dispose()


def main() -> None:
    """Print replay counts as JSON."""
    try:
        payload = asyncio.run(run())
    except Exception:  # noqa: BLE001
        sys.stderr.write("Raw archive parser replay failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
