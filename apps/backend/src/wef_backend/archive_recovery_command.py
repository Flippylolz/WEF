"""Restricted backend operator preflight and bounded original-archive recovery."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.composition import build_contact_cipher
from wef_backend.features.admin.infrastructure.ai_enrichment_store import build_offer_origin_sync
from wef_backend.features.ingestion.application.archive_processing import ArchivedEventProcessor
from wef_backend.features.ingestion.application.raw_archive import RawEventDrainer
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.archive_recovery import SQLAlchemyArchiveRecovery
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)
from wef_backend.settings import load_settings


async def run(action: str) -> dict[str, object]:
    """Use the same bounded durable state as automatic background recovery."""
    settings = load_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    channel = default_live_channel_identity()
    recovery = SQLAlchemyArchiveRecovery(factory)
    try:
        if action in {"pause", "resume"}:
            await recovery.set_paused(channel.channel_id, paused=action == "pause")
        elif action == "apply":
            store = SQLAlchemyIngestionPersistence(
                factory,
                contact_cipher=build_contact_cipher(settings),
                field_origin_sync=build_offer_origin_sync(factory),
            )
            result = await RawEventDrainer(
                archive=SQLAlchemyRawEventArchive(factory),
                processor=ArchivedEventProcessor(store, decode_archived_payload),
                identity=channel,
                recovery=recovery,
            ).drain_once(release_sha=settings.release_sha)
            return asdict(result)
        return await recovery.preflight(channel.channel_id)
    finally:
        await engine.dispose()


def main() -> None:
    """Default to read-only preflight; never emit source payloads or credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("preflight", "apply", "pause", "resume"), default="preflight", nargs="?"
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args.action))
    except Exception as error:  # noqa: BLE001 - operator output must never expose SQL/source values
        sys.stderr.write(f"Archive recovery failed ({safe_error_category(error)})\n")
        raise SystemExit(2) from None
    print(json.dumps(result, default=str, sort_keys=True))  # noqa: T201


if __name__ == "__main__":
    main()
