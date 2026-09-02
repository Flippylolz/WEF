"""Postgres coverage for batch checkpoints, apply, revert, and origin sync."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text

from tests.fakes import FakeChatCompletions, FakeClock
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.ai_review import ALLOWED_GROQ_MODEL, AiCurationRuntime
from wef_backend.features.admin.application.offer_enrichment import (
    BatchState,
    ItemOutcome,
    OriginKind,
    OriginState,
    PauseOfferEnrichmentBatch,
    ProcessOfferEnrichmentItem,
    ResumeOfferEnrichmentBatch,
    RevertOfferEnrichmentBatch,
    StartOfferEnrichmentBatch,
    SyncOfferAiOrigins,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_store import (
    SQLAlchemyOfferAiEnrichmentStore,
)
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.features.ingestion.application.persistence import normalized_location_key
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_SOURCE = "Piętro 4 przy metrze. Tel +48111222333"


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))


def _runtime() -> AiCurationRuntime:
    return AiCurationRuntime(
        enabled=True,
        zdr_verified=True,
        model=ALLOWED_GROQ_MODEL,
        api_key_present=True,
        auto_apply_fields=frozenset({"floor_label"}),
    )


async def _prepare() -> DatabaseResources:
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            for statement in (
                "DELETE FROM offer_field_origins",
                "DELETE FROM offer_ai_field_events",
                "DELETE FROM offer_ai_enrichment_items",
                "DELETE FROM offer_ai_enrichment_batches",
                "DELETE FROM place_ai_review_runs",
                "DELETE FROM location_geocode_selections",
                "DELETE FROM admin_audit_events",
                "DELETE FROM offer_sources",
                "DELETE FROM offers",
                "DELETE FROM developments",
                "DELETE FROM source_messages",
                "DELETE FROM ingest_runs",
                "UPDATE locations SET selected_geocode_result_id = NULL",
                "DELETE FROM geocode_miss_claims",
                "DELETE FROM geocode_results",
                "DELETE FROM locations",
                "DELETE FROM users",
                "DELETE FROM source_channels",
            ):
                await session.execute(text(statement))
            await session.commit()
    except BaseException:
        await database.engine.dispose()
        raise
    return database


async def _owner(database: DatabaseResources) -> UUID:
    owner_id = uuid4()
    async with database.session_factory.begin() as session:
        session.add(
            UserRow(
                id=owner_id,
                username_normalized=f"owner-{owner_id.hex[:8]}",
                username_display="owner",
                hashed_password="hash",
                role=UserRole.OWNER.value,
                is_active=True,
                must_change_password=False,
                created_at=_NOW,
                updated_at=_NOW,
            ),
        )
    return owner_id


async def _seed_offer(database: DatabaseResources, source_text: str) -> tuple[UUID, UUID]:
    location_id, offer_id = uuid4(), uuid4()
    channel_id, message_id, revision_id = uuid4(), uuid4(), uuid4()
    checksum = "e" * 64
    async with database.session_factory() as session, session.begin():
        session.add(
            LocationRow(
                id=location_id,
                display_name="ul. Testowa 1",
                display_address="ul. Testowa 1, Warszawa",
                normalized_address="ul. Testowa 1, Warszawa",
                normalized_address_hash=normalized_location_key("ul. Testowa 1, Warszawa"),
                selected_geocode_result_id=None,
                district="Mokotów",
                city="Warszawa",
                country_code="PL",
                point=None,
                precision="unknown",
                confidence=Decimal("0.30"),
                review_status="needs_review",
                out_of_scope=False,
                updated_at=_NOW,
            ),
        )
        session.add(
            OfferRow(
                id=offer_id,
                location_id=location_id,
                content_type="unit",
                market_type="unknown",
                property_type="unknown",
                visibility="visible",
                published_at=_NOW,
                latest_source_at=_NOW,
                parking_included_in_price=False,
                storage_included_in_price=False,
                source_text_excerpt="excerpt",
                source_text_public_masked="masked",
                canonical_fingerprint=f"fp-{offer_id}",
                parser_version="test",
            ),
        )
        await session.flush()
        await session.execute(
            text(
                "INSERT INTO source_channels "
                "(id, platform, external_id, display_name) "
                "VALUES (:id, 'telegram', :external, 'Eval source')"
            ),
            {"id": channel_id, "external": str(channel_id)},
        )
        await session.execute(
            text(
                "INSERT INTO source_messages "
                "(id, source_channel_id, external_message_id, current_revision_id, "
                "message_type, published_at, text_original, entities_json, "
                "raw_payload_json, raw_checksum, ingested_at) "
                "VALUES (:id, :channel, 1, :revision, 'message', :now, :text, "
                "'[]', '{}', :checksum, :now)"
            ),
            {
                "id": message_id,
                "channel": channel_id,
                "revision": revision_id,
                "now": _NOW,
                "text": source_text,
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
                "text": source_text,
                "checksum": checksum,
            },
        )
        await session.execute(
            text(
                "INSERT INTO offer_sources "
                "(id, offer_id, source_message_id, source_message_revision_id, "
                "relationship, confidence, extraction_json) "
                "VALUES (:id, :offer, :message, :revision, 'primary', 1.0, '{}')"
            ),
            {
                "id": uuid4(),
                "offer": offer_id,
                "message": message_id,
                "revision": revision_id,
            },
        )
    return offer_id, revision_id


async def test_batch_apply_resume_revert_and_source_edit() -> None:  # noqa: PLR0915
    """Process, crash-resume, revert, and source-edit invalidation stay missing-only."""
    database = await _prepare()
    try:
        store = SQLAlchemyOfferAiEnrichmentStore(database.session_factory)
        audits = SQLAlchemyAdminAuditStore(database.session_factory)
        clock = FakeClock(moment=_NOW)
        owner_id = await _owner(database)
        offer_id, revision_id = await _seed_offer(database, _SOURCE)
        provider = FakeChatCompletions(
            payload={
                "fields": [
                    {
                        "field_name": "floor_label",
                        "proposed_value": "4",
                        "source_revision_id": str(revision_id),
                        "evidence_fragment": "Piętro 4",
                        "confidence": "high",
                    },
                ],
            },
        )
        start = StartOfferEnrichmentBatch(store, audits, clock, _runtime())
        process = ProcessOfferEnrichmentItem(store, provider, audits, clock, _runtime())
        batch = await start(owner_id=owner_id, request_id=uuid4(), offer_ids=(offer_id,))
        item = await store.next_item(batch.id)
        assert item is not None
        await store.mark_item_processing(item, now=_NOW)
        outcome = await process(owner_id=owner_id, batch_id=batch.id, request_id=uuid4())
        assert outcome is ItemOutcome.APPLIED
        resume = await process(owner_id=owner_id, batch_id=batch.id, request_id=uuid4())
        assert resume is None
        assert await store.next_item(batch.id) is None
        assert await store.next_queued_item(batch.id) is None
        assert await store.next_processing_item(batch.id) is None
        finished = await store.get_batch(batch.id)
        assert finished is not None
        assert finished.state is BatchState.COMPLETED

        async with database.session_factory() as session:
            offer = await session.get(OfferRow, offer_id)
            revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        assert offer is not None
        assert offer.floor_label == "4"
        assert offer.market_type == "unknown"
        assert revision == EXPECTED_DATABASE_REVISION
        sent = provider.calls[0][1]["content"]
        assert "+48111222333" not in sent

        reverted = await RevertOfferEnrichmentBatch(store, audits, clock)(
            owner_id=owner_id,
            batch_id=batch.id,
            request_id=uuid4(),
        )
        assert reverted == 1
        async with database.session_factory() as session:
            offer = await session.get(OfferRow, offer_id)
        assert offer is not None
        assert offer.floor_label is None

        batch2 = await start(owner_id=owner_id, request_id=uuid4(), offer_ids=(offer_id,))
        applied = await process(owner_id=owner_id, batch_id=batch2.id, request_id=uuid4())
        assert applied is ItemOutcome.APPLIED
        origins = await store.list_active_ai_origins(offer_id)
        assert len(origins) == 1
        assert origins[0].origin is OriginKind.AI
        await SyncOfferAiOrigins(store, clock).after_offer_upsert(
            offer_id=offer_id,
            parser_values={"floor_label": "4"},
            parser_version="test",
            source_changed=True,
            actor_id="parser-replay",
        )
        async with database.session_factory() as session:
            offer = await session.get(OfferRow, offer_id)
            origin_state = await session.scalar(
                text(
                    "SELECT state FROM offer_field_origins "
                    "WHERE offer_id = :offer AND field_name = 'floor_label'"
                ),
                {"offer": offer_id},
            )
        assert offer is not None
        assert offer.floor_label is None
        assert origin_state == OriginState.STALE.value
    finally:
        await database.engine.dispose()


async def test_missing_cohort_pause_and_parser_conflict() -> None:
    """SQL store lists missing offers, pause/resume, and parser-replay conflicts."""
    database = await _prepare()
    try:
        store = SQLAlchemyOfferAiEnrichmentStore(database.session_factory)
        audits = SQLAlchemyAdminAuditStore(database.session_factory)
        clock = FakeClock(moment=_NOW)
        owner_id = await _owner(database)
        offer_id, revision_id = await _seed_offer(database, _SOURCE)
        missing = await store.list_missing_offer_ids(limit=10)
        assert offer_id in missing
        queued = await store.count_owner_queued_items(owner_id)
        assert queued == 0
        start = StartOfferEnrichmentBatch(store, audits, clock, _runtime())
        batch = await start(owner_id=owner_id, request_id=uuid4())
        assert batch.candidate_count == 1
        paused = await PauseOfferEnrichmentBatch(store, audits)(
            owner_id=owner_id,
            batch_id=batch.id,
            request_id=uuid4(),
        )
        assert paused.state is BatchState.PAUSED
        assert await store.count_owner_queued_items(owner_id) == 1
        resumed = await ResumeOfferEnrichmentBatch(store, audits)(
            owner_id=owner_id,
            batch_id=batch.id,
            request_id=uuid4(),
        )
        assert resumed.state is BatchState.RUNNING
        provider = FakeChatCompletions(
            payload={
                "fields": [
                    {
                        "field_name": "floor_label",
                        "proposed_value": "4",
                        "source_revision_id": str(revision_id),
                        "evidence_fragment": "Piętro 4",
                        "confidence": "high",
                    },
                ],
            },
        )
        process = ProcessOfferEnrichmentItem(store, provider, audits, clock, _runtime())
        outcome = await process(owner_id=owner_id, batch_id=batch.id, request_id=uuid4())
        assert outcome is ItemOutcome.APPLIED
        calls = await store.count_owner_provider_calls_since(owner_id, since=_NOW)
        assert calls == 1
        protected = await store.protected_field_names(offer_id)
        assert "floor_label" in protected
        await SyncOfferAiOrigins(store, clock).after_offer_upsert(
            offer_id=offer_id,
            parser_values={"floor_label": "5"},
            parser_version="test",
            source_changed=False,
            actor_id="parser-replay",
        )
        async with database.session_factory() as session:
            offer = await session.get(OfferRow, offer_id)
            origin_state = await session.scalar(
                text(
                    "SELECT state FROM offer_field_origins "
                    "WHERE offer_id = :offer AND field_name = 'floor_label'"
                ),
                {"offer": offer_id},
            )
        assert offer is not None
        assert offer.floor_label == "4"
        assert origin_state == OriginState.CONFLICTING.value
        missing_item = await store.get_item(uuid4())
        assert missing_item is None
    finally:
        await database.engine.dispose()
