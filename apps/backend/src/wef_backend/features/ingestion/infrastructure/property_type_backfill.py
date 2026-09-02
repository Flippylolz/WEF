"""Dry-run and apply reporting for offer property-type backfill."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import select

from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import (
    PARSER_VERSION,
    extract_listing,
)
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform, freeze_json
from wef_backend.features.ingestion.domain.model import RawMessage
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class PropertyTypeBackfillSummary:
    """Aggregate redacted counts for one property-type backfill run."""

    total: int
    apartment: int
    house: int
    semi_detached: int
    unknown: int
    conflicts: int
    changed: int
    unchanged: int
    failures: int
    parser_version: str


async def backfill_property_types(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int | None,
    apply: bool,
) -> PropertyTypeBackfillSummary:
    """Re-extract property types from retained primary source revisions."""
    counts = {
        "total": 0,
        "apartment": 0,
        "house": 0,
        "semi_detached": 0,
        "unknown": 0,
        "conflicts": 0,
        "changed": 0,
        "unchanged": 0,
        "failures": 0,
    }
    async with session_factory() as session:
        statement = (
            select(OfferRow, SourceMessageRow, SourceChannelRow)
            .join(OfferSourceRow, OfferSourceRow.offer_id == OfferRow.id)
            .join(
                SourceMessageRow,
                SourceMessageRow.id == OfferSourceRow.source_message_id,
            )
            .join(SourceChannelRow, SourceChannelRow.id == SourceMessageRow.source_channel_id)
            .where(OfferSourceRow.relationship == "primary")
            .order_by(OfferRow.id)
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = (await session.execute(statement)).all()

    for offer, message, channel in rows:
        counts["total"] += 1
        try:
            await _process_backfill_row(
                session_factory,
                counts=counts,
                offer=offer,
                message=message,
                channel=channel,
                apply=apply,
            )
        except Exception:  # noqa: BLE001
            counts["failures"] += 1

    return PropertyTypeBackfillSummary(
        total=counts["total"],
        apartment=counts["apartment"],
        house=counts["house"],
        semi_detached=counts["semi_detached"],
        unknown=counts["unknown"],
        conflicts=counts["conflicts"],
        changed=counts["changed"],
        unchanged=counts["unchanged"],
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
    result = extract_listing(_row_to_raw(message=message, channel=channel))
    listing = result.listing
    if listing is None:
        counts["failures"] += 1
        return
    extracted = (
        listing.property_type.value.value if listing.property_type is not None else "unknown"
    )
    if any(warning.field_name == "property_type" for warning in result.warnings):
        counts["conflicts"] += 1
    if extracted == "apartment":
        counts["apartment"] += 1
    elif extracted == "house":
        counts["house"] += 1
    elif extracted == "semi_detached":
        counts["semi_detached"] += 1
    else:
        counts["unknown"] += 1
    if offer.property_type == extracted:
        counts["unchanged"] += 1
        return
    counts["changed"] += 1
    if apply:
        await _apply_property_type(session_factory, offer.id, extracted)


async def _apply_property_type(
    session_factory: async_sessionmaker[AsyncSession],
    offer_id: UUID,
    property_type: str,
) -> None:
    async with session_factory.begin() as session:
        offer = await session.get(OfferRow, offer_id)
        if offer is None:
            return
        offer.property_type = property_type


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
