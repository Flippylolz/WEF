"""Operator CLI: paced ingestion AI parse generate/apply for open parse issues."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text

from wef_backend.composition import build_services
from wef_backend.database import create_database_resources
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyStatus,
    IngestionAiParseStatus,
)
from wef_backend.settings import Settings, load_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class BatchCandidate:
    """One open parse issue eligible for owner AI recovery."""

    external_message_id: int
    source_message_revision_id: UUID


@dataclass(frozen=True, slots=True)
class BatchIngestionAiParseOptions:
    """Inputs for one operator batch run."""

    owner_id: UUID | None
    limit: int
    spacing_seconds: float
    generate_only: bool
    link_existing: bool
    min_text_length: int
    settings: Settings | None = None


@dataclass(slots=True)
class BatchIngestionAiParseSummary:
    """Redacted JSON summary for one operator batch."""

    linked_existing_offers: int = 0
    candidates_considered: int = 0
    generated: int = 0
    applied: int = 0
    skipped: dict[str, int] = field(default_factory=dict)


_LINK_EXISTING_OFFERS_SQL = text(
    """
    UPDATE source_message_parse_issues AS smpi
    SET offer_id = os.offer_id
    FROM offer_sources AS os
    WHERE os.source_message_id = smpi.source_message_id
      AND os.relationship = 'primary'
      AND smpi.offer_id IS NULL
    """,
)

_CANDIDATES_SQL = text(
    """
    SELECT DISTINCT ON (md5(left(smr.text_original, 200)))
      sm.external_message_id,
      smpi.source_message_revision_id
    FROM source_message_parse_issues AS smpi
    JOIN source_messages AS sm ON sm.id = smpi.source_message_id
    JOIN source_message_revisions AS smr ON smr.id = smpi.source_message_revision_id
    WHERE smpi.offer_id IS NULL
      AND smpi.issue_outcome = 'parser_miss'
      AND length(smr.text_original) >= :min_text_length
      AND smr.text_original NOT ILIKE '%Serock%'
      AND smr.text_original NOT ILIKE '%Dosin%'
      AND smr.text_original NOT ILIKE '%застройщика%'
      AND smr.text_original NOT ILIKE '%0% комиссии%'
    ORDER BY md5(left(smr.text_original, 200)), sm.external_message_id DESC
    LIMIT :limit
    """,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate and optionally apply Groq ingestion AI parse proposals for "
            "open parser_miss rows. Respects the owner daily budget and should be "
            "paced below Groq free-tier RPM (~30/min)."
        ),
    )
    parser.add_argument(
        "--owner-id",
        type=UUID,
        default=None,
        help="Owner user id (defaults to the configured bootstrap owner account)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max distinct open parse issues to attempt in this run (default: 10)",
    )
    parser.add_argument(
        "--spacing-seconds",
        type=float,
        default=2.5,
        help="Minimum delay between generate calls (default: 2.5)",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Stop after generate; do not apply proposals",
    )
    parser.add_argument(
        "--link-existing-offers",
        action="store_true",
        help=("Before batching, link parse issues to existing primary offers via offer_sources"),
    )
    parser.add_argument(
        "--min-text-length",
        type=int,
        default=120,
        help="Minimum source revision length for candidate selection (default: 120)",
    )
    return parser


async def resolve_owner_id(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    owner_id: UUID | None,
) -> UUID:
    """Resolve the owner id from CLI input or bootstrap settings."""
    if owner_id is not None:
        return owner_id
    username = settings.bootstrap_owner_username
    if not username:
        message = "bootstrap owner username is not configured"
        raise RuntimeError(message)
    async with session_factory() as session:
        resolved = (
            await session.execute(
                text(
                    """
                    SELECT id
                    FROM users
                    WHERE username = :username
                      AND role = 'owner'
                    LIMIT 1
                    """,
                ),
                {"username": username},
            )
        ).scalar_one_or_none()
    if resolved is None:
        message = "bootstrap owner account was not found"
        raise RuntimeError(message)
    return UUID(str(resolved))


async def link_existing_offers(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Attach offer_id on parse issues that already have a primary offer."""
    async with session_factory() as session:
        result = await session.execute(_LINK_EXISTING_OFFERS_SQL)
        await session.commit()
        return int(result.rowcount or 0)


async def load_candidates(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int,
    min_text_length: int,
) -> tuple[BatchCandidate, ...]:
    """Return distinct open parser_miss revisions for one bounded batch."""
    async with session_factory() as session:
        rows = (
            await session.execute(
                _CANDIDATES_SQL,
                {"limit": limit, "min_text_length": min_text_length},
            )
        ).all()
    return tuple(
        BatchCandidate(
            external_message_id=int(external_message_id),
            source_message_revision_id=UUID(str(revision_id)),
        )
        for external_message_id, revision_id in rows
    )


def _skip(summary: BatchIngestionAiParseSummary, reason: str) -> None:
    summary.skipped[reason] = summary.skipped.get(reason, 0) + 1


async def run_batch(options: BatchIngestionAiParseOptions) -> BatchIngestionAiParseSummary:
    """Run one paced generate/apply batch and return redacted counts."""
    runtime_settings = options.settings or load_settings()
    database = create_database_resources(runtime_settings.database_url)
    summary = BatchIngestionAiParseSummary()
    try:
        owner = await resolve_owner_id(
            database.session_factory,
            runtime_settings,
            owner_id=options.owner_id,
        )
        if options.link_existing:
            summary.linked_existing_offers = await link_existing_offers(
                database.session_factory,
            )
        candidates = await load_candidates(
            database.session_factory,
            limit=options.limit,
            min_text_length=options.min_text_length,
        )
        summary.candidates_considered = len(candidates)
        admin = build_services(runtime_settings).admin
        for index, candidate in enumerate(candidates):
            if index and options.spacing_seconds > 0:
                await asyncio.sleep(options.spacing_seconds)
            outcome = await admin.generate_ingestion_ai_parse(
                owner_id=owner,
                source_message_revision_id=candidate.source_message_revision_id,
                request_id=uuid4(),
            )
            if outcome.status is not IngestionAiParseStatus.GENERATED or outcome.run is None:
                reason = outcome.reason or outcome.status.value
                _skip(summary, reason)
                continue
            summary.generated += 1
            if options.generate_only:
                continue
            try:
                applied = await admin.apply_ingestion_ai_parse(
                    owner_id=owner,
                    run_id=outcome.run.id,
                    request_id=uuid4(),
                )
            except AdminDeniedError as error:
                _skip(summary, str(error))
                continue
            if applied.status is IngestionAiApplyStatus.APPLIED:
                summary.applied += 1
            else:
                _skip(summary, applied.status.value)
        return summary
    finally:
        await database.engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print batch counts as JSON; exit 2 on failure."""
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(
            run_batch(
                BatchIngestionAiParseOptions(
                    owner_id=args.owner_id,
                    limit=args.limit,
                    spacing_seconds=args.spacing_seconds,
                    generate_only=args.generate_only,
                    link_existing=args.link_existing_offers,
                    min_text_length=args.min_text_length,
                ),
            ),
        )
    except Exception:  # noqa: BLE001
        sys.stderr.write("Batch ingestion AI parse failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(asdict(payload), sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
