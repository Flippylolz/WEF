"""PostGIS generate/apply coverage for ingestion AI parse persistence."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import select, text

from tests.fakes import FakeChatCompletions, FakeClock
from tests.test_ingestion_ai_parse import (
    _context,
    _payload,
    build_listing_candidate_from_ai,
    parse_ingestion_ai_parse_payload,
)
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    AiCurationRuntime,
    ProviderOutcome,
    ReviewRunState,
)
from wef_backend.features.admin.application.ingestion_ai_parse import (
    ApplyIngestionAiParse,
    GenerateIngestionAiParse,
    IngestionAiApplyStatus,
    IngestionAiParseRun,
    IngestionAiParseStatus,
    IngestionAiParseVerdict,
)
from wef_backend.features.admin.infrastructure.ingestion_ai_parse_store import (
    SQLAlchemyIngestionAiParseStore,
)
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.features.ingestion.application.persistence import PersistenceBatchError
from wef_backend.features.ingestion.infrastructure.models import OfferSourceRow
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

_NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
_SOURCE_TEXT = "Mokotów 2 pokoje 850 000 zł"


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))


def _runtime() -> AiCurationRuntime:
    return AiCurationRuntime(
        enabled=True,
        zdr_verified=True,
        model=ALLOWED_GROQ_MODEL,
        api_key_present=True,
    )


async def _prepare() -> DatabaseResources:
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    async with database.session_factory() as session:
        for statement in (
            "DELETE FROM ingestion_ai_parse_runs",
            "DELETE FROM place_ai_review_runs",
            "DELETE FROM offer_ai_field_events",
            "DELETE FROM offer_ai_enrichment_items",
            "DELETE FROM offer_ai_enrichment_batches",
            "DELETE FROM source_message_parse_issues",
            "DELETE FROM offer_sources",
            "DELETE FROM offers",
            "DELETE FROM source_messages",
            "DELETE FROM source_message_revisions",
            "DELETE FROM source_channels",
            "DELETE FROM admin_audit_events",
            "DELETE FROM users",
        ):
            await session.execute(text(statement))
        await session.commit()
    return database


async def _seed_owner(database: DatabaseResources) -> UUID:
    owner_id = uuid4()
    async with database.session_factory() as session, session.begin():
        session.add(
            UserRow(
                id=owner_id,
                username_normalized="owner",
                username_display="owner",
                hashed_password="fakehash:longenough123",
                role=UserRole.OWNER.value,
                must_change_password=False,
                is_active=True,
                created_at=_NOW,
            ),
        )
    return owner_id


async def _seed_parse_miss(database: DatabaseResources) -> tuple[UUID, UUID]:
    channel_id, message_id, revision_id = uuid4(), uuid4(), uuid4()
    checksum = "c" * 64
    async with database.session_factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO source_channels "
                "(id, platform, external_id, display_name) "
                "VALUES (:id, 'telegram', :external, 'Parse miss source')"
            ),
            {"id": channel_id, "external": str(channel_id)},
        )
        await session.execute(
            text(
                "INSERT INTO source_messages "
                "(id, source_channel_id, external_message_id, current_revision_id, "
                "message_type, published_at, text_original, entities_json, "
                "raw_payload_json, raw_checksum, ingested_at) "
                "VALUES (:id, :channel, 29435, :revision, 'message', :now, :text, "
                "'[]', '{}', :checksum, :now)"
            ),
            {
                "id": message_id,
                "channel": channel_id,
                "revision": revision_id,
                "now": _NOW,
                "text": _SOURCE_TEXT,
                "checksum": checksum,
            },
        )
        await session.execute(
            text(
                "INSERT INTO source_message_revisions "
                "(id, source_message_id, revision_number, captured_at, message_type, "
                "published_at, text_original, entities_json, raw_payload_json, "
                "raw_checksum) "
                "VALUES (:id, :message, 1, :now, 'message', :now, :text, '[]', "
                "'{}', :checksum)"
            ),
            {
                "id": revision_id,
                "message": message_id,
                "now": _NOW,
                "text": _SOURCE_TEXT,
                "checksum": checksum,
            },
        )
    return message_id, revision_id


@pytest.mark.asyncio
async def test_ingestion_ai_parse_generate_and_apply_creates_offer() -> None:
    """Generate and apply persist one offer from a parse miss revision."""
    database = await _prepare()
    owner_id = await _seed_owner(database)
    message_id, revision_id = await _seed_parse_miss(database)
    store = SQLAlchemyIngestionAiParseStore(database.session_factory)
    persistence = SQLAlchemyIngestionPersistence(database.session_factory)
    audits = SQLAlchemyAdminAuditStore(database.session_factory)
    clock = FakeClock(_NOW)
    generate = GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        audits,
        clock,
        _runtime(),
    )
    apply = ApplyIngestionAiParse(store, persistence, audits, clock, _runtime())
    generated = await generate(
        owner_id=owner_id,
        source_message_revision_id=revision_id,
        request_id=uuid4(),
    )
    assert generated.status is IngestionAiParseStatus.GENERATED
    assert generated.run is not None
    assert await store.has_primary_offer(message_id) is False
    pending = await store.get_pending_run(revision_id)
    assert pending is not None
    assert pending.id == generated.run.id
    applied = await apply(
        owner_id=owner_id,
        run_id=generated.run.id,
        request_id=uuid4(),
    )
    assert applied.status is IngestionAiApplyStatus.APPLIED
    assert await store.has_primary_offer(message_id) is True
    assert await store.get_pending_run(revision_id) is None
    async with database.session_factory() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == EXPECTED_DATABASE_REVISION
        offer_count = await session.scalar(select(OfferRow.id))
        source_count = await session.scalar(
            select(OfferSourceRow.id).where(OfferSourceRow.source_message_id == message_id),
        )
    assert offer_count is not None
    assert source_count is not None


@pytest.mark.asyncio
async def test_persist_owner_ai_listing_rejects_unknown_revision() -> None:
    """Owner AI listing persistence fails closed for unknown revisions."""
    database = await _prepare()
    persistence = SQLAlchemyIngestionPersistence(database.session_factory)
    context = _context()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    listing = build_listing_candidate_from_ai(context=context, proposed_fields=fields)

    with pytest.raises(PersistenceBatchError, match="revision not found"):
        await persistence.persist_owner_ai_listing(
            source_message_revision_id=uuid4(),
            listing=listing,
        )


@pytest.mark.asyncio
async def test_ingestion_ai_parse_store_marks_failed_runs_as_stale_on_apply() -> None:
    """Failed runs cannot be marked applied."""
    database = await _prepare()
    owner_id = await _seed_owner(database)
    message_id, revision_id = await _seed_parse_miss(database)
    store = SQLAlchemyIngestionAiParseStore(database.session_factory)
    generate = GenerateIngestionAiParse(
        store,
        FakeChatCompletions(error=ProviderOutcome.SCHEMA),
        SQLAlchemyAdminAuditStore(database.session_factory),
        FakeClock(_NOW),
        _runtime(),
    )
    failed = await generate(
        owner_id=owner_id,
        source_message_revision_id=revision_id,
        request_id=uuid4(),
    )
    assert failed.run is not None
    status = await store.mark_applied(
        failed.run.id,
        offer_id=uuid4(),
        applied_at=_NOW,
    )
    assert status is IngestionAiApplyStatus.STALE
    assert await store.has_primary_offer(message_id) is False


@pytest.mark.asyncio
async def test_ingestion_ai_parse_store_insert_run_handles_duplicate_pending() -> None:
    """Duplicate pending inserts fail closed without raising."""
    database = await _prepare()
    owner_id = await _seed_owner(database)
    _message_id, revision_id = await _seed_parse_miss(database)
    store = SQLAlchemyIngestionAiParseStore(database.session_factory)
    generate = GenerateIngestionAiParse(
        store,
        FakeChatCompletions(payload=_payload()),
        SQLAlchemyAdminAuditStore(database.session_factory),
        FakeClock(_NOW),
        _runtime(),
    )
    generated = await generate(
        owner_id=owner_id,
        source_message_revision_id=revision_id,
        request_id=uuid4(),
    )
    assert generated.run is not None
    duplicate = IngestionAiParseRun(
        id=uuid4(),
        owner_user_id=owner_id,
        source_message_id=generated.run.source_message_id,
        source_message_revision_id=revision_id,
        external_message_id=generated.run.external_message_id,
        state=ReviewRunState.PENDING,
        model=ALLOWED_GROQ_MODEL,
        prompt_version="ingestion-ai-parse-v1",
        schema_version="ingestion-ai-parse-schema-v1",
        input_fingerprint="d" * 64,
        source_checksum=generated.run.source_checksum,
        proposed_fields=generated.run.proposed_fields,
        verdict=IngestionAiParseVerdict.LISTING_PROPOSED.value,
        warnings=(),
        token_input=1,
        token_output=1,
        provider_latency_ms=1,
        provider_outcome=ProviderOutcome.SUCCEEDED,
        provider_request_id="dup",
        created_at=_NOW,
        expires_at=_NOW,
        applied_at=None,
        offer_id=None,
    )
    assert await store.insert_run(duplicate) is False


@pytest.mark.asyncio
async def test_ingestion_ai_parse_store_mark_applied_unknown_run() -> None:
    """Unknown run ids return a bounded apply status."""
    database = await _prepare()
    store = SQLAlchemyIngestionAiParseStore(database.session_factory)
    status = await store.mark_applied(
        uuid4(),
        offer_id=uuid4(),
        applied_at=_NOW,
    )
    assert status is IngestionAiApplyStatus.UNKNOWN


@pytest.mark.asyncio
async def test_ingestion_ai_parse_store_get_revision_context_missing() -> None:
    """Unknown revision ids do not load parse context."""
    database = await _prepare()
    store = SQLAlchemyIngestionAiParseStore(database.session_factory)
    assert await store.get_revision_context(uuid4()) is None
