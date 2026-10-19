"""Real database boundaries for guarded AI writes and stale provenance handles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, update

from tests.fakes import FakeClock
from tests.test_offer_ai_enrichment_integration import (
    _NOW,
    TEST_DATABASE_URL,
    _owner,
    _prepare,
    _runtime,
    _seed_offer,
)
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    FieldEventOutcome,
    ItemOutcome,
    ItemState,
    OfferAiEnrichmentBatch,
    OfferAiEnrichmentItem,
    OfferAiFieldEvent,
    OfferFieldOrigin,
    OriginKind,
    OriginState,
    StartOfferEnrichmentBatch,
    value_fingerprint,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_models import (
    OfferAiEnrichmentItemRow,
    OfferAiFieldEventRow,
    OfferFieldOriginRow,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_store import (
    SQLAlchemyOfferAiEnrichmentStore,
)
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.infrastructure.models import OfferSourceRow

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from wef_backend.database import DatabaseResources

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]

_TEXT = "Piętro 4. Rynek pierwotny. Parking w cenie. Komórka w cenie. 3 pokoje."
_FRAGMENTS = {
    "floor_label": "Piętro 4",
    "market_type": "Rynek pierwotny",
    "parking_included_in_price": "Parking w cenie",
    "storage_included_in_price": "Komórka w cenie",
    "rooms_min": "3 pokoje",
}


@dataclass
class EnrichmentRows:
    """Isolated persisted source, owner and queued enrichment identities."""

    database: DatabaseResources
    store: SQLAlchemyOfferAiEnrichmentStore
    owner_id: UUID
    offer_id: UUID
    revision_id: UUID
    batch: OfferAiEnrichmentBatch
    item: OfferAiEnrichmentItem


@pytest.fixture
async def enrichment_rows() -> AsyncIterator[EnrichmentRows]:
    database = await _prepare()
    try:
        store = SQLAlchemyOfferAiEnrichmentStore(database.session_factory)
        owner_id = await _owner(database)
        offer_id, revision_id = await _seed_offer(database, _TEXT)
        batch = await StartOfferEnrichmentBatch(
            store,
            SQLAlchemyAdminAuditStore(database.session_factory),
            FakeClock(moment=_NOW),
            _runtime(),
        )(owner_id=owner_id, request_id=uuid4(), offer_ids=(offer_id,))
        item = await store.next_item(batch.id)
        assert item is not None
        await store.mark_item_processing(item, now=_NOW)
        batch = await store.set_batch_state(batch.id, state=BatchState.RUNNING, started_at=_NOW)
        yield EnrichmentRows(database, store, owner_id, offer_id, revision_id, batch, item)
    finally:
        await database.engine.dispose()


def _event(
    rows: EnrichmentRows,
    *,
    item: OfferAiEnrichmentItem | None = None,
    field: str = "floor_label",
    value: object = "4",
) -> OfferAiFieldEvent:
    selected = item or rows.item
    fragment = _FRAGMENTS[field]
    start = _TEXT.index(fragment)
    return OfferAiFieldEvent(
        id=uuid4(),
        batch_id=selected.batch_id,
        batch_item_id=selected.id,
        offer_id=rows.offer_id,
        field_name=field,
        proposed_value=value,
        applied_value=value,
        outcome=FieldEventOutcome.APPLIED,
        reason="synthetic_boundary",
        source_message_revision_id=rows.revision_id,
        source_start=start,
        source_end=start + len(fragment),
        source_fingerprint=sha256(fragment.encode()).hexdigest(),
        parser_version="test",
        model=rows.batch.model,
        prompt_version=rows.batch.prompt_version,
        schema_version=rows.batch.schema_version,
        confidence="high",
        provider_request_id="synthetic",
        token_input=1,
        token_output=1,
        latency_ms=1,
        actor_id=str(rows.owner_id),
        created_at=max(_NOW, selected.created_at),
    )


def _origin(rows: EnrichmentRows, event: OfferAiFieldEvent) -> OfferFieldOrigin:
    return OfferFieldOrigin(
        offer_id=rows.offer_id,
        field_name=event.field_name,
        origin=OriginKind.AI,
        value_fingerprint=value_fingerprint(event.applied_value),
        canonical_value=event.applied_value,
        source_revision_id=rows.revision_id,
        parser_version="test",
        field_event_id=event.id,
        state=OriginState.ACTIVE,
        updated_at=_NOW,
    )


async def _complete(
    rows: EnrichmentRows,
    *,
    item: OfferAiEnrichmentItem | None = None,
    values: dict[str, object] | None = None,
    events: tuple[OfferAiFieldEvent, ...] | None = None,
    outcome: ItemOutcome = ItemOutcome.APPLIED,
    state: ItemState = ItemState.SUCCEEDED,
) -> tuple[ItemOutcome, OfferAiFieldEvent]:
    selected = item or rows.item
    event = _event(rows, item=selected)
    records = (event,) if events is None else events
    result = await rows.store.complete_item(
        item=selected,
        outcome=outcome,
        state=state,
        now=max(_NOW, selected.created_at),
        provider_called_at=max(_NOW, selected.created_at),
        events=records,
        apply_values={"floor_label": "4"} if values is None else values,
        origins=tuple(
            _origin(rows, record)
            for record in records
            if record.outcome is FieldEventOutcome.APPLIED
        ),
        fingerprint=selected.input_fingerprint,
    )
    return result, records[0] if records else event


async def _change_offer(rows: EnrichmentRows, values: dict[str, object]) -> None:
    async with rows.database.session_factory.begin() as session:
        await session.execute(update(OfferRow).where(OfferRow.id == rows.offer_id).values(**values))


async def _remove_provenance(rows: EnrichmentRows) -> None:
    """Simulate a retired history handle while retaining its caller's immutable snapshot."""
    async with rows.database.session_factory.begin() as session:
        await session.execute(
            delete(OfferFieldOriginRow).where(OfferFieldOriginRow.offer_id == rows.offer_id)
        )
        await session.execute(
            delete(OfferAiFieldEventRow).where(OfferAiFieldEventRow.offer_id == rows.offer_id)
        )


