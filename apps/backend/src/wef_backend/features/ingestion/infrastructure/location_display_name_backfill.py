"""Dry-run and apply reporting for location display-name backfill."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import select

from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import normalize_location_text
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform, freeze_json
from wef_backend.features.ingestion.domain.model import RawMessage
from wef_backend.features.ingestion.infrastructure.models import (
    LocationGeocodeSelectionRow,
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_OPERATOR_VERIFIED_ACTOR = "operator"


@dataclass(frozen=True, slots=True)
class LocationDisplayNameBackfillSummary:
    """Aggregate redacted counts for one location display-name backfill run."""

    total: int
    changed: int
    unchanged: int
    skipped_verified: int
    failures: int


@dataclass(frozen=True, slots=True)
class _LocationSourceBackfillRow:
    """One primary source revision eligible for location display-name replay."""

    location: LocationRow
    message: SourceMessageRow
    channel: SourceChannelRow
    source_created_at: datetime


def _newest_primary_source_rows(
    rows: Sequence[_LocationSourceBackfillRow],
) -> list[_LocationSourceBackfillRow]:
    """Keep the newest primary source revision for each location."""
    ordered = sorted(
        rows,
        key=lambda row: (
            -row.message.published_at.timestamp(),
            -row.source_created_at.timestamp(),
        ),
    )
    selected: list[_LocationSourceBackfillRow] = []
    seen_location_ids: set[UUID] = set()
    for row in ordered:
        if row.location.id in seen_location_ids:
            continue
        seen_location_ids.add(row.location.id)
        selected.append(row)
    return sorted(selected, key=lambda row: row.location.id)


async def backfill_location_display_names(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None,
    apply: bool,
) -> LocationDisplayNameBackfillSummary:
    """Rename non-verified locations using retained primary source evidence."""
    counts = {
        "total": 0,
        "changed": 0,
        "unchanged": 0,
        "skipped_verified": 0,
        "failures": 0,
    }
    async with session_factory() as session:
        verified_location_ids = set(
            await session.scalars(
                select(LocationGeocodeSelectionRow.location_id).where(
                    LocationGeocodeSelectionRow.actor_type == _OPERATOR_VERIFIED_ACTOR,
                ),
            ),
        )
        statement = (
            select(
                LocationRow,
                SourceMessageRow,
                SourceChannelRow,
                OfferSourceRow.created_at,
            )
            .join(OfferRow, OfferRow.location_id == LocationRow.id)
            .join(OfferSourceRow, OfferSourceRow.offer_id == OfferRow.id)
            .join(
                SourceMessageRow,
                SourceMessageRow.id == OfferSourceRow.source_message_id,
            )
            .join(SourceChannelRow, SourceChannelRow.id == SourceMessageRow.source_channel_id)
            .where(OfferSourceRow.relationship == "primary")
        )
        fetched = [
            _LocationSourceBackfillRow(
                location=location,
                message=message,
                channel=channel,
                source_created_at=source_created_at,
            )
            for location, message, channel, source_created_at in (
                await session.execute(statement)
            ).all()
        ]

    rows = _newest_primary_source_rows(fetched)
    if limit is not None:
        rows = rows[:limit]

    for row in rows:
        if row.location.id in verified_location_ids:
            counts["skipped_verified"] += 1
            continue
        counts["total"] += 1
        try:
            await _process_backfill_row(
                session_factory,
                counts=counts,
                location=row.location,
                message=row.message,
                channel=row.channel,
                apply=apply,
            )
        except Exception:  # noqa: BLE001
            counts["failures"] += 1

    return LocationDisplayNameBackfillSummary(
        total=counts["total"],
        changed=counts["changed"],
        unchanged=counts["unchanged"],
        skipped_verified=counts["skipped_verified"],
        failures=counts["failures"],
    )


async def _process_backfill_row(  # noqa: PLR0913
    session_factory: async_sessionmaker[AsyncSession],
    *,
    counts: dict[str, int],
    location: LocationRow,
    message: SourceMessageRow,
    channel: SourceChannelRow,
    apply: bool,
) -> None:
    result = extract_listing(_row_to_raw(message=message, channel=channel))
    listing = result.listing
    if listing is None or listing.location is None:
        counts["failures"] += 1
        return
    normalized_name = normalize_location_text(
        listing.location.value,
        district=listing.district.value if listing.district else None,
    )
    if normalized_name == location.display_name and normalized_name == location.display_address:
        counts["unchanged"] += 1
        return
    counts["changed"] += 1
    if apply:
        await _apply_display_name(
            session_factory,
            location_id=location.id,
            display_name=normalized_name,
            expected_hash=location.normalized_address_hash,
        )


async def _apply_display_name(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    location_id: UUID,
    display_name: str,
    expected_hash: str,
) -> None:
    async with session_factory.begin() as session:
        location = await session.get(LocationRow, location_id)
        if location is None:
            return
        if location.normalized_address_hash != expected_hash:
            message = "location identity hash changed during display-name backfill"
            raise RuntimeError(message)
        location.display_name = display_name
        location.display_address = display_name


def _payload_for_message(*, payload: object, external_message_id: int) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return cast("Mapping[str, object]", payload)
    if payload:
        parsed = json.loads(payload) if isinstance(payload, str) else payload
        if isinstance(parsed, Mapping):
            return cast("Mapping[str, object]", parsed)
    return {"id": external_message_id}


def _row_to_raw(*, message: SourceMessageRow, channel: SourceChannelRow) -> RawMessage:
    payload = _payload_for_message(
        payload=message.raw_payload_json,
        external_message_id=message.external_message_id,
    )
    frozen = freeze_json(dict(payload))
    if not isinstance(frozen, Mapping):
        error = "source message payload must freeze as an object"
        raise TypeError(error)
    return RawMessage(
        source=SourceIdentity(
            platform=SourcePlatform.TELEGRAM,
            channel_id=channel.external_id,
            channel_name=channel.display_name,
            channel_type="public_channel",
        ),
        external_message_id=int(message.external_message_id),
        reply_to_message_id=None,
        published_at=message.published_at,
        edited_at=message.edited_at,
        message_type=message.message_type or "message",
        text=message.text_original or "",
        original_text=message.text_original or "",
        text_entities=(),
        media=(),
        raw_payload=frozen,
        checksum=message.raw_checksum,
    )
