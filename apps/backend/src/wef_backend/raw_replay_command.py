"""Operator CLI: replay archived raw events through the current parser (E17-T2)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.composition import build_contact_cipher
from wef_backend.database import create_database_resources
from wef_backend.features.admin.infrastructure.ai_enrichment_store import build_offer_origin_sync
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


async def run(*, seed_archive: bool = False) -> dict[str, int]:
    """Replay stale archived messages and return JSON-serializable counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        archive = SQLAlchemyRawEventArchive(database.session_factory)
        if seed_archive:
            seeded, skipped = await archive.seed_from_history()
            payload_seed: dict[str, int] = {"seeded": seeded, "seed_skipped": skipped}
        else:
            payload_seed = {}
        replayer = RawParserReplayer(
            store=SQLAlchemyIngestionPersistence(
                database.session_factory,
                contact_cipher=build_contact_cipher(settings),
                field_origin_sync=build_offer_origin_sync(database.session_factory),
            ),
            source=archive,
            identity=default_live_channel_identity(),
        )
        result = await replayer(release_sha=settings.release_sha)
        return {**payload_seed, **asdict(result)}
    finally:
        await database.engine.dispose()


def main() -> None:
    """Print replay counts as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-archive",
        action="store_true",
        help="Backfill the archive from retained history before replaying",
    )
    args = parser.parse_args()
    try:
        payload = asyncio.run(run(seed_archive=args.seed_archive))
    except Exception:  # noqa: BLE001
        sys.stderr.write("Raw archive parser replay failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
