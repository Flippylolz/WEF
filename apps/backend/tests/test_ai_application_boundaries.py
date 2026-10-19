"""AI validation, residual-contact and durable retry boundaries."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAdminAuditStore,
    FakeChatCompletions,
    FakeClock,
    FakeIngestionAiParseStore,
    FakeOfferAiEnrichmentStore,
    FakeOwnerAiListingPersistence,
    FakeParseIssueStore,
    active_ai_runtime,
)
from tests.test_ingestion_ai_parse import _context, _payload, _pending_run
from tests.test_offer_enrichment import (
    _NOW,
    _field,
    _process,
    _revision,
    _runtime,
    _snapshot,
    _start,
)
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import (
    ProviderOutcome,
    ProviderRequestError,
    ReviewRunState,
)
from wef_backend.features.admin.application.ingestion_ai_parse import (
    ApplyIngestionAiParse,
    GenerateIngestionAiParse,
    IngestionAiApplyStatus,
    IngestionAiParseStatus,
    _canonical_field_value,
    parse_ingestion_ai_parse_payload,
)
from wef_backend.features.admin.application.offer_enrichment import (
    MAX_QUEUED_ITEMS,
    BatchState,
    ItemOutcome,
    ItemState,
    PauseOfferEnrichmentBatch,
    StartOfferEnrichmentBatch,
    canonicalize_offer_field,
    catalog_value_for_field,
    parse_offer_enrichment_payload,
    resolve_evidence_offsets,
)


@pytest.mark.parametrize("value", [True, "100", Decimal(100), None])
def test_catalog_prices_require_integer_major_units(value: object) -> None:
    """Booleans and coercible strings cannot bypass the canonical price boundary."""
    with pytest.raises(AdminDeniedError, match="expected an integer"):
        catalog_value_for_field("apartment_price_min", value)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("parking_included_in_price", "true", "boolean"),
        ("rooms_min", "two", "integer"),
    ],
)
def test_enrichment_rejects_malformed_scalar_values(
    field: str, value: object, message: str
) -> None:
    """Provider strings cannot masquerade as included flags or room counts."""
    with pytest.raises(AdminDeniedError, match=message):
        canonicalize_offer_field(field, value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"extra": "private"},
        {"field_name": "coordinates"},
        {"source_revision_id": 3},
        {"source_revision_id": "00000000-0000-0000-0000-000000000000"},
        {"evidence_fragment": 4},
        {"confidence": "certain"},
    ],
)
def test_enrichment_payload_rejects_untrusted_field_metadata(overrides: dict[str, object]) -> None:
    """Unknown fields, foreign revisions and malformed evidence fail closed."""
    revision_id = uuid4()
    with pytest.raises(ProviderRequestError) as caught:
        parse_offer_enrichment_payload(
            {"fields": [{**_field(revision_id), **overrides}]},
            allowed_revision_ids={str(revision_id)},
            missing={"floor_label"},
        )
    assert caught.value.outcome is ProviderOutcome.SCHEMA


def test_enrichment_payload_rejects_duplicate_fields() -> None:
    """Conflicting proposals for one field are never resolved by input order."""
    revision_id = uuid4()
    with pytest.raises(ProviderRequestError):
        parse_offer_enrichment_payload(
            {"fields": [_field(revision_id), _field(revision_id, value="5")]},
            allowed_revision_ids={str(revision_id)},
            missing={"floor_label"},
        )


def test_evidence_fallback_skips_contacts_and_refuses_contact_only_matches() -> None:
    """An ambiguous fragment may use a later safe match but never a contact span."""
    source = "+48111222333 then floor 111"
    start, end = resolve_evidence_offsets(source, "111", allow_ambiguous_first_match=True)
    assert source[start:end] == "111"
    assert start == source.rindex("111")
    with pytest.raises(AdminDeniedError, match="not found"):
        resolve_evidence_offsets(
            "+48111222333 and +48111222333",
            "111",
            allow_ambiguous_first_match=True,
        )
    with pytest.raises(AdminDeniedError, match="not found"):
        resolve_evidence_offsets("elsewhere", "floor\n\nfloor")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("parking_included_in_price", "yes", "boolean"),
        ("apartment_price_min", "bad", "decimal"),
        ("apartment_price_min", "0", "positive"),
        ("area_min_sqm", "0", "positive"),
        ("rooms_min", True, "integer"),
        ("rooms_min", "many", "integer"),
        ("rooms_min", 0, "positive"),
    ],
)
def test_listing_scalar_validation_fails_closed(field: str, value: object, message: str) -> None:
    """Invalid numeric and boolean values produce bounded application denials."""
    with pytest.raises(AdminDeniedError, match=message):
        _canonical_field_value(field, value)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("parking_included_in_price", False, False),
        ("storage_price_min", "42.5", "42.5"),
        ("area_min_sqm", "42.125", "42.12"),
        ("rooms_max", "3", 3),
        *(("currency", value, value) for value in ("PLN", "EUR", "USD", "GBP")),
    ],
)
def test_listing_scalar_validation_preserves_canonical_values(
    field: str,
    value: object,
    expected: object,
) -> None:
    """All supported ISO currencies and typed scalar forms stay accepted."""
    assert _canonical_field_value(field, value) == expected


@pytest.mark.parametrize("state", [BatchState.COMPLETED, BatchState.REVERTED, BatchState.FAILED])
async def test_terminal_enrichment_batches_ignore_pause_and_processing(state: BatchState) -> None:
    """Finished batches retain their state and never call the provider again."""
    owner = uuid4()
    snapshot = _snapshot()
    store = FakeOfferAiEnrichmentStore(snapshots={snapshot.id: snapshot})
    batch = await _start(store, owner_id=owner)
    store.batches[batch.id] = replace(batch, state=state)
    paused = await PauseOfferEnrichmentBatch(store, FakeAdminAuditStore())(
        owner_id=owner,
        batch_id=batch.id,
        request_id=uuid4(),
    )
    provider = FakeChatCompletions()
    assert paused == store.batches[batch.id]
    assert await _process(store, provider, owner_id=owner, batch_id=batch.id) is None
    assert not provider.calls


async def test_enrichment_queue_cap_refuses_another_batch() -> None:
    """The owner cap includes queued items across earlier batches."""
    snapshots = [_snapshot() for _ in range(MAX_QUEUED_ITEMS)]
    store = FakeOfferAiEnrichmentStore(snapshots={item.id: item for item in snapshots})
    owner = uuid4()
    start = StartOfferEnrichmentBatch(store, FakeAdminAuditStore(), FakeClock(_NOW), _runtime())
    await start(owner_id=owner, request_id=uuid4(), limit=MAX_QUEUED_ITEMS)
    with pytest.raises(AdminDeniedError, match="queued enrichment cap"):
        await start(owner_id=owner, request_id=uuid4())
    assert len(store.batches) == 1


async def test_enrichment_stale_selection_cannot_create_an_empty_batch() -> None:
    """An explicitly selected offer that disappeared is skipped before insertion."""
    store = FakeOfferAiEnrichmentStore()
    with pytest.raises(AdminDeniedError, match="no eligible offers"):
        await StartOfferEnrichmentBatch(
            store,
            FakeAdminAuditStore(),
            FakeClock(_NOW),
            _runtime(),
        )(owner_id=uuid4(), request_id=uuid4(), offer_ids=(uuid4(),))
    assert not store.batches


@pytest.mark.parametrize("failure", ["masking", "schema", "retry"])
async def test_enrichment_provider_boundaries(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsafe sources, malformed results and durable retries have distinct outcomes."""
    owner = uuid4()
    snapshot = _snapshot()
    revision = _revision(
        "callback 1234567890123 Warszawa 850 000 zł" if failure == "masking" else "Piętro 4",
    )
    store = FakeOfferAiEnrichmentStore(
        snapshots={snapshot.id: snapshot},
        sources={snapshot.id: (revision,)},
    )
    batch = await _start(store, owner_id=owner)
    provider = FakeChatCompletions(payload={"invalid": []})
    if failure == "retry":
        monkeypatch.setattr(provider, "durable_budget", True, raising=False)

        async def pending(**_kwargs: object) -> object:
            raise ProviderRequestError(
                ProviderOutcome.NETWORK, retry_at=_NOW + timedelta(minutes=1)
            )

        monkeypatch.setattr(provider, "complete", pending)
    outcome = await _process(store, provider, owner_id=owner, batch_id=batch.id)
    item = next(iter(store.items.values()))
    if failure == "masking":
        assert outcome is ItemOutcome.INVALID
        assert item.state is ItemState.FAILED
        assert not provider.calls
    elif failure == "schema":
        assert outcome is ItemOutcome.PROVIDER_FAILED
        assert item.state is ItemState.FAILED
        assert len(provider.calls) == 1
    else:
        assert outcome is ItemOutcome.NO_EVIDENCE
        assert item.state is ItemState.PROCESSING
        assert item.provider_called_at is None
    assert not store.events
    assert store.snapshots[snapshot.id] == snapshot


