"""Private progress status and observation-gated incident activation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.ingestion_progress_store import (
    SQLAlchemyIngestionProgressStore,
)
from wef_backend.settings import load_settings


async def run(action: str) -> dict[str, object]:
    """Change incident activation only; preserve every ingestion and recovery state."""
    engine = create_async_engine(load_settings().database_url)
    try:
        store = SQLAlchemyIngestionProgressStore(
            async_sessionmaker(engine, expire_on_commit=False),
            default_live_channel_identity().channel_id,
        )
        if action in {"enable", "disable"}:
            await store.control(enabled=action == "enable")
        return await store.status()
    finally:
        await engine.dispose()


def main() -> None:
    """Print aggregate status without exposing source records or contacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("status", "enable", "disable"), default="status", nargs="?"
    )
    sys.stdout.write(json.dumps(asyncio.run(run(parser.parse_args().action))) + "\n")


if __name__ == "__main__":
    main()