async def _remove_offer(rows: EnrichmentRows) -> None:
    await _remove_provenance(rows)
    async with rows.database.session_factory.begin() as session:
        await session.execute(
            delete(OfferAiEnrichmentItemRow).where(
                OfferAiEnrichmentItemRow.offer_id == rows.offer_id
            )
        )
        await session.execute(
            delete(OfferSourceRow).where(OfferSourceRow.offer_id == rows.offer_id)
        )
        await session.execute(delete(OfferRow).where(OfferRow.id == rows.offer_id))


async def test_unknown_offer_batch_and_state_update_fail_closed(
    enrichment_rows: EnrichmentRows,
) -> None:
    store = enrichment_rows.store
    assert await store.get_offer_snapshot(uuid4()) is None
    assert await store.get_batch(uuid4()) is None
    with pytest.raises(RuntimeError, match="enrichment batch disappeared after state update"):
        await store.set_batch_state(uuid4(), state=BatchState.RUNNING)
    assert (await store.get_batch(enrichment_rows.batch.id)) is not None


async def test_owner_lists_and_parser_gap_history_are_scoped(
    enrichment_rows: EnrichmentRows,
) -> None:
    rows = enrichment_rows
    other_owner = await _owner(rows.database)
    other_batch = await StartOfferEnrichmentBatch(
        rows.store,
        SQLAlchemyAdminAuditStore(rows.database.session_factory),
        FakeClock(moment=_NOW + timedelta(seconds=1)),
        _runtime(),
    )(owner_id=other_owner, request_id=uuid4(), offer_ids=(rows.offer_id,))
    other_item = await rows.store.next_item(other_batch.id)
    assert other_item is not None
    await rows.store.mark_item_processing(other_item, now=other_item.created_at)
    applied, event = await _complete(rows)
    assert applied is ItemOutcome.APPLIED
    proposal = replace(
        _event(rows, item=other_item),
        outcome=FieldEventOutcome.PROPOSED,
        applied_value=None,
        confidence="low",
        actor_id=str(other_owner),
    )
    await _complete(
        rows,
        item=other_item,
        values={},
        events=(proposal,),
        outcome=ItemOutcome.BELOW_THRESHOLD,
        state=ItemState.SKIPPED,
    )
    assert [batch.id for batch in await rows.store.list_owner_batches(rows.owner_id, limit=1)] == [
        rows.batch.id
    ]
    assert [item.id for item in await rows.store.list_batch_items(rows.batch.id)] == [rows.item.id]
    found = await rows.store.get_item(rows.item.id)
    assert found is not None
    assert found.state is ItemState.SUCCEEDED
    assert [record.id for record in await rows.store.list_batch_field_events(rows.batch.id)] == [
        event.id
    ]
    assert [
        record.id for record in await rows.store.list_owner_parser_gap_events(rows.owner_id)
    ] == [event.id]
    assert [record.id for record in await rows.store.list_owner_parser_gap_events(other_owner)] == [
        proposal.id
    ]


