"""SQLAlchemy adapter for offer AI enrichment persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update

from wef_backend.features.admin.application.ai_review import SourceRevisionEvidence
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    FieldEventOutcome,
    ItemOutcome,
    ItemState,
    OfferAiEnrichmentBatch,
    OfferAiEnrichmentItem,
    OfferAiFieldEvent,
    OfferEnrichmentSnapshot,
    OfferFieldOrigin,
    OriginKind,
    OriginState,
    SyncOfferAiOrigins,
    current_field_value,
    is_missing,
    offer_input_fingerprint,
    value_fingerprint,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_models import (
    OfferAiEnrichmentBatchRow,
    OfferAiEnrichmentItemRow,
    OfferAiFieldEventRow,
    OfferFieldOriginRow,
)
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.identity.infrastructure.security import SystemClock
from wef_backend.features.ingestion.infrastructure.models import (
    OfferSourceRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_COLUMN_BY_FIELD = {
    "market_type": "market_type",
    "currency": "currency",
    "apartment_price_min": "price_min_minor",
    "apartment_price_max": "price_max_minor",
    "parking_price_min": "parking_price_min_minor",
    "parking_price_max": "parking_price_max_minor",
    "parking_included_in_price": "parking_included_in_price",
    "storage_price_min": "storage_price_min_minor",
    "storage_price_max": "storage_price_max_minor",
    "storage_included_in_price": "storage_included_in_price",
    "area_min_sqm": "area_min_sqm",
    "area_max_sqm": "area_max_sqm",
    "rooms_min": "rooms_min",
    "rooms_max": "rooms_max",
    "floor_label": "floor_label",
    "delivery_label": "delivery_label",
}
_PRICE_MAJOR_FIELDS = frozenset(
    {
        "apartment_price_min",
        "apartment_price_max",
        "parking_price_min",
        "parking_price_max",
        "storage_price_min",
        "storage_price_max",
    },
)
_OPEN_BATCH_STATES = (
    BatchState.QUEUED.value,
    BatchState.RUNNING.value,
    BatchState.PAUSED.value,
)


class SQLAlchemyOfferAiEnrichmentStore:
    """Load offers/sources and persist guarded enrichment provenance."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def count_owner_queued_items(self, owner_id: UUID) -> int:
        """Count items in queued/running/paused batches for this owner."""
        async with self._session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(OfferAiEnrichmentItemRow)
                .join(
                    OfferAiEnrichmentBatchRow,
                    OfferAiEnrichmentBatchRow.id == OfferAiEnrichmentItemRow.batch_id,
                )
                .where(
                    OfferAiEnrichmentBatchRow.owner_user_id == owner_id,
                    OfferAiEnrichmentBatchRow.state.in_(_OPEN_BATCH_STATES),
                )
            )
            count = await session.scalar(stmt)
        return int(count or 0)

    async def count_owner_provider_calls_since(self, owner_id: UUID, *, since: datetime) -> int:
        """Count this owner's enrichment provider calls at or after ``since``."""
        async with self._session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(OfferAiEnrichmentItemRow)
                .join(
                    OfferAiEnrichmentBatchRow,
                    OfferAiEnrichmentBatchRow.id == OfferAiEnrichmentItemRow.batch_id,
                )
                .where(
                    OfferAiEnrichmentBatchRow.owner_user_id == owner_id,
                    OfferAiEnrichmentItemRow.provider_called_at >= since,
                )
            )
            count = await session.scalar(stmt)
        return int(count or 0)

    async def list_missing_offer_ids(self, *, limit: int) -> tuple[UUID, ...]:
        """Return offers that still have at least one missing allowlisted field."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferRow.id)
                .where(
                    or_(
                        OfferRow.market_type == "unknown",
                        OfferRow.currency.is_(None),
                        OfferRow.price_min_minor.is_(None),
                        OfferRow.price_max_minor.is_(None),
                        OfferRow.parking_price_min_minor.is_(None),
                        OfferRow.parking_price_max_minor.is_(None),
                        and_(
                            OfferRow.parking_included_in_price.is_(False),
                            OfferRow.parking_price_min_minor.is_(None),
                            OfferRow.parking_price_max_minor.is_(None),
                        ),
                        OfferRow.storage_price_min_minor.is_(None),
                        OfferRow.storage_price_max_minor.is_(None),
                        and_(
                            OfferRow.storage_included_in_price.is_(False),
                            OfferRow.storage_price_min_minor.is_(None),
                            OfferRow.storage_price_max_minor.is_(None),
                        ),
                        OfferRow.area_min_sqm.is_(None),
                        OfferRow.area_max_sqm.is_(None),
                        OfferRow.rooms_min.is_(None),
                        OfferRow.rooms_max.is_(None),
                        OfferRow.floor_label.is_(None),
                        OfferRow.delivery_label.is_(None),
                    ),
                )
                .order_by(OfferRow.updated_at.desc(), OfferRow.id.desc())
                .limit(limit)
            )
            rows = await session.scalars(stmt)
            return tuple(rows.all())

    async def get_offer_snapshot(self, offer_id: UUID) -> OfferEnrichmentSnapshot | None:
        """Return one offer snapshot, or None when unknown."""
        async with self._session_factory() as session:
            row = await session.get(OfferRow, offer_id)
            if row is None:
                return None
            return _snapshot(row)

    async def list_offer_source_revisions(
        self,
        offer_id: UUID,
        *,
        limit: int,
    ) -> tuple[SourceRevisionEvidence, ...]:
        """Return current source revisions linked to the offer."""
        async with self._session_factory() as session:
            stmt = (
                select(SourceMessageRevisionRow)
                .join(
                    OfferSourceRow,
                    OfferSourceRow.source_message_revision_id == SourceMessageRevisionRow.id,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(
                    OfferSourceRow.offer_id == offer_id,
                    SourceMessageRow.current_revision_id == SourceMessageRevisionRow.id,
                )
                .order_by(
                    SourceMessageRevisionRow.published_at.desc(),
                    SourceMessageRevisionRow.id.desc(),
                )
                .limit(limit)
            )
            rows = await session.scalars(stmt)
        return tuple(
            SourceRevisionEvidence(
                revision_id=row.id,
                checksum=row.raw_checksum,
                published_at=row.published_at,
                text_original=row.text_original,
            )
            for row in rows
        )

    async def insert_batch(
        self,
        batch: OfferAiEnrichmentBatch,
        items: tuple[OfferAiEnrichmentItem, ...],
    ) -> None:
        """Persist a new batch and its frozen item scope."""
        async with self._session_factory() as session:
            session.add(_batch_to_row(batch))
            session.add_all(_item_to_row(item) for item in items)
            await session.commit()

    async def get_batch(self, batch_id: UUID) -> OfferAiEnrichmentBatch | None:
        """Return one batch by id."""
        async with self._session_factory() as session:
            row = await session.get(OfferAiEnrichmentBatchRow, batch_id)
            if row is None:
                return None
            return _batch_from_row(row)

    async def list_owner_batches(
        self,
        owner_id: UUID,
        *,
        limit: int = 20,
    ) -> tuple[OfferAiEnrichmentBatch, ...]:
        """Return recent enrichment batches for one owner."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiEnrichmentBatchRow)
                .where(OfferAiEnrichmentBatchRow.owner_user_id == owner_id)
                .order_by(OfferAiEnrichmentBatchRow.created_at.desc())
                .limit(limit)
            )
            rows = await session.scalars(stmt)
        return tuple(_batch_from_row(row) for row in rows)

    async def list_batch_items(self, batch_id: UUID) -> tuple[OfferAiEnrichmentItem, ...]:
        """Return all items for one batch in ordinal order."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiEnrichmentItemRow)
                .where(OfferAiEnrichmentItemRow.batch_id == batch_id)
                .order_by(OfferAiEnrichmentItemRow.ordinal)
            )
            rows = await session.scalars(stmt)
        return tuple(_item_from_row(row) for row in rows)

    async def list_batch_field_events(self, batch_id: UUID) -> tuple[OfferAiFieldEvent, ...]:
        """Return append-only field events for one batch."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiFieldEventRow)
                .where(OfferAiFieldEventRow.batch_id == batch_id)
                .order_by(OfferAiFieldEventRow.created_at, OfferAiFieldEventRow.id)
            )
            rows = await session.scalars(stmt)
        return tuple(_event_from_row(row) for row in rows)

    async def list_owner_parser_gap_events(
        self,
        owner_id: UUID,
        *,
        limit: int = 500,
    ) -> tuple[OfferAiFieldEvent, ...]:
        """Return redacted parser-gap events across an owner's batches."""
        gap_outcomes = (
            FieldEventOutcome.APPLIED.value,
            FieldEventOutcome.PARSER_CONFLICTING.value,
            FieldEventOutcome.SKIPPED.value,
            FieldEventOutcome.PROPOSED.value,
        )
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiFieldEventRow)
                .join(
                    OfferAiEnrichmentBatchRow,
                    OfferAiEnrichmentBatchRow.id == OfferAiFieldEventRow.batch_id,
                )
                .where(
                    OfferAiEnrichmentBatchRow.owner_user_id == owner_id,
                    OfferAiFieldEventRow.outcome.in_(gap_outcomes),
                )
                .order_by(OfferAiFieldEventRow.created_at.desc(), OfferAiFieldEventRow.id.desc())
                .limit(limit)
            )
            rows = await session.scalars(stmt)
        return tuple(_event_from_row(row) for row in rows)

    async def set_batch_state(
        self,
        batch_id: UUID,
        *,
        state: BatchState,
        failure_category: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> OfferAiEnrichmentBatch:
        """Update batch lifecycle fields."""
        values: dict[str, object] = {"state": state.value, "failure_category": failure_category}
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        async with self._session_factory() as session:
            await session.execute(
                update(OfferAiEnrichmentBatchRow)
                .where(OfferAiEnrichmentBatchRow.id == batch_id)
                .values(**values),
            )
            await session.commit()
            row = await session.get(OfferAiEnrichmentBatchRow, batch_id)
        if row is None:
            message = "enrichment batch disappeared after state update"
            raise RuntimeError(message)
        return _batch_from_row(row)

    async def next_item(self, batch_id: UUID) -> OfferAiEnrichmentItem | None:
        """Return the next queued or retryable processing item."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiEnrichmentItemRow)
                .where(
                    OfferAiEnrichmentItemRow.batch_id == batch_id,
                    OfferAiEnrichmentItemRow.state.in_(
                        (ItemState.QUEUED.value, ItemState.PROCESSING.value),
                    ),
                )
                .order_by(OfferAiEnrichmentItemRow.ordinal.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = await session.scalar(stmt)
            if row is None:
                return None
            return _item_from_row(row)

    async def next_queued_item(self, batch_id: UUID) -> OfferAiEnrichmentItem | None:
        """Return the next queued item for chunk collection."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiEnrichmentItemRow)
                .where(
                    OfferAiEnrichmentItemRow.batch_id == batch_id,
                    OfferAiEnrichmentItemRow.state == ItemState.QUEUED.value,
                )
                .order_by(OfferAiEnrichmentItemRow.ordinal.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = await session.scalar(stmt)
            if row is None:
                return None
            return _item_from_row(row)

    async def next_processing_item(self, batch_id: UUID) -> OfferAiEnrichmentItem | None:
        """Return the oldest in-flight item left from a partial run."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiEnrichmentItemRow)
                .where(
                    OfferAiEnrichmentItemRow.batch_id == batch_id,
                    OfferAiEnrichmentItemRow.state == ItemState.PROCESSING.value,
                )
                .order_by(OfferAiEnrichmentItemRow.ordinal.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = await session.scalar(stmt)
            if row is None:
                return None
            return _item_from_row(row)

    async def get_item(self, item_id: UUID) -> OfferAiEnrichmentItem | None:
        """Return one item by id."""
        async with self._session_factory() as session:
            row = await session.get(OfferAiEnrichmentItemRow, item_id)
            if row is None:
                return None
            return _item_from_row(row)

    async def mark_item_processing(self, item: OfferAiEnrichmentItem, *, now: datetime) -> None:
        """Mark an item processing before the provider call."""
        async with self._session_factory() as session:
            await session.execute(
                update(OfferAiEnrichmentItemRow)
                .where(OfferAiEnrichmentItemRow.id == item.id)
                .values(
                    state=ItemState.PROCESSING.value,
                    attempt_count=item.attempt_count + 1,
                    updated_at=now,
                ),
            )
            await session.commit()

    async def complete_item(  # noqa: PLR0913
        self,
        *,
        item: OfferAiEnrichmentItem,
        outcome: ItemOutcome,
        state: ItemState,
        now: datetime,
        provider_called_at: datetime | None,
        events: tuple[OfferAiFieldEvent, ...],
        apply_values: dict[str, object],
        origins: tuple[OfferFieldOrigin, ...],
        fingerprint: str,
    ) -> ItemOutcome:
        """Write events, optional canonical values, and item/batch counters."""
        async with self._session_factory.begin() as session:
            offer = await session.get(OfferRow, item.offer_id, with_for_update=True)
            row = await session.get(OfferAiEnrichmentItemRow, item.id, with_for_update=True)
            if offer is None or row is None:
                return ItemOutcome.STALE
            snapshot = _snapshot(offer)
            source_stmt = (
                select(SourceMessageRevisionRow)
                .join(
                    OfferSourceRow,
                    OfferSourceRow.source_message_revision_id == SourceMessageRevisionRow.id,
                )
                .join(
                    SourceMessageRow,
                    SourceMessageRow.id == SourceMessageRevisionRow.source_message_id,
                )
                .where(
                    OfferSourceRow.offer_id == offer.id,
                    SourceMessageRow.current_revision_id == SourceMessageRevisionRow.id,
                )
                .order_by(
                    SourceMessageRevisionRow.published_at.desc(),
                    SourceMessageRevisionRow.id.desc(),
                )
                .limit(10)
            )
            source_rows = tuple(await session.scalars(source_stmt))
            current = offer_input_fingerprint(
                snapshot,
                tuple(source.id for source in source_rows),
                tuple(source.raw_checksum for source in source_rows),
            )
            del fingerprint
            apply_values = {
                name: value for name, value in apply_values.items() if is_missing(snapshot, name)
            }
            origins = tuple(origin for origin in origins if origin.field_name in apply_values)
            if apply_values and current != item.input_fingerprint:
                outcome = ItemOutcome.STALE
                state = ItemState.FAILED
                apply_values = {}
                origins = ()
            if not apply_values:
                origins = ()
                if outcome is ItemOutcome.APPLIED:
                    outcome = ItemOutcome.NO_MISSING
                    state = ItemState.SKIPPED
            events = tuple(
                event
                for event in events
                if event.outcome is not FieldEventOutcome.APPLIED
                or event.field_name in apply_values
            )
            if apply_values:
                await session.execute(
                    update(OfferRow)
                    .where(OfferRow.id == offer.id)
                    .values(**_offer_values(apply_values), updated_at=now),
                )
            session.add_all(_event_to_row(event) for event in events)
            await session.flush()
            for origin in origins:
                await session.merge(_origin_to_row(origin))
            counters = {
                "processed_count": OfferAiEnrichmentBatchRow.processed_count + 1,
                "checkpoint_ordinal": item.ordinal + 1,
                "updated_at": now,
            }
            if outcome is ItemOutcome.APPLIED:
                counters["applied_count"] = OfferAiEnrichmentBatchRow.applied_count + 1
            elif state is ItemState.FAILED:
                counters["failed_count"] = OfferAiEnrichmentBatchRow.failed_count + 1
            else:
                counters["skipped_count"] = OfferAiEnrichmentBatchRow.skipped_count + 1
            await session.execute(
                update(OfferAiEnrichmentBatchRow)
                .where(OfferAiEnrichmentBatchRow.id == item.batch_id)
                .values(**counters),
            )
            await session.execute(
                update(OfferAiEnrichmentItemRow)
                .where(OfferAiEnrichmentItemRow.id == item.id)
                .values(
                    state=state.value,
                    outcome=outcome.value,
                    processed_at=now,
                    updated_at=now,
                    provider_called_at=provider_called_at,
                ),
            )
        return outcome

    async def list_applied_events(self, batch_id: UUID) -> tuple[OfferAiFieldEvent, ...]:
        """Return applied events for guarded revert."""
        async with self._session_factory() as session:
            stmt = (
                select(OfferAiFieldEventRow)
                .where(
                    OfferAiFieldEventRow.batch_id == batch_id,
                    OfferAiFieldEventRow.outcome == FieldEventOutcome.APPLIED.value,
                )
                .order_by(OfferAiFieldEventRow.created_at.asc())
            )
            rows = await session.scalars(stmt)
        return tuple(_event_from_row(row) for row in rows)

    async def revert_applied_event(
        self,
        event: OfferAiFieldEvent,
        *,
        actor_id: str,
        now: datetime,
    ) -> bool:
        """Clear the field only when it still equals the applied value."""
        async with self._session_factory.begin() as session:
            offer = await session.get(OfferRow, event.offer_id, with_for_update=True)
            if offer is None:
                return False
            snapshot = _snapshot(offer)
            current = current_field_value(snapshot, event.field_name)
            if value_fingerprint(current) != value_fingerprint(event.applied_value):
                return False
            await session.execute(
                update(OfferRow)
                .where(OfferRow.id == offer.id)
                .values(**_clear_values(event.field_name), updated_at=now),
            )
            await session.execute(
                update(OfferFieldOriginRow)
                .where(
                    OfferFieldOriginRow.offer_id == event.offer_id,
                    OfferFieldOriginRow.field_name == event.field_name,
                )
                .values(state=OriginState.STALE.value, updated_at=now),
            )
            session.add(
                _event_to_row(
                    OfferAiFieldEvent(
                        id=uuid4(),
                        batch_id=event.batch_id,
                        batch_item_id=event.batch_item_id,
                        offer_id=event.offer_id,
                        field_name=event.field_name,
                        proposed_value=event.applied_value,
                        applied_value=None,
                        outcome=FieldEventOutcome.ROLLED_BACK,
                        reason="reverted",
                        source_message_revision_id=event.source_message_revision_id,
                        source_start=event.source_start,
                        source_end=event.source_end,
                        source_fingerprint=event.source_fingerprint,
                        parser_version=event.parser_version,
                        model=event.model,
                        prompt_version=event.prompt_version,
                        schema_version=event.schema_version,
                        confidence=event.confidence,
                        provider_request_id=event.provider_request_id,
                        token_input=event.token_input,
                        token_output=event.token_output,
                        latency_ms=event.latency_ms,
                        actor_id=actor_id,
                        created_at=now,
                    ),
                ),
            )
        return True

    async def list_active_ai_origins(self, offer_id: UUID) -> tuple[OfferFieldOrigin, ...]:
        """Return active AI origins for one offer."""
        async with self._session_factory() as session:
            stmt = select(OfferFieldOriginRow).where(
                OfferFieldOriginRow.offer_id == offer_id,
                OfferFieldOriginRow.origin == OriginKind.AI.value,
                OfferFieldOriginRow.state == OriginState.ACTIVE.value,
            )
            rows = await session.scalars(stmt)
        return tuple(_origin_from_row(row) for row in rows)

    async def protected_field_names(self, offer_id: UUID) -> frozenset[str]:
        """Return AI-owned fields that parser upsert must not clobber."""
        async with self._session_factory() as session:
            stmt = select(OfferFieldOriginRow.field_name).where(
                OfferFieldOriginRow.offer_id == offer_id,
                OfferFieldOriginRow.origin == OriginKind.AI.value,
                OfferFieldOriginRow.state.in_(
                    (OriginState.ACTIVE.value, OriginState.CONFLICTING.value),
                ),
            )
            rows = await session.scalars(stmt)
        return frozenset(rows.all())

    async def invalidate_or_conflict_origin(
        self,
        origin: OfferFieldOrigin,
        *,
        current_value: object,
        now: datetime,
        actor_id: str,
    ) -> FieldEventOutcome:
        """Stale-clear a still-matching AI value, or mark a mismatch conflicting."""
        del current_value
        async with self._session_factory.begin() as session:
            offer = await session.get(OfferRow, origin.offer_id, with_for_update=True)
            if offer is None:
                return FieldEventOutcome.SKIPPED
            snapshot = _snapshot(offer)
            current = current_field_value(snapshot, origin.field_name)
            matches = value_fingerprint(current) == origin.value_fingerprint
            outcome = FieldEventOutcome.INVALIDATED if matches else FieldEventOutcome.SKIPPED
            if matches:
                await session.execute(
                    update(OfferRow)
                    .where(OfferRow.id == offer.id)
                    .values(**_clear_values(origin.field_name), updated_at=now),
                )
                state = OriginState.STALE.value
            else:
                state = OriginState.CONFLICTING.value
            await session.execute(
                update(OfferFieldOriginRow)
                .where(
                    OfferFieldOriginRow.offer_id == origin.offer_id,
                    OfferFieldOriginRow.field_name == origin.field_name,
                )
                .values(state=state, updated_at=now),
            )
            applied = await session.get(OfferAiFieldEventRow, origin.field_event_id)
            if applied is not None:
                session.add(
                    OfferAiFieldEventRow(
                        id=uuid4(),
                        batch_id=applied.batch_id,
                        batch_item_id=applied.batch_item_id,
                        offer_id=origin.offer_id,
                        field_name=origin.field_name,
                        proposed_value=origin.canonical_value,
                        applied_value=None,
                        outcome=outcome.value,
                        reason="source_edit" if matches else "source_edit_conflict",
                        source_message_revision_id=origin.source_revision_id,
                        source_start=None,
                        source_end=None,
                        source_fingerprint=None,
                        parser_version=origin.parser_version,
                        model=applied.model,
                        prompt_version=applied.prompt_version,
                        schema_version=applied.schema_version,
                        confidence=None,
                        provider_request_id=None,
                        token_input=None,
                        token_output=None,
                        latency_ms=None,
                        actor_id=actor_id,
                        created_at=now,
                    ),
                )
        return outcome

    async def record_parser_comparison(
        self,
        origin: OfferFieldOrigin,
        *,
        parser_value: object,
        parser_version: str,
        now: datetime,
        actor_id: str,
    ) -> FieldEventOutcome:
        """Record parser_confirmed or parser_conflicting against an AI origin."""
        matches = value_fingerprint(parser_value) == origin.value_fingerprint
        outcome = (
            FieldEventOutcome.PARSER_CONFIRMED if matches else FieldEventOutcome.PARSER_CONFLICTING
        )
        async with self._session_factory.begin() as session:
            if matches:
                await session.execute(
                    update(OfferFieldOriginRow)
                    .where(
                        OfferFieldOriginRow.offer_id == origin.offer_id,
                        OfferFieldOriginRow.field_name == origin.field_name,
                    )
                    .values(
                        origin=OriginKind.PARSER.value,
                        field_event_id=None,
                        parser_version=parser_version,
                        canonical_value=parser_value,
                        value_fingerprint=value_fingerprint(parser_value),
                        state=OriginState.ACTIVE.value,
                        updated_at=now,
                    ),
                )
            else:
                await session.execute(
                    update(OfferFieldOriginRow)
                    .where(
                        OfferFieldOriginRow.offer_id == origin.offer_id,
                        OfferFieldOriginRow.field_name == origin.field_name,
                    )
                    .values(state=OriginState.CONFLICTING.value, updated_at=now),
                )
            applied = await session.get(OfferAiFieldEventRow, origin.field_event_id)
            if applied is not None:
                session.add(
                    OfferAiFieldEventRow(
                        id=uuid4(),
                        batch_id=applied.batch_id,
                        batch_item_id=applied.batch_item_id,
                        offer_id=origin.offer_id,
                        field_name=origin.field_name,
                        proposed_value=parser_value,
                        applied_value=origin.canonical_value if matches else None,
                        outcome=outcome.value,
                        reason="parser_replay",
                        source_message_revision_id=origin.source_revision_id,
                        source_start=None,
                        source_end=None,
                        source_fingerprint=None,
                        parser_version=parser_version,
                        model=applied.model,
                        prompt_version=applied.prompt_version,
                        schema_version=applied.schema_version,
                        confidence=None,
                        provider_request_id=None,
                        token_input=None,
                        token_output=None,
                        latency_ms=None,
                        actor_id=actor_id,
                        created_at=now,
                    ),
                )
        return outcome


def _snapshot(row: OfferRow) -> OfferEnrichmentSnapshot:
    return OfferEnrichmentSnapshot(
        id=row.id,
        market_type=row.market_type,
        currency=row.currency,
        apartment_price_min=row.price_min_minor,
        apartment_price_max=row.price_max_minor,
        parking_price_min=row.parking_price_min_minor,
        parking_price_max=row.parking_price_max_minor,
        parking_included_in_price=row.parking_included_in_price,
        storage_price_min=row.storage_price_min_minor,
        storage_price_max=row.storage_price_max_minor,
        storage_included_in_price=row.storage_included_in_price,
        area_min_sqm=row.area_min_sqm,
        area_max_sqm=row.area_max_sqm,
        rooms_min=row.rooms_min,
        rooms_max=row.rooms_max,
        floor_label=row.floor_label,
        delivery_label=row.delivery_label,
        parser_version=row.parser_version,
        updated_at=row.updated_at,
    )


def _offer_values(apply_values: dict[str, object]) -> dict[str, object]:
    """Map allowlisted AI field names onto offer columns.

    Price proposals are major currency units (as quoted in source text); the
    catalog stores integer minor units, so convert on write.
    """
    values: dict[str, object] = {}
    for name, value in apply_values.items():
        column = _COLUMN_BY_FIELD[name]
        if name in {"area_min_sqm", "area_max_sqm"}:
            values[column] = Decimal(str(value))
        elif name in _PRICE_MAJOR_FIELDS:
            values[column] = int(value) * 100
        else:
            values[column] = value
    return values


def _clear_values(field_name: str) -> dict[str, object]:
    column = _COLUMN_BY_FIELD[field_name]
    if field_name == "market_type":
        return {column: "unknown"}
    if field_name in {"parking_included_in_price", "storage_included_in_price"}:
        return {column: False}
    return {column: None}


def _batch_to_row(batch: OfferAiEnrichmentBatch) -> OfferAiEnrichmentBatchRow:
    return OfferAiEnrichmentBatchRow(
        id=batch.id,
        owner_user_id=batch.owner_user_id,
        scope_json=batch.scope_json,
        candidate_count=batch.candidate_count,
        model=batch.model,
        prompt_version=batch.prompt_version,
        schema_version=batch.schema_version,
        state=batch.state.value,
        checkpoint_ordinal=batch.checkpoint_ordinal,
        processed_count=batch.processed_count,
        applied_count=batch.applied_count,
        skipped_count=batch.skipped_count,
        failed_count=batch.failed_count,
        failure_category=batch.failure_category,
        created_at=batch.created_at,
        started_at=batch.started_at,
        finished_at=batch.finished_at,
        updated_at=batch.created_at,
    )


def _batch_from_row(row: OfferAiEnrichmentBatchRow) -> OfferAiEnrichmentBatch:
    scope = row.scope_json if isinstance(row.scope_json, dict) else {}
    return OfferAiEnrichmentBatch(
        id=row.id,
        owner_user_id=row.owner_user_id,
        scope_json=dict(scope),
        candidate_count=row.candidate_count,
        model=row.model,
        prompt_version=row.prompt_version,
        schema_version=row.schema_version,
        state=BatchState(row.state),
        checkpoint_ordinal=row.checkpoint_ordinal,
        processed_count=row.processed_count,
        applied_count=row.applied_count,
        skipped_count=row.skipped_count,
        failed_count=row.failed_count,
        failure_category=row.failure_category,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def _item_to_row(item: OfferAiEnrichmentItem) -> OfferAiEnrichmentItemRow:
    return OfferAiEnrichmentItemRow(
        id=item.id,
        batch_id=item.batch_id,
        offer_id=item.offer_id,
        ordinal=item.ordinal,
        input_fingerprint=item.input_fingerprint,
        state=item.state.value,
        outcome=None if item.outcome is None else item.outcome.value,
        attempt_count=item.attempt_count,
        provider_called_at=item.provider_called_at,
        created_at=item.created_at,
        processed_at=item.processed_at,
        updated_at=item.created_at,
    )


def _item_from_row(row: OfferAiEnrichmentItemRow) -> OfferAiEnrichmentItem:
    return OfferAiEnrichmentItem(
        id=row.id,
        batch_id=row.batch_id,
        offer_id=row.offer_id,
        ordinal=row.ordinal,
        input_fingerprint=row.input_fingerprint,
        state=ItemState(row.state),
        outcome=None if row.outcome is None else ItemOutcome(row.outcome),
        attempt_count=row.attempt_count,
        provider_called_at=row.provider_called_at,
        created_at=row.created_at,
        processed_at=row.processed_at,
    )


def _event_to_row(event: OfferAiFieldEvent) -> OfferAiFieldEventRow:
    return OfferAiFieldEventRow(
        id=event.id,
        batch_id=event.batch_id,
        batch_item_id=event.batch_item_id,
        offer_id=event.offer_id,
        field_name=event.field_name,
        proposed_value=event.proposed_value,
        applied_value=event.applied_value,
        outcome=event.outcome.value,
        reason=event.reason,
        source_message_revision_id=event.source_message_revision_id,
        source_start=event.source_start,
        source_end=event.source_end,
        source_fingerprint=event.source_fingerprint,
        parser_version=event.parser_version,
        model=event.model,
        prompt_version=event.prompt_version,
        schema_version=event.schema_version,
        confidence=event.confidence,
        provider_request_id=event.provider_request_id,
        token_input=event.token_input,
        token_output=event.token_output,
        latency_ms=event.latency_ms,
        actor_id=event.actor_id,
        created_at=event.created_at,
    )


def _event_from_row(row: OfferAiFieldEventRow) -> OfferAiFieldEvent:
    return OfferAiFieldEvent(
        id=row.id,
        batch_id=row.batch_id,
        batch_item_id=row.batch_item_id,
        offer_id=row.offer_id,
        field_name=row.field_name,
        proposed_value=row.proposed_value,
        applied_value=row.applied_value,
        outcome=FieldEventOutcome(row.outcome),
        reason=row.reason,
        source_message_revision_id=row.source_message_revision_id,
        source_start=row.source_start,
        source_end=row.source_end,
        source_fingerprint=row.source_fingerprint,
        parser_version=row.parser_version,
        model=row.model,
        prompt_version=row.prompt_version,
        schema_version=row.schema_version,
        confidence=row.confidence,
        provider_request_id=row.provider_request_id,
        token_input=row.token_input,
        token_output=row.token_output,
        latency_ms=row.latency_ms,
        actor_id=row.actor_id,
        created_at=row.created_at,
    )


def _origin_to_row(origin: OfferFieldOrigin) -> OfferFieldOriginRow:
    return OfferFieldOriginRow(
        offer_id=origin.offer_id,
        field_name=origin.field_name,
        origin=origin.origin.value,
        value_fingerprint=origin.value_fingerprint,
        canonical_value=origin.canonical_value,
        source_revision_id=origin.source_revision_id,
        parser_version=origin.parser_version,
        field_event_id=origin.field_event_id,
        state=origin.state.value,
        updated_at=origin.updated_at,
    )


def _origin_from_row(row: OfferFieldOriginRow) -> OfferFieldOrigin:
    return OfferFieldOrigin(
        offer_id=row.offer_id,
        field_name=row.field_name,
        origin=OriginKind(row.origin),
        value_fingerprint=row.value_fingerprint,
        canonical_value=row.canonical_value,
        source_revision_id=row.source_revision_id,
        parser_version=row.parser_version,
        field_event_id=row.field_event_id,
        state=OriginState(row.state),
        updated_at=row.updated_at,
    )


def build_offer_origin_sync(
    session_factory: async_sessionmaker[AsyncSession],
) -> SyncOfferAiOrigins:
    """Wire parser-upsert origin sync for ingestion commands."""
    return SyncOfferAiOrigins(SQLAlchemyOfferAiEnrichmentStore(session_factory), SystemClock())
