"""Dry-run and apply reporting for offer area backfill."""

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
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class AreaBackfillSummary:
    """Aggregate redacted counts for one area backfill run."""

    total: int
    filled: int
    unchanged: int
    skipped_already_known: int
    failures: int
    parser_version: str


async def backfill_areas(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None,
    apply: bool,
) -> AreaBackfillSummary:
    """Re-extract area from retained primary source revisions.

    Only processes offers whose current area_min_sqm is NULL. Only writes when
    extraction returns a bounded area range (never clears a known value).
    """
    counts = {
        "total": 0,
        "filled": 0,
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
            .where(OfferRow.area_min_sqm.is_(None))
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

    return AreaBackfillSummary(
        total=counts["total"],
        filled=counts["filled"],
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
    if offer.area_min_sqm is not None:
        counts["skipped_already_known"] += 1
        return

    result = extract_listing(_row_to_raw(message=message, channel=channel))
    listing = result.listing
    if listing is None:
        counts["failures"] += 1
        return

    if listing.area_sqm is None:
        counts["unchanged"] += 1
        return

    counts["filled"] += 1
    if apply:
        await _apply_area(
            session_factory,
            offer.id,
            listing.area_sqm.value.lower,
            listing.area_sqm.value.upper,
        )


async def _apply_area(
    session_factory: async_sessionmaker[AsyncSession],
    offer_id: UUID,
    area_min_sqm: Decimal,
    area_max_sqm: Decimal,
) -> None:
    async with session_factory.begin() as session:
        offer = await session.get(OfferRow, offer_id)
        if offer is None:
            return
        offer.area_min_sqm = area_min_sqm
        offer.area_max_sqm = area_max_sqm