@pytest.mark.parametrize("target", ["offer", "item"])
async def test_complete_item_refuses_disappeared_rows(
    enrichment_rows: EnrichmentRows, target: str
) -> None:
    rows = enrichment_rows
    if target == "offer":
        await _remove_offer(rows)
    else:
        async with rows.database.session_factory.begin() as session:
            await session.execute(
                delete(OfferAiEnrichmentItemRow).where(OfferAiEnrichmentItemRow.id == rows.item.id)
            )
    outcome, _event_record = await _complete(rows)
    assert outcome is ItemOutcome.STALE
    batch = await rows.store.get_batch(rows.batch.id)
    assert batch is not None
    assert batch.processed_count == 0


@pytest.mark.parametrize("outcome", [None, ItemOutcome.NO_MISSING])
async def test_terminal_item_is_not_counted_or_processed_twice(
    enrichment_rows: EnrichmentRows,
    outcome: ItemOutcome | None,
) -> None:
    rows = enrichment_rows
    async with rows.database.session_factory.begin() as session:
        await session.execute(
            update(OfferAiEnrichmentItemRow)
            .where(OfferAiEnrichmentItemRow.id == rows.item.id)
            .values(state=ItemState.SKIPPED.value, outcome=outcome.value if outcome else None)
        )
    result, _event_record = await _complete(rows)
    assert result is (outcome or ItemOutcome.STALE)
    batch = await rows.store.get_batch(rows.batch.id)
    assert batch is not None
    assert batch.processed_count == 0
    assert await rows.store.list_batch_field_events(rows.batch.id) == ()


async def test_concurrent_canonical_edit_refuses_stale_proposal(
    enrichment_rows: EnrichmentRows,
) -> None:
    rows = enrichment_rows
    await _change_offer(rows, {"currency": "PLN"})
    outcome, _event_record = await _complete(rows)
    assert outcome is ItemOutcome.STALE
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    assert snapshot is not None
    assert snapshot.floor_label is None
    assert snapshot.currency == "PLN"
    assert await rows.store.list_active_ai_origins(rows.offer_id) == ()
    assert await rows.store.list_batch_field_events(rows.batch.id) == ()
    batch = await rows.store.get_batch(rows.batch.id)
    assert batch is not None
    assert (batch.processed_count, batch.failed_count) == (1, 1)


async def test_owner_fill_preserves_value_and_marks_no_missing(
    enrichment_rows: EnrichmentRows,
) -> None:
    rows = enrichment_rows
    await _change_offer(rows, {"floor_label": "9"})
    outcome, _event_record = await _complete(rows)
    assert outcome is ItemOutcome.NO_MISSING
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    assert snapshot is not None
    assert snapshot.floor_label == "9"
    batch = await rows.store.get_batch(rows.batch.id)
    assert batch is not None
    assert batch.skipped_count == 1
    assert await rows.store.list_batch_field_events(rows.batch.id) == ()


async def test_concurrent_ai_origin_is_protected_from_another_batch(
    enrichment_rows: EnrichmentRows,
) -> None:
    rows = enrichment_rows
    batch = await StartOfferEnrichmentBatch(
        rows.store,
        SQLAlchemyAdminAuditStore(rows.database.session_factory),
        FakeClock(moment=_NOW),
        _runtime(),
    )(owner_id=rows.owner_id, request_id=uuid4(), offer_ids=(rows.offer_id,))
    other_item = await rows.store.next_item(batch.id)
    assert other_item is not None
    await rows.store.mark_item_processing(other_item, now=other_item.created_at)
    assert (await _complete(rows, item=other_item))[0] is ItemOutcome.APPLIED
    outcome, _event_record = await _complete(rows)
    assert outcome is ItemOutcome.CONFLICT
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    assert snapshot is not None
    assert snapshot.floor_label == "4"
    events = await rows.store.list_batch_field_events(rows.batch.id)
    assert len(events) == 1
    assert events[0].outcome is FieldEventOutcome.SKIPPED
    assert events[0].reason == "protected_conflict"


@pytest.mark.parametrize("existing_upper", [None, 2])
async def test_range_conflict_cannot_write_invalid_canonical_bounds(
    enrichment_rows: EnrichmentRows,
    existing_upper: int | None,
) -> None:
    rows = enrichment_rows
    if existing_upper is not None:
        await _change_offer(rows, {"rooms_max": existing_upper})
    values: dict[str, object] = {"rooms_min": 3}
    if existing_upper is None:
        values["rooms_max"] = 1
    event = _event(rows, field="rooms_min", value=3)
    outcome, _event_record = await _complete(rows, values=values, events=(event,))
    assert outcome is ItemOutcome.CONFLICT
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    assert snapshot is not None
    assert snapshot.rooms_min is None
    assert snapshot.rooms_max == existing_upper


