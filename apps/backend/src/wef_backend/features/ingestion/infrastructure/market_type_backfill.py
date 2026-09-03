"""Dry-run and apply reporting for offer market-type backfill."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import (
    PARSER_VERSION,
    extract_listing,
)
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.property_type_backfill import (
    _newest_primary_source_rows,
    _PrimarySourceBackfillRow,
    _row_to_raw,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class MarketTypeBackfillSummary:
    """Aggregate redacted counts for one market-type backfill run."""

    total: int
    primary: int
    secondary: int
    unknown: int
    changed: int
    unchanged: int
    skipped_already_known: int
    failures: int
    parser_version: str


async def backfill_market_types(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None,
    apply: bool,
) -> MarketTypeBackfillSummary:
    """Re-extract market types from retained primary source revisions.

    Only processes offers whose current market_type is 'unknown'.  Only writes
    when the re-extracted value is 'primary' or 'secondary' (never downgrades
    a known value to unknown).
    """
    counts = {
        "total": 0,
        "primary": 0,
        "secondary": 0,
        "unknown": 0,
        "changed": 0,
        "unchanged": 0,
        "skipped_already_known": 0,
        "failures": 0,
    }
    async with session_factory() as session:
        statement = (
            select(
                OfferRow,
                SourceMessageRow,
                SourceChannelRow,
                OfferSourceRow.created_at,
            )
            .join(OfferSourceRow, OfferSourceRow.offer_id == OfferRow.id)
            .join(
                SourceMessageRow,
                SourceMessageRow.id == OfferSourceRow.source_message_id,
            )
            .join(SourceChannelRow, SourceChannelRow.id == SourceMessageRow.source_channel_id)
            .where(OfferSourceRow.relationship == "primary")
            .where(OfferRow.market_type == "unknown")
        )
        fetched = [
            _PrimarySourceBackfillRow(
                offer=offer,
                message=message,
                channel=channel,
                source_created_at=source_created_at,
            )
            for offer, message, channel, source_created_at in (
                await session.execute(statement)
            ).all()
        ]
    rows = _newest_primary_source_rows(fetched)
    if limit is not None:
        rows = rows[:limit]

    for row in rows:
        counts["total"] += 1
        try:
            await _process_backfill_row(
                session_factory,
                counts=counts,
                offer=row.offer,
                message=row.message,
                channel=row.channel,
                apply=apply,
            )
        except Exception:  # noqa: BLE001
            counts["failures"] += 1

    return MarketTypeBackfillSummary(
        total=counts["total"],
        primary=counts["primary"],
        secondary=counts["secondary"],
        unknown=counts["unknown"],
        changed=counts["changed"],
        unchanged=counts["unchanged"],
        skipped_already_known=counts["skipped_already_known"],
        failures=counts["failures"],
        parser_version=PARSER_VERSION,
    )


async def _process_backfill_row(  # noqa: PLR0913
    session_factory: async_sessionmaker[AsyncSession],
    *,
    counts: dict[str, int],
    offer: OfferRow,
    message: SourceMessageRow,
    channel: SourceChannelRow,
    apply: bool,
) -> None:
    # Skip offers that already have a known market type (defensive; query filters
    # these out, but guards against any race or future call-site changes).
    if offer.market_type != "unknown":
        counts["skipped_already_known"] += 1
        return

    result = extract_listing(_row_to_raw(message=message, channel=channel))
    listing = result.listing
    if listing is None:
        counts["failures"] += 1
        return

    extracted = listing.market_type.value.value if listing.market_type is not None else "unknown"

    if extracted == "primary":
        counts["primary"] += 1
    elif extracted == "secondary":
        counts["secondary"] += 1
    else:
        counts["unknown"] += 1

    if extracted == "unknown":
        # Re-extraction didn't improve on the current value; leave it alone.
        counts["unchanged"] += 1
        return

    counts["changed"] += 1
    if apply:
        await _apply_market_type(session_factory, offer.id, extracted)


async def _apply_market_type(
    session_factory: async_sessionmaker[AsyncSession],
    offer_id: UUID,
    market_type: str,
) -> None:
    async with session_factory.begin() as session:
        offer = await session.get(OfferRow, offer_id)
        if offer is None:
            return
        offer.market_type = market_type