@pytest.mark.parametrize("failure", ["masking", "collision"])
async def test_listing_batch_generation_denies_unsafe_or_concurrent_rows(failure: str) -> None:
    """Masking denies before submission; insert races deny after provider success."""
    context = _context(
        text="callback 1234567890123" if failure == "masking" else "Mokotów 850 000 zł"
    )
    store = FakeIngestionAiParseStore(
        contexts={context.revision_id: context},
        force_insert_failure=failure == "collision",
    )
    provider = FakeChatCompletions(payload=_payload())
    outcomes = await GenerateIngestionAiParse(
        store,
        provider,
        FakeAdminAuditStore(),
        FakeClock(_NOW),
        active_ai_runtime(),
    ).generate_batch(
        owner_id=uuid4(),
        source_message_revision_ids=(context.revision_id,),
        request_id=uuid4(),
    )
    assert len(outcomes) == 1
    assert outcomes[0].status is IngestionAiParseStatus.DENIED
    assert outcomes[0].reason == ("masking_failed" if failure == "masking" else "in_flight")
    assert len(provider.calls) == (0 if failure == "masking" else 1)
    assert not store.runs


@pytest.mark.parametrize("applied_without_offer", [False, True])
async def test_listing_apply_checks_auto_evidence_and_legacy_idempotency(
    *,
    applied_without_offer: bool,
) -> None:
    """Auto apply needs calibrated evidence; legacy applied rows stay idempotent."""
    context = _context()
    owner = uuid4()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run = _pending_run(context=context, owner_id=owner, run_id=uuid4(), fields=fields)
    if applied_without_offer:
        run = replace(run, state=ReviewRunState.APPLIED, offer_id=None)
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context}, runs={run.id: run})
    persist = FakeOwnerAiListingPersistence()
    apply = ApplyIngestionAiParse(
        store,
        persist,
        FakeParseIssueStore(),
        FakeAdminAuditStore(),
        FakeClock(run.created_at),
        active_ai_runtime(),
    )
    if applied_without_offer:
        outcome = await apply(owner_id=owner, run_id=run.id, request_id=uuid4(), automatic=True)
        assert outcome.status is IngestionAiApplyStatus.APPLIED
        assert outcome.offer_id is None
    else:
        with pytest.raises(AdminDeniedError, match="not calibrated"):
            await apply(owner_id=owner, run_id=run.id, request_id=uuid4(), automatic=True)
    assert not persist.offers