@pytest.mark.parametrize("missing_offer", [False, True])
async def test_revert_refuses_changed_or_removed_offer(
    enrichment_rows: EnrichmentRows, *, missing_offer: bool
) -> None:
    rows = enrichment_rows
    applied, event = await _complete(rows)
    assert applied is ItemOutcome.APPLIED
    if missing_offer:
        await _remove_offer(rows)
    else:
        await _change_offer(rows, {"floor_label": "9"})
    assert not await rows.store.revert_applied_event(event, actor_id=str(rows.owner_id), now=_NOW)
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    if missing_offer:
        assert snapshot is None
    else:
        assert snapshot is not None
        assert snapshot.floor_label == "9"


@pytest.mark.parametrize(
    ("field", "value", "cleared"),
    [
        ("market_type", "primary", "unknown"),
        ("parking_included_in_price", True, False),
        ("storage_included_in_price", True, False),
    ],
)
async def test_source_invalidation_restores_canonical_sentinel_values(
    enrichment_rows: EnrichmentRows,
    field: str,
    value: object,
    cleared: object,
) -> None:
    rows = enrichment_rows
    event = _event(rows, field=field, value=value)
    assert (await _complete(rows, values={field: value}, events=(event,)))[0] is ItemOutcome.APPLIED
    origin = (await rows.store.list_active_ai_origins(rows.offer_id))[0]
    outcome = await rows.store.invalidate_or_conflict_origin(
        origin,
        current_value=value,
        now=_NOW + timedelta(seconds=2),
        actor_id=str(rows.owner_id),
    )
    assert outcome is FieldEventOutcome.INVALIDATED
    snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
    assert snapshot is not None
    assert getattr(snapshot, field) == cleared


@pytest.mark.parametrize("mutation", ["owner-value", "removed-offer", "retired-event"])
async def test_origin_invalidation_preserves_owner_edits_and_stale_history_handles(
    enrichment_rows: EnrichmentRows,
    mutation: str,
) -> None:
    rows = enrichment_rows
    assert (await _complete(rows))[0] is ItemOutcome.APPLIED
    origin = (await rows.store.list_active_ai_origins(rows.offer_id))[0]
    if mutation == "owner-value":
        await _change_offer(rows, {"floor_label": "9"})
    elif mutation == "removed-offer":
        await _remove_offer(rows)
    else:
        await _remove_provenance(rows)
    result = await rows.store.invalidate_or_conflict_origin(
        origin,
        current_value="untrusted caller value",
        now=_NOW + timedelta(seconds=2),
        actor_id=str(rows.owner_id),
    )
    assert result is (
        FieldEventOutcome.INVALIDATED if mutation == "retired-event" else FieldEventOutcome.SKIPPED
    )
    if mutation == "owner-value":
        snapshot = await rows.store.get_offer_snapshot(rows.offer_id)
        assert snapshot is not None
        assert snapshot.floor_label == "9"
        assert await rows.store.list_active_ai_origins(rows.offer_id) == ()
        assert (await rows.store.list_batch_field_events(rows.batch.id))[
            -1
        ].reason == "source_edit_conflict"
    else:
        assert await rows.store.list_batch_field_events(rows.batch.id) == ()


@pytest.mark.parametrize("retired", [False, True])
async def test_parser_confirmation_converts_origin_without_resurrecting_retired_history(
    enrichment_rows: EnrichmentRows,
    *,
    retired: bool,
) -> None:
    rows = enrichment_rows
    assert (await _complete(rows))[0] is ItemOutcome.APPLIED
    origin = (await rows.store.list_active_ai_origins(rows.offer_id))[0]
    if retired:
        await _remove_provenance(rows)
    outcome = await rows.store.record_parser_comparison(
        origin,
        parser_value="4",
        parser_version="next-parser",
        now=_NOW + timedelta(seconds=2),
        actor_id=str(rows.owner_id),
    )
    assert outcome is FieldEventOutcome.PARSER_CONFIRMED
    assert await rows.store.list_active_ai_origins(rows.offer_id) == ()
    events = await rows.store.list_batch_field_events(rows.batch.id)
    if retired:
        assert events == ()
    else:
        assert events[-1].outcome is FieldEventOutcome.PARSER_CONFIRMED
