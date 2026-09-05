"""Explicit, bounded reversal of unchanged still-parser-owned replay fields."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, text

from wef_backend.features.admin.application.offer_enrichment import value_fingerprint
from wef_backend.features.admin.infrastructure.ai_enrichment_models import OfferFieldOriginRow
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.parser_replay import FIELD_COLUMNS, scalar
from wef_backend.features.ingestion.application.persistence import extraction_fingerprint
from wef_backend.features.ingestion.infrastructure.models import OfferSourceRow, SourceMessageRow

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def rollback_parser_work(  # noqa: C901, PLR0912 - coupled rollback guards share one transaction
    sessions: async_sessionmaker[AsyncSession], work_id: UUID, now: datetime
) -> dict[str, int]:
    """Pause its release and reverse one job atomically; never schedule this automatically."""
    result = {"reverted": 0, "protected_conflict": 0}
    async with sessions.begin() as session:
        work = (
            (
                await session.execute(
                    text("SELECT * FROM parser_replay_work WHERE id=:id"), {"id": work_id}
                )
            )
            .mappings()
            .one_or_none()
        )
        if work is None:
            return result
        await session.execute(
            text(
                """
UPDATE parser_replay_releases SET phase='paused',reason='rollback' WHERE
version=:release
"""
            ),
            {"release": work["release_version"]},
        )
        message = await session.get(SourceMessageRow, work["message_id"], with_for_update=True)
        rows = (
            (
                await session.execute(
                    text("""
SELECT * FROM parser_replay_field_events WHERE work_id=:id AND
reverted_at IS NULL ORDER BY field_name FOR UPDATE
"""),
                    {"id": work_id},
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return result
        offer = await session.get(OfferRow, rows[0]["offer_id"], with_for_update=True)
        origins = {
            row.field_name: row
            for row in (
                await session.scalars(
                    select(OfferFieldOriginRow)
                    .where(OfferFieldOriginRow.offer_id == rows[0]["offer_id"])
                    .with_for_update()
                )
            ).all()
        }
        source_current = (
            message is not None
            and message.current_revision_id == work["revision_id"]
            and message.deleted_at is None
        )
        protected: set[str] = set()
        for event in rows:
            name = event["field_name"]
            origin = origins.get(name)
            matches = (
                source_current
                and offer is not None
                and origin is not None
                and origin.origin == "parser"
                and origin.state == "active"
                and origin.parser_version == event["parser_version"]
                and origin.source_revision_id == work["revision_id"]
                and origin.value_fingerprint == value_fingerprint(event["after_value"])
                and scalar(getattr(offer, FIELD_COLUMNS[name])) == event["after_value"]
            )
            if not matches:
                protected.add(event["before_origin"]["group"])
        # Money/currency are one rollback unit too.
        if protected & {"apartment_price", "parking_price", "storage_price"}:
            protected |= {"apartment_price", "parking_price", "storage_price"}
        link = await session.scalar(
            select(OfferSourceRow)
            .where(
                OfferSourceRow.source_message_revision_id == work["revision_id"],
                OfferSourceRow.offer_id == rows[0]["offer_id"],
            )
            .with_for_update()
        )
        document = (
            dict(link.extraction_json)
            if link is not None and isinstance(link.extraction_json, dict)
            else {}
        )
        for event in rows:
            before = event["before_origin"]
            if before["group"] in protected or offer is None or link is None:
                result["protected_conflict"] += 1
                await session.execute(
                    text(
                        """
UPDATE parser_replay_field_events SET
rollback_reason='protected_conflict' WHERE id=:id
"""
                    ),
                    {"id": event["id"]},
                )
                continue
            name, value = event["field_name"], event["before_value"]
            setattr(
                offer,
                FIELD_COLUMNS[name],
                Decimal(str(value)) if name.startswith("area_") and value is not None else value,
            )
            origin = origins[name]
            if before["origin"] is None:
                await session.delete(origin)
            else:
                origin.origin, origin.state = before["origin"], before["state"]
                origin.parser_version, origin.canonical_value = (
                    before["parser_version"],
                    before["canonical_value"],
                )
                origin.value_fingerprint = before["value_fingerprint"]
                origin.source_revision_id = (
                    UUID(before["source_revision_id"]) if before["source_revision_id"] else None
                )
                origin.updated_at = now
            if before["extraction"] is None:
                document.pop(before["group"], None)
            else:
                document[before["group"]] = before["extraction"]
            await session.execute(
                text("""
UPDATE parser_replay_field_events SET
reverted_at=:now,rollback_reason='reverted' WHERE id=:id
"""),
                {"id": event["id"], "now": now},
            )
            result["reverted"] += 1
        if offer is not None and link is not None and result["reverted"]:
            link.extraction_json = document
            offer.canonical_fingerprint = extraction_fingerprint(document)
            offer.updated_at = now
            if not result["protected_conflict"]:
                offer.parser_version = rows[0]["before_origin"]["offer_parser_version"]
    return result
