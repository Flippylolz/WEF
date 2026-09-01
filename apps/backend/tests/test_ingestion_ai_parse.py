"""Unit tests for owner ingestion AI parse interactors."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from tests.fakes import (
    FakeAdminAuditStore,
    FakeChatCompletions,
    FakeClock,
    FakeIngestionAiParseStore,
    FakeOwnerAiListingPersistence,
    FakeParseIssueStore,
    _inactive_ai_runtime,
    active_ai_runtime,
)
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    ProviderOutcome,
    ProviderRequestError,
    ReviewRunState,
)
from wef_backend.features.admin.application.ingestion_ai_parse import (
    AI_PARSE_PARSER_VERSION,
    ApplyIngestionAiParse,
    GenerateIngestionAiParse,
    GetIngestionAiParse,
    IngestionAiApplyStatus,
    IngestionAiParseRun,
    IngestionAiParseStatus,
    IngestionAiParseVerdict,
    RevisionParseContext,
    build_listing_candidate_from_ai,
    ingestion_ai_parse_json_schema,
    parse_ingestion_ai_parse_payload,
)
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain.parse_issue import (
    ParseIssueOutcome,
    SourceMessageParseIssue,
)


def _context(*, text: str = "Mokotów 2 pokoje 850 000 zł") -> RevisionParseContext:
    return RevisionParseContext(
        revision_id=uuid4(),
        message_id=uuid4(),
        external_message_id=29435,
        checksum="a" * 64,
        text_original=text,
    )


def _payload(*, fragment: str = "850 000 zł") -> dict[str, Any]:
    return {
        "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
        "fields": [
            {
                "field_name": "location",
                "proposed_value": "Mokotów",
                "evidence_fragment": "Mokotów",
                "confidence": "high",
            },
            {
                "field_name": "currency",
                "proposed_value": "PLN",
                "evidence_fragment": "zł",
                "confidence": "high",
            },
            {
                "field_name": "apartment_price_min",
                "proposed_value": "850000",
                "evidence_fragment": fragment,
                "confidence": "high",
            },
        ],
        "warnings": ["low_confidence"],
    }


def _pending_run(
    *,
    context: RevisionParseContext,
    owner_id: UUID,
    run_id: UUID,
    fields: tuple[dict[str, object], ...],
) -> IngestionAiParseRun:
    now = datetime(2026, 9, 1, 11, 0, tzinfo=UTC)
    return IngestionAiParseRun(
        id=run_id,
        owner_user_id=owner_id,
        source_message_id=context.message_id,
        source_message_revision_id=context.revision_id,
        external_message_id=context.external_message_id,
        state=ReviewRunState.PENDING,
        model=ALLOWED_GROQ_MODEL,
        prompt_version="ingestion-ai-parse-v1",
        schema_version="ingestion-ai-parse-schema-v1",
        input_fingerprint="b" * 64,
        source_checksum=context.checksum,
        proposed_fields=fields,
        verdict=IngestionAiParseVerdict.LISTING_PROPOSED.value,
        warnings=(),
        token_input=10,
        token_output=20,
        provider_latency_ms=100,
        provider_outcome=ProviderOutcome.SUCCEEDED,
        provider_request_id="req-1",
        created_at=now,
        expires_at=now + timedelta(hours=24),
        applied_at=None,
        offer_id=None,
    )


def test_parse_ingestion_ai_parse_payload_rejects_duplicate_fields() -> None:
    """Duplicate field names fail schema validation."""
    payload = _payload()
    payload["fields"] = [
        *payload["fields"],
        payload["fields"][0],
    ]
    with pytest.raises(ProviderRequestError):
        parse_ingestion_ai_parse_payload(payload)


def test_parse_ingestion_ai_parse_payload_rejects_invalid_warning() -> None:
    """Unknown warning codes fail schema validation."""
    payload = _payload()
    payload["warnings"] = ["unknown_warning"]
    with pytest.raises(ProviderRequestError):
        parse_ingestion_ai_parse_payload(payload)


def test_parse_ingestion_ai_parse_payload_rejects_unknown_fields() -> None:
    """Unknown top-level keys fail schema validation."""
    with pytest.raises(ProviderRequestError):
        parse_ingestion_ai_parse_payload({"verdict": "listing_proposed", "extra": []})


def test_ingestion_ai_parse_json_schema_lists_listing_fields() -> None:
    """Structured output schema exposes listing field names."""
    schema = cast("dict[str, Any]", ingestion_ai_parse_json_schema())
    field_names = cast(
        "list[str]",
        schema["properties"]["fields"]["items"]["properties"]["field_name"]["enum"],
    )
    assert "location" in field_names
    assert "apartment_price_min" in field_names


@pytest.mark.asyncio
async def test_get_ingestion_ai_parse_returns_run() -> None:
    """Get returns one stored run."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    run_id = uuid4()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=uuid4(),
        run_id=run_id,
        fields=fields,
    )
    run = await GetIngestionAiParse(store)(run_id=run_id)
    assert run is not None
    assert run.id == run_id


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_is_idempotent_for_applied_runs() -> None:
    """Re-applying an already applied run returns the stored offer."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    persistence = FakeOwnerAiListingPersistence()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    offer_id = uuid4()
    store.runs[run_id] = replace(
        _pending_run(
            context=context,
            owner_id=owner_id,
            run_id=run_id,
            fields=fields,
        ),
        state=ReviewRunState.APPLIED,
        offer_id=offer_id,
        applied_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    outcome = await ApplyIngestionAiParse(
        store,
        persistence,
        FakeParseIssueStore(),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=owner_id,
        run_id=run_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiApplyStatus.APPLIED
    assert outcome.offer_id == offer_id


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_stale_checksum() -> None:
    """Apply refuses when the source revision checksum changed."""
    context = _context()
    stale = replace(context, checksum="d" * 64)
    store = FakeIngestionAiParseStore(contexts={stale.revision_id: stale})
    persistence = FakeOwnerAiListingPersistence()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    with pytest.raises(AdminDeniedError, match="parse run is stale"):
        await ApplyIngestionAiParse(
            store,
            persistence,
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            active_ai_runtime(),
        )(
            owner_id=owner_id,
            run_id=run_id,
            request_id=uuid4(),
        )


def test_build_listing_candidate_from_ai_maps_required_fields() -> None:
    """Approved proposals become typed listing candidates."""
    context = _context()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.parser_version == AI_PARSE_PARSER_VERSION
    assert listing.location is not None
    assert listing.location.value == "Mokotów"
    assert listing.apartment_price is not None
    assert listing.apartment_price.value.currency == "PLN"


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_creates_pending_run() -> None:
    """Generate stores one pending run when AI curation is active."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    provider = FakeChatCompletions(payload=_payload())
    outcome = await GenerateIngestionAiParse(
        store,
        provider,
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.GENERATED
    assert outcome.run is not None
    assert outcome.run.state is ReviewRunState.PENDING


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_when_disabled() -> None:
    """Generate is fail-closed when AI curation is inactive."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    outcome = await GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        _inactive_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "disabled"


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_when_offer_exists() -> None:
    """Generate refuses messages that already have a primary offer."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    store.offers.add(context.message_id)
    outcome = await GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "offer_exists"


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_non_listing_verdict() -> None:
    """Apply refuses proposals that are not listings."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    persistence = FakeOwnerAiListingPersistence()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = replace(
        _pending_run(
            context=context,
            owner_id=owner_id,
            run_id=run_id,
            fields=fields,
        ),
        verdict=IngestionAiParseVerdict.NOT_A_LISTING.value,
    )
    with pytest.raises(AdminDeniedError, match="proposal is not a listing"):
        await ApplyIngestionAiParse(
            store,
            persistence,
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            active_ai_runtime(),
        )(
            owner_id=owner_id,
            run_id=run_id,
            request_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_persists_offer() -> None:
    """Apply converts a pending proposal into one persisted offer."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    persistence = FakeOwnerAiListingPersistence()
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    outcome = await ApplyIngestionAiParse(
        store,
        persistence,
        FakeParseIssueStore(),
        FakeAdminAuditStore(),
        FakeClock(now),
        active_ai_runtime(),
    )(
        owner_id=owner_id,
        run_id=run_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiApplyStatus.APPLIED
    assert context.revision_id in persistence.offers


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_links_parse_issue_offer() -> None:
    """Apply attaches the new offer id to parse issue rows for the source message."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    persistence = FakeOwnerAiListingPersistence()
    parse_issues = FakeParseIssueStore()
    parse_issues.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=context.message_id,
            source_message_revision_id=context.revision_id,
            external_message_id=context.external_message_id,
            ingest_run_id=None,
            parser_version="e2-v5",
            score=3,
            threshold=5,
            is_candidate=False,
            signals_json=(),
            warnings_json=(),
            issue_outcome=ParseIssueOutcome.PARSER_MISS,
            message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE.value,
            boundary_band="non_candidate_one_below_threshold",
            signal_combination="price_marker",
            text_excerpt_redacted="Mokotów listing without enough markers",
            offer_id=None,
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        ),
    )
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    outcome = await ApplyIngestionAiParse(
        store,
        persistence,
        parse_issues,
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=owner_id,
        run_id=run_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiApplyStatus.APPLIED
    assert outcome.offer_id is not None
    assert parse_issues.issues[0].offer_id == outcome.offer_id


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_unknown_revision() -> None:
    """Generate refuses unknown revisions."""
    outcome = await GenerateIngestionAiParse(
        FakeIngestionAiParseStore(),
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=uuid4(),
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "revision_not_found"


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_in_flight() -> None:
    """Generate refuses when a pending run already exists."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    owner_id = uuid4()
    run_id = uuid4()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    outcome = await GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "in_flight"


def test_build_listing_candidate_from_ai_maps_optional_fields() -> None:
    """Optional proposal fields map onto typed listing values."""
    text = "Osiedle Alfa Mokotów 3 pokoje 60 m2 850 000 zł parking w cenie"
    context = _context(text=text)
    payload = {
        "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
        "fields": [
            {
                "field_name": "development_name",
                "proposed_value": "Osiedle Alfa",
                "evidence_fragment": "Osiedle Alfa",
                "confidence": "high",
            },
            {
                "field_name": "location",
                "proposed_value": "Mokotów",
                "evidence_fragment": "Mokotów",
                "confidence": "high",
            },
            {
                "field_name": "district",
                "proposed_value": "Mokotów",
                "evidence_fragment": "Mokotów",
                "confidence": "medium",
            },
            {
                "field_name": "market_type",
                "proposed_value": "primary",
                "evidence_fragment": "Osiedle Alfa",
                "confidence": "medium",
            },
            {
                "field_name": "currency",
                "proposed_value": "PLN",
                "evidence_fragment": "zł",
                "confidence": "high",
            },
            {
                "field_name": "apartment_price_min",
                "proposed_value": "850000",
                "evidence_fragment": "850 000 zł",
                "confidence": "high",
            },
            {
                "field_name": "area_min_sqm",
                "proposed_value": "60",
                "evidence_fragment": "60 m2",
                "confidence": "high",
            },
            {
                "field_name": "rooms_min",
                "proposed_value": "3",
                "evidence_fragment": "3 pokoje",
                "confidence": "high",
            },
            {
                "field_name": "parking_included_in_price",
                "proposed_value": True,
                "evidence_fragment": "parking w cenie",
                "confidence": "high",
            },
        ],
        "warnings": [],
    }
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(payload)
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.development_name is not None
    assert listing.district is not None
    assert listing.area_sqm is not None
    assert listing.rooms is not None
    assert listing.parking_included_in_price is not None


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_records_provider_failure() -> None:
    """Provider failures persist a failed run."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    provider = FakeChatCompletions(error=ProviderOutcome.SCHEMA)
    outcome = await GenerateIngestionAiParse(
        store,
        provider,
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.FAILED
    assert outcome.run is not None
    assert outcome.run.state is ReviewRunState.FAILED


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_daily_limit() -> None:
    """Generate refuses when the owner daily budget is exhausted."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    owner_id = uuid4()
    runtime = active_ai_runtime()
    for _ in range(runtime.daily_limit):
        run_id = uuid4()
        store.runs[run_id] = replace(
            _pending_run(
                context=context,
                owner_id=owner_id,
                run_id=run_id,
                fields=parse_ingestion_ai_parse_payload(_payload())[1],
            ),
            state=ReviewRunState.FAILED,
        )
    outcome = await GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        runtime,
    )(
        owner_id=owner_id,
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "daily_limit"


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_unknown_run() -> None:
    """Apply refuses unknown run ids."""
    with pytest.raises(AdminDeniedError, match="parse run not found"):
        await ApplyIngestionAiParse(
            FakeIngestionAiParseStore(),
            FakeOwnerAiListingPersistence(),
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            active_ai_runtime(),
        )(
            owner_id=uuid4(),
            run_id=uuid4(),
            request_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_expired_run() -> None:
    """Apply refuses expired pending runs."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = replace(
        _pending_run(
            context=context,
            owner_id=owner_id,
            run_id=run_id,
            fields=fields,
        ),
        expires_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
    )
    with pytest.raises(AdminDeniedError, match="expired or not pending"):
        await ApplyIngestionAiParse(
            store,
            FakeOwnerAiListingPersistence(),
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            active_ai_runtime(),
        )(
            owner_id=owner_id,
            run_id=run_id,
            request_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_masking_failure() -> None:
    """Residual contact-like material fails closed before the provider."""
    context = _context(text="callback 1234567890123 Warszawa 850 000 zł")
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    provider = FakeChatCompletions(payload=_payload())
    outcome = await GenerateIngestionAiParse(
        store,
        provider,
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "masking_failed"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_ingestion_ai_parse_denies_insert_collision() -> None:
    """A concurrent pending run denies the second insert after provider success."""
    context = _context()
    store = FakeIngestionAiParseStore(
        contexts={context.revision_id: context},
        force_insert_failure=True,
    )
    outcome = await GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=uuid4(),
        source_message_revision_id=context.revision_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiParseStatus.DENIED
    assert outcome.reason == "in_flight"


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_when_disabled() -> None:
    """Apply is fail-closed when AI curation is inactive."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    with pytest.raises(AdminDeniedError, match="AI ingestion parse is disabled"):
        await ApplyIngestionAiParse(
            store,
            FakeOwnerAiListingPersistence(),
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            _inactive_ai_runtime(),
        )(
            owner_id=owner_id,
            run_id=run_id,
            request_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_denies_when_offer_exists() -> None:
    """Apply refuses when a primary offer appeared after generate."""
    context = _context()
    store = FakeIngestionAiParseStore(contexts={context.revision_id: context})
    store.offers.add(context.message_id)
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    with pytest.raises(AdminDeniedError, match="offer already exists"):
        await ApplyIngestionAiParse(
            store,
            FakeOwnerAiListingPersistence(),
            FakeParseIssueStore(),
            FakeAdminAuditStore(),
            FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
            active_ai_runtime(),
        )(
            owner_id=owner_id,
            run_id=run_id,
            request_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_apply_ingestion_ai_parse_handles_mark_collision() -> None:
    """Apply surfaces a bounded outcome when the run cannot be marked applied."""
    context = _context()
    store = FakeIngestionAiParseStore(
        contexts={context.revision_id: context},
        mark_applied_status=IngestionAiApplyStatus.COLLISION,
    )
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run_id = uuid4()
    owner_id = uuid4()
    store.runs[run_id] = _pending_run(
        context=context,
        owner_id=owner_id,
        run_id=run_id,
        fields=fields,
    )
    outcome = await ApplyIngestionAiParse(
        store,
        FakeOwnerAiListingPersistence(),
        FakeParseIssueStore(),
        FakeAdminAuditStore(),
        FakeClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
        active_ai_runtime(),
    )(
        owner_id=owner_id,
        run_id=run_id,
        request_id=uuid4(),
    )
    assert outcome.status is IngestionAiApplyStatus.COLLISION
    assert outcome.offer_id is None


def test_build_listing_candidate_from_ai_maps_price_and_label_fields() -> None:
    """Optional price and label fields map onto typed listing values."""
    text = "Mokotów piętro 5 oddanie Q4 850 000 zł parking 50 000 zł komórka 10 000 zł"
    context = _context(text=text)
    payload = {
        "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
        "fields": [
            {
                "field_name": "location",
                "proposed_value": "Mokotów",
                "evidence_fragment": "Mokotów",
                "confidence": "high",
            },
            {
                "field_name": "currency",
                "proposed_value": "PLN",
                "evidence_fragment": "zł",
                "confidence": "high",
            },
            {
                "field_name": "apartment_price_min",
                "proposed_value": "850000",
                "evidence_fragment": "850 000 zł",
                "confidence": "high",
            },
            {
                "field_name": "parking_price_min",
                "proposed_value": "50000",
                "evidence_fragment": "parking 50 000 zł",
                "confidence": "high",
            },
            {
                "field_name": "storage_price_min",
                "proposed_value": "10000",
                "evidence_fragment": "komórka 10 000 zł",
                "confidence": "high",
            },
            {
                "field_name": "floor_label",
                "proposed_value": "5",
                "evidence_fragment": "piętro 5",
                "confidence": "high",
            },
            {
                "field_name": "delivery_label",
                "proposed_value": "Q4",
                "evidence_fragment": "oddanie Q4",
                "confidence": "medium",
            },
        ],
        "warnings": [],
    }
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(payload)
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.parking_price is not None
    assert listing.storage_price is not None
    assert listing.floor is not None
    assert listing.delivery is not None


def test_build_listing_candidate_from_ai_accepts_zl_currency_symbol() -> None:
    """Groq may propose zł symbols; apply normalizes them to PLN."""
    context = _context()
    fields = _listing_fields(currency="zł")
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.apartment_price is not None
    assert listing.apartment_price.value.currency == "PLN"


def test_build_listing_candidate_from_ai_accepts_sale_market_alias() -> None:
    """Groq may propose sale labels; apply normalizes them to secondary."""
    context = _context(text="Mokotów 2 pokoje sale 850 000 zł")
    fields = _listing_fields(market_type="sale")
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.market_type is not None
    assert listing.market_type.value == "secondary"


def test_build_listing_candidate_from_ai_accepts_residential_market_alias() -> None:
    """Groq may propose residential labels; apply normalizes them to unknown."""
    context = _context(text="Mokotów residential 2 pokoje 850 000 zł")
    fields = _listing_fields(market_type="residential")
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)
    assert listing.market_type is not None
    assert listing.market_type.value == "unknown"


def test_build_listing_candidate_from_ai_requires_core_fields() -> None:
    """Apply rejects proposals missing required listing fields."""
    context = _context()
    with pytest.raises(AdminDeniedError, match="proposal missing required fields"):
        build_listing_candidate_from_ai(context=context, proposed_fields=())


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-dict",
        {"verdict": "unknown", "fields": [], "warnings": []},
        {
            "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
            "fields": "bad",
            "warnings": [],
        },
        {
            "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
            "fields": ["not-a-dict"],
            "warnings": [],
        },
        {
            "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
            "fields": [{"field_name": "location", "extra": True}],
            "warnings": [],
        },
        {
            "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
            "fields": [
                {
                    "field_name": "unknown_field",
                    "proposed_value": "x",
                    "evidence_fragment": "x",
                    "confidence": "high",
                },
            ],
            "warnings": [],
        },
        {
            "verdict": IngestionAiParseVerdict.LISTING_PROPOSED.value,
            "fields": [
                {
                    "field_name": "location",
                    "proposed_value": "Mokotów",
                    "evidence_fragment": 123,
                    "confidence": "high",
                },
            ],
            "warnings": [],
        },
    ],
)
def test_parse_ingestion_ai_parse_payload_rejects_invalid_shapes(payload: object) -> None:
    """Malformed provider payloads fail schema validation."""
    with pytest.raises(ProviderRequestError):
        parse_ingestion_ai_parse_payload(payload)


def _listing_fields(**overrides: object) -> tuple[dict[str, object], ...]:
    payload = _payload()
    fields = payload["fields"]
    assert isinstance(fields, list)
    for field in fields:
        assert isinstance(field, dict)
        name = str(field["field_name"])
        if name in overrides:
            field["proposed_value"] = overrides.pop(name)
    fields.extend(
        {
            "field_name": name,
            "proposed_value": value,
            "evidence_fragment": str(value),
            "confidence": "high",
        }
        for name, value in overrides.items()
    )
    return parse_ingestion_ai_parse_payload(payload)[1]


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"currency": "JPY"}, "unsupported currency"),
        ({"market_type": "invalid"}, "unsupported market type"),
        ({"location": ""}, "label is empty or too long"),
        ({"apartment_price_max": "1"}, "invalid apartment price range"),
        ({"parking_price_max": "1", "parking_price_min": "50000"}, "invalid money range"),
        ({"area_max_sqm": "1", "area_min_sqm": "50"}, "invalid decimal range"),
        ({"rooms_max": "1", "rooms_min": "3"}, "invalid integer range"),
    ],
)
def test_build_listing_candidate_from_ai_rejects_invalid_values(
    overrides: dict[str, object],
    match: str,
) -> None:
    """Canonical field coercion rejects unsupported AI proposal values."""
    context = _context()
    fields = _listing_fields(**overrides)
    with pytest.raises(AdminDeniedError, match=match):
        build_listing_candidate_from_ai(context=context, proposed_fields=fields)
