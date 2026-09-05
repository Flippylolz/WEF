"""Private aggregate status and durable media-only pause/resume controls."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.settings import load_settings


async def run(action: str) -> dict[str, object]:
    """Apply a bounded operator action without changing source or public asset evidence."""
    settings = load_settings()
    engine = create_async_engine(settings.database_url)
    try:
        store = SQLAlchemyMediaRecoveryStore(
            async_sessionmaker(engine, expire_on_commit=False),
            default_live_channel_identity().channel_id,
        )
        if action != "status":
            await store.control(action)
        return await store.status()
    finally:
        await engine.dispose()


def main() -> None:
    """Print aggregate media state; normal recovery requires no per-record commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("status", "pause", "resume"), default="status", nargs="?"
    )
    sys.stdout.write(json.dumps(asyncio.run(run(parser.parse_args().action))) + "\n")


if __name__ == "__main__":
    main()
