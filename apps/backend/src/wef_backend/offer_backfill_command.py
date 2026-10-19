"""Bounded current-revision offer backfill; dry-run by default, resumable by source ID."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter

from sqlalchemy import select

from wef_backend.composition import build_contact_cipher
from wef_backend.database import create_database_resources
from wef_backend.features.admin.infrastructure.ai_enrichment_store import build_offer_origin_sync
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION
from wef_backend.features.ingestion.application.persistence import (
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
)
from wef_backend.features.ingestion.infrastructure.models import SourceChannelRow, SourceMessageRow
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.settings import load_settings

MAX_PAGE_SIZE = 500


async def run(
    *, channel: str, after_id: int, through_id: int, limit: int, apply: bool
) -> dict[str, object]:
    """Process one frozen, bounded page; receipts contain counts and IDs, no source text."""
    if after_id < 0 or through_id <= after_id or not 1 <= limit <= MAX_PAGE_SIZE:
        message = "require 0 <= after-id < through-id and limit 1..500"
        raise ValueError(message)
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        async with database.session_factory() as session:
            source_channel = await session.scalar(
                select(SourceChannelRow).where(SourceChannelRow.external_id == channel)
            )
            if source_channel is None:
                message = "unknown source channel"
                raise ValueError(message)
            rows = (
                await session.execute(
                    select(
                        SourceMessageRow.external_message_id, SourceMessageRow.current_revision_id
                    )
                    .where(
                        SourceMessageRow.source_channel_id == source_channel.id,
                        SourceMessageRow.external_message_id > after_id,
                        SourceMessageRow.external_message_id <= through_id,
                        SourceMessageRow.deleted_at.is_(None),
                    )
                    .order_by(SourceMessageRow.external_message_id)
                    .limit(limit)
                )
            ).all()
            channel_id = source_channel.id
        store = SQLAlchemyIngestionPersistence(
            database.session_factory,
            contact_cipher=build_contact_cipher(settings) if apply else None,
            field_origin_sync=build_offer_origin_sync(database.session_factory) if apply else None,
        )
        run_id = (
            await store.start_run(
                channel_id=channel_id,
                mode=RunMode.REPROCESS,
                parser_version=PARSER_VERSION,
                source_checksum=None,
                release_sha=settings.release_sha,
            )
            if apply
            else None
        )
        counts: Counter[str] = Counter()
        cursor = after_id
        try:
            for row in rows:
                counts[
                    await store.replay_current_revision(row.current_revision_id, run_id=run_id)
                ] += 1
                cursor = row.external_message_id
        except Exception:
            if run_id is not None:
                await store.finish_run(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    counts=RunCounts(
                        seen=sum(counts.values()),
                        unchanged=counts["update_candidate"]
                        + counts["create_candidate"]
                        + counts["current"],
                        skipped_non_candidate=counts["non_candidate"] + counts["stale"],
                        offers=counts["create_candidate"],
                    ),
                    checkpoint=RunCheckpoint(),
                    error_summary=f"bounded_backfill_failed_after_id={cursor}",
                )
            raise
        if run_id is not None:
            await store.finish_run(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                counts=RunCounts(
                    seen=sum(counts.values()),
                    unchanged=counts["update_candidate"]
                    + counts["create_candidate"]
                    + counts["current"],
                    skipped_non_candidate=counts["non_candidate"] + counts["stale"],
                    offers=counts["create_candidate"],
                ),
                checkpoint=RunCheckpoint(),
                error_summary=None,
            )
        return {
            "apply": apply,
            "parser_version": PARSER_VERSION,
            "run_id": str(run_id) if run_id else None,
            "after_id": after_id,
            "through_id": through_id,
            "next_after_id": cursor,
            "scanned": len(rows),
            "exhausted": len(rows) < limit,
            "counts": dict(counts),
        }
    finally:
        await database.engine.dispose()


def main() -> None:
    """Require an explicit channel, frozen upper bound and apply switch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--after-id", type=int, default=0)
    parser.add_argument("--through-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        receipt = asyncio.run(
            run(
                channel=args.channel,
                after_id=args.after_id,
                through_id=args.through_id,
                limit=args.limit,
                apply=args.apply,
            )
        )
    except Exception as error:  # noqa: BLE001
        sys.stderr.write(f"Offer backfill failed: {type(error).__name__}\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