@pytest.mark.parametrize("fragment", ["Warszawa", "zł"])
async def test_price_fill_requires_grounded_currency_proposal(fragment: str) -> None:
    """A price cannot borrow an ISO code from evidence that never mentions currency."""
    owner = uuid4()
    snapshot, revision = _snapshot(), _revision("Warszawa\nCena: 850 000 zł")
    store = FakeOfferAiEnrichmentStore(
        snapshots={snapshot.id: snapshot},
        sources={snapshot.id: (revision,)},
    )
    runtime = _runtime(apply=frozenset({"currency", "apartment_price_min"}))
    batch = await _start(store, owner_id=owner, runtime=runtime)
    provider = FakeChatCompletions(
        payload={
            "fields": [
                _field(
                    revision.revision_id,
                    name="apartment_price_min",
                    value=850000,
                    fragment="850 000 zł",
                ),
                _field(revision.revision_id, name="currency", value="PLN", fragment=fragment),
            ]
        }
    )
    outcome = await _process(store, provider, owner_id=owner, batch_id=batch.id, runtime=runtime)
    current = store.snapshots[snapshot.id]
    if fragment == "Warszawa":
        assert outcome is ItemOutcome.BELOW_THRESHOLD
        assert current.apartment_price_min is None
        assert current.currency is None
    else:
        assert outcome is ItemOutcome.APPLIED
        assert current.apartment_price_min == 850_000
        assert store.events[0].applied_value == 85_000_000
        assert current.currency == "PLN"


async def test_listing_automatic_apply_preserves_source_property_type() -> None:
    """Calibrated source text produces a typed listing through the real apply service."""
    context = _context(text="Продажа: квартира\nLocation: Warszawa, Testowa 1\nPrice: 780000 PLN")
    payload = _payload()
    payload["fields"] = [
        {
            "field_name": name,
            "proposed_value": value,
            "evidence_fragment": fragment,
            "confidence": "high",
        }
        for name, value, fragment in (
            ("location", "Warszawa, Testowa 1", "Warszawa, Testowa 1"),
            ("currency", "PLN", "PLN"),
            ("apartment_price_min", "780000", "780000 PLN"),
        )
    ]
    owner = uuid4()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(payload)
    run = _pending_run(context=context, owner_id=owner, run_id=uuid4(), fields=fields)
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context}, runs={run.id: run})
    persist = FakeOwnerAiListingPersistence()
    result = await ApplyIngestionAiParse(
        store,
        persist,
        FakeParseIssueStore(),
        FakeAdminAuditStore(),
        FakeClock(run.created_at),
        active_ai_runtime(),
    )(owner_id=owner, run_id=run.id, request_id=uuid4(), automatic=True)
    assert result.status is IngestionAiApplyStatus.APPLIED
    assert result.offer_id is not None
    listing = persist.offers[context.revision_id]
    assert listing.property_type is not None
    assert listing.property_type.value.value == "apartment"
