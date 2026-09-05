"""Admin HTTP tests for ingestion parse issue reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeChatCompletions,
    FakeIngestionAiParseStore,
    FakeOwnerAiListingPersistence,
    FakeParseIssueStore,
    active_ai_runtime,
)
from tests.test_admin_api import _csrf_from_html, _owner_session, admin_client
from wef_backend.features.admin.application.ai_review import ProviderOutcome, ReviewRunState
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyStatus,
    IngestionAiParseRun,
    IngestionAiParseVerdict,
    RevisionParseContext,
)
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain.parse_issue import (
    ParseIssueOutcome,
    SourceMessageParseIssue,
)


@pytest.mark.asyncio
async def test_ingestion_issues_export_is_redacted() -> None:
    """CSV export includes score metadata but no raw phone numbers."""
    store = FakeParseIssueStore()
    store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=uuid4(),
            external_message_id=29435,
            ingest_run_id=uuid4(),
            parser_version="e2-v5",
            score=3,
            threshold=5,
            is_candidate=False,
            signals_json=(
                {
                    "reason": "price_marker",
                    "weight": 3,
                    "source_start": 0,
                    "source_end": 4,
                },
            ),
            warnings_json=(),
            issue_outcome=ParseIssueOutcome.PARSER_MISS,
            message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE.value,
            boundary_band="non_candidate_one_below_threshold",
            signal_combination="price_marker",
            text_excerpt_redacted="Warsaw listing without enough markers",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    async with admin_client(parse_issue_store=store) as (client, _identity):
        await _owner_session(client, _identity)
        home = await client.get("/admin/ingestion-issues")
        assert home.status_code == 200
        assert "29435" in home.text
        assert "unclassified (open)" in home.text
        csv_response = await client.get("/admin/ingestion-issues/export.csv")
        assert csv_response.status_code == 200
        body = csv_response.text
        assert "29435" in body
        assert "non_candidate_one_below_threshold" in body
        assert "+48" not in body
        json_response = await client.get("/admin/ingestion-issues/export.json")
        assert json_response.status_code == 200
        assert "Warsaw listing" in json_response.text


@pytest.mark.asyncio
async def test_ingestion_issues_hides_ai_link_when_disabled() -> None:
    """The issues table omits AI review links when curation is disabled."""
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=uuid4(),
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    async with admin_client(parse_issue_store=parse_store) as (client, identity):
        await _owner_session(client, identity)
        home = await client.get("/admin/ingestion-issues")
        assert home.status_code == 200
        assert "Review</a>" not in home.text


@pytest.mark.asyncio
async def test_anonymous_cannot_reach_ingestion_ai_routes() -> None:
    """Unauthenticated browsers never reach generate or apply."""
    async with admin_client() as (client, _identity):
        generate = await client.post(
            "/admin/ingestion-issues/ai-generate",
            data={"revision_id": str(uuid4())},
            follow_redirects=False,
        )
        apply = await client.post(
            "/admin/ingestion-issues/ai-apply",
            data={"run_id": str(uuid4())},
            follow_redirects=False,
        )
        assert generate.status_code in {302, 303, 401, 403}
        assert apply.status_code in {302, 303, 401, 403}


@pytest.mark.asyncio
async def test_ingestion_issue_review_redirects_on_invalid_ids() -> None:
    """Invalid revision or run ids redirect back to the issues list."""
    async with admin_client(runtime=active_ai_runtime()) as (client, identity):
        await _owner_session(client, identity)
        bad_revision = await client.get(
            "/admin/ingestion-issues/review?revision_id=not-a-uuid",
            follow_redirects=False,
        )
        bad_run = await client.get(
            "/admin/ingestion-issues/review?run_id=not-a-uuid",
            follow_redirects=False,
        )
        assert bad_revision.status_code == 303
        assert bad_run.status_code == 303


@pytest.mark.asyncio
async def test_ingestion_issue_review_shows_error_banner() -> None:
    """Review page renders query-string error messages."""
    revision_id = uuid4()
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=revision_id,
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    async with admin_client(
        parse_issue_store=parse_store,
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        page = await client.get(
            f"/admin/ingestion-issues/review?revision_id={revision_id}&error=daily_limit",
        )
        assert page.status_code == 200
        assert "daily_limit" in page.text


@pytest.mark.asyncio
async def test_ingestion_issue_review_shows_generate_action_when_enabled() -> None:
    """Review page exposes AI generate when curation is enabled and no offer exists."""
    revision_id = uuid4()
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=revision_id,
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    async with admin_client(
        parse_issue_store=parse_store,
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        page = await client.get(f"/admin/ingestion-issues/review?revision_id={revision_id}")
        assert page.status_code == 200
        assert "Generate AI listing proposal" in page.text
        assert "29435" in page.text


@pytest.mark.asyncio
async def test_ingestion_issue_generate_redirects_to_review() -> None:
    """Generate from the review page stores a pending proposal."""
    revision_id = uuid4()
    message_id = uuid4()
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=message_id,
            source_message_revision_id=revision_id,
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    ai_store = FakeIngestionAiParseStore(
        contexts={
            revision_id: RevisionParseContext(
                revision_id=revision_id,
                message_id=message_id,
                external_message_id=29435,
                checksum="a" * 64,
                text_original="Mokotów 850 000 zł",
            ),
        },
    )
    provider = FakeChatCompletions(
        payload={
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
            ],
            "warnings": [],
        },
    )
    async with admin_client(
        parse_issue_store=parse_store,
        ingestion_ai_parse_store=ai_store,
        provider=provider,
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        review = await client.get(f"/admin/ingestion-issues/review?revision_id={revision_id}")
        token = _csrf_from_html(review.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-generate",
            data={"revision_id": str(revision_id), "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "run_id=" in response.headers["location"]
        follow = await client.get(response.headers["location"])
        assert follow.status_code == 200
        assert "listing_proposed" in follow.text


@pytest.mark.asyncio
async def test_ingestion_issue_apply_redirects_after_success() -> None:
    """Apply from the review page creates one offer through the fake persistence port."""
    revision_id = uuid4()
    message_id = uuid4()
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=message_id,
            source_message_revision_id=revision_id,
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    ai_store = FakeIngestionAiParseStore(
        contexts={
            revision_id: RevisionParseContext(
                revision_id=revision_id,
                message_id=message_id,
                external_message_id=29435,
                checksum="a" * 64,
                text_original="Mokotów 850 000 zł",
            ),
        },
    )
    run_id = uuid4()
    async with admin_client(
        parse_issue_store=parse_store,
        ingestion_ai_parse_store=ai_store,
        owner_ai_listing_persistence=FakeOwnerAiListingPersistence(),
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        accounts = await identity.list_accounts(limit=1)
        owner_id = accounts[0].id
        ai_store.runs[run_id] = IngestionAiParseRun(
            id=run_id,
            owner_user_id=owner_id,
            source_message_id=message_id,
            source_message_revision_id=revision_id,
            external_message_id=29435,
            state=ReviewRunState.PENDING,
            model="openai/gpt-oss-20b",
            prompt_version="ingestion-ai-parse-v1",
            schema_version="ingestion-ai-parse-schema-v1",
            input_fingerprint="b" * 64,
            source_checksum="a" * 64,
            proposed_fields=(
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
            ),
            verdict=IngestionAiParseVerdict.LISTING_PROPOSED.value,
            warnings=(),
            token_input=1,
            token_output=1,
            provider_latency_ms=1,
            provider_outcome=ProviderOutcome.SUCCEEDED,
            provider_request_id="req",
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            expires_at=datetime(2026, 9, 2, tzinfo=UTC),
            applied_at=None,
            offer_id=None,
        )
        review = await client.get(
            f"/admin/ingestion-issues/review?revision_id={revision_id}&run_id={run_id}",
        )
        token = _csrf_from_html(review.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-apply",
            data={"run_id": str(run_id), "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        follow = await client.get(response.headers["location"])
        assert follow.status_code == 200
        assert "Offer created" in follow.text


@pytest.mark.asyncio
async def test_ingestion_issue_review_redirects_when_revision_missing() -> None:
    """Unknown revision ids redirect back to the issues list."""
    async with admin_client(runtime=active_ai_runtime()) as (client, identity):
        await _owner_session(client, identity)
        response = await client.get(
            f"/admin/ingestion-issues/review?revision_id={uuid4()}",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/ingestion-issues"


@pytest.mark.asyncio
async def test_ingestion_issue_review_redirects_when_run_missing() -> None:
    """Unknown run ids redirect back to the issues list."""
    async with admin_client(runtime=active_ai_runtime()) as (client, identity):
        await _owner_session(client, identity)
        response = await client.get(
            f"/admin/ingestion-issues/review?run_id={uuid4()}",
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.asyncio
async def test_ingestion_issue_generate_redirects_on_invalid_revision() -> None:
    """Invalid revision ids on generate redirect back to the issues list."""
    async with admin_client(runtime=active_ai_runtime()) as (client, identity):
        await _owner_session(client, identity)
        users = await client.get("/admin/users")
        token = _csrf_from_html(users.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-generate",
            data={"revision_id": "not-a-uuid", "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.asyncio
async def test_ingestion_issue_generate_redirects_with_denied_reason() -> None:
    """Generate denials surface on the review page."""
    revision_id = uuid4()
    parse_store = FakeParseIssueStore()
    parse_store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=revision_id,
            external_message_id=29435,
            ingest_run_id=uuid4(),
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
            text_excerpt_redacted="Near-threshold miss",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    ai_store = FakeIngestionAiParseStore(
        contexts={
            revision_id: RevisionParseContext(
                revision_id=revision_id,
                message_id=uuid4(),
                external_message_id=29435,
                checksum="a" * 64,
                text_original="Mokotów 850 000 zł",
            ),
        },
    )
    ai_store.offers.add(ai_store.contexts[revision_id].message_id)
    async with admin_client(
        parse_issue_store=parse_store,
        ingestion_ai_parse_store=ai_store,
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        review = await client.get(f"/admin/ingestion-issues/review?revision_id={revision_id}")
        token = _csrf_from_html(review.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-generate",
            data={"revision_id": str(revision_id), "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        follow = await client.get(response.headers["location"])
        assert "already has an offer" in follow.text


@pytest.mark.asyncio
async def test_ingestion_issue_apply_redirects_on_invalid_run() -> None:
    """Invalid run ids on apply redirect back to the issues list."""
    async with admin_client(runtime=active_ai_runtime()) as (client, identity):
        await _owner_session(client, identity)
        users = await client.get("/admin/users")
        token = _csrf_from_html(users.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-apply",
            data={"run_id": "not-a-uuid", "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.asyncio
async def test_ingestion_issue_apply_redirects_on_denied_error() -> None:
    """Apply denials surface on the review page."""
    run_id = uuid4()
    revision_id = uuid4()
    ai_store = FakeIngestionAiParseStore()
    ai_store.runs[run_id] = IngestionAiParseRun(
        id=run_id,
        owner_user_id=uuid4(),
        source_message_id=uuid4(),
        source_message_revision_id=revision_id,
        external_message_id=29435,
        state=ReviewRunState.PENDING,
        model="openai/gpt-oss-20b",
        prompt_version="ingestion-ai-parse-v1",
        schema_version="ingestion-ai-parse-schema-v1",
        input_fingerprint="b" * 64,
        source_checksum="a" * 64,
        proposed_fields=(),
        verdict=IngestionAiParseVerdict.LISTING_PROPOSED.value,
        warnings=(),
        token_input=1,
        token_output=1,
        provider_latency_ms=1,
        provider_outcome=ProviderOutcome.SUCCEEDED,
        provider_request_id="req",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        expires_at=datetime(2026, 9, 2, tzinfo=UTC),
        applied_at=None,
        offer_id=None,
    )
    async with admin_client(
        ingestion_ai_parse_store=ai_store,
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        users = await client.get("/admin/users")
        token = _csrf_from_html(users.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-apply",
            data={"run_id": str(run_id), "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]


@pytest.mark.asyncio
async def test_ingestion_issue_apply_redirects_on_collision() -> None:
    """Non-applied apply outcomes surface on the review page."""
    revision_id = uuid4()
    message_id = uuid4()
    ai_store = FakeIngestionAiParseStore(
        contexts={
            revision_id: RevisionParseContext(
                revision_id=revision_id,
                message_id=message_id,
                external_message_id=29435,
                checksum="a" * 64,
                text_original="Mokotów 850 000 zł",
            ),
        },
        mark_applied_status=IngestionAiApplyStatus.COLLISION,
    )
    run_id = uuid4()
    async with admin_client(
        ingestion_ai_parse_store=ai_store,
        owner_ai_listing_persistence=FakeOwnerAiListingPersistence(),
        runtime=active_ai_runtime(),
    ) as (client, identity):
        await _owner_session(client, identity)
        accounts = await identity.list_accounts(limit=1)
        owner_id = accounts[0].id
        ai_store.runs[run_id] = IngestionAiParseRun(
            id=run_id,
            owner_user_id=owner_id,
            source_message_id=message_id,
            source_message_revision_id=revision_id,
            external_message_id=29435,
            state=ReviewRunState.PENDING,
            model="openai/gpt-oss-20b",
            prompt_version="ingestion-ai-parse-v1",
            schema_version="ingestion-ai-parse-schema-v1",
            input_fingerprint="b" * 64,
            source_checksum="a" * 64,
            proposed_fields=(
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
            ),
            verdict=IngestionAiParseVerdict.LISTING_PROPOSED.value,
            warnings=(),
            token_input=1,
            token_output=1,
            provider_latency_ms=1,
            provider_outcome=ProviderOutcome.SUCCEEDED,
            provider_request_id="req",
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            expires_at=datetime(2026, 9, 2, tzinfo=UTC),
            applied_at=None,
            offer_id=None,
        )
        users = await client.get("/admin/users")
        token = _csrf_from_html(users.text)
        response = await client.post(
            "/admin/ingestion-issues/ai-apply",
            data={"run_id": str(run_id), "csrftoken": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "collision" in response.headers["location"]
