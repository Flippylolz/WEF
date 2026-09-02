"""Postgres coverage for public data_origin projection from active AI origins."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from geoalchemy2.elements import WKTElement
from sqlalchemy import text

from tests.fakes import FakeChatCompletions, FakeClock
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.ai_review import ALLOWED_GROQ_MODEL, AiCurationRuntime
from wef_backend.features.admin.application.offer_enrichment import (
    ItemOutcome,
    ProcessOfferEnrichmentItem,
    RevertOfferEnrichmentBatch,
    StartOfferEnrichmentBatch,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_store import (
    SQLAlchemyOfferAiEnrichmentStore,
)
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.application import BrowseLocationOffers, GetOfferDetail
from wef_backend.features.catalog.application.map_query import BoundingBox, MapFilters
from wef_backend.features.catalog.infrastructure.browse_adapter import (
    SQLAlchemyCatalogBrowseAdapter,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.catalog.infrastructure.offer_detail_adapter import (
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.features.ingestion.application.persistence import normalized_location_key
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_SOURCE = "Piętro 4 przy metrze."


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
                "DELETE FROM offer_sources",
                "DELETE FROM offers",
                "DELETE FROM source_message_revisions",
                "DELETE FROM source_messages",
                "DELETE FROM source_channels",
                "DELETE FROM locations",
                "DELETE FROM users",
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


async def _seed_offer(database: DatabaseResources, source_text: str) -> tuple[UUID, UUID, UUID]:

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
                point=WKTElement("POINT(21.0 52.2)", srid=4326),
                precision="building",
                confidence=Decimal("0.90"),
                review_status="accepted",
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
    return offer_id, revision_id, location_id


async def test_data_origin_switches_with_active_ai_origin() -> None:
    """Public detail and browse projections derive parser vs ai_assisted correctly."""
    database = await _prepare()
    try:
        store = SQLAlchemyOfferAiEnrichmentStore(database.session_factory)
        audits = SQLAlchemyAdminAuditStore(database.session_factory)
        clock = FakeClock(moment=_NOW)
        owner_id = await _owner(database)
        offer_id, revision_id, location_id = await _seed_offer(database, _SOURCE)
        detail_service = GetOfferDetail(SQLAlchemyOfferDetailAdapter(database.session_factory))
        location_offers = BrowseLocationOffers(
            SQLAlchemyCatalogBrowseAdapter(database.session_factory),
        )
        filters = MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"))

        before = await detail_service(offer_id)
        assert before is not None
        assert before.data_origin == "parser"

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
        outcome = await process(owner_id=owner_id, batch_id=batch.id, request_id=uuid4())
        assert outcome is ItemOutcome.APPLIED

        assisted = await detail_service(offer_id)
        assert assisted is not None
        assert assisted.data_origin == "ai_assisted"

        page = await location_offers(
            location_id=location_id,
            filters=filters,
            include_non_matching=True,
            cursor=None,
            limit=10,
        )
        listed = next(item for item in page.items if item.id == offer_id)
        assert listed.data_origin == "ai_assisted"

        revert = RevertOfferEnrichmentBatch(store, audits, clock)
        await revert(owner_id=owner_id, batch_id=batch.id, request_id=uuid4())
        after = await detail_service(offer_id)
        assert after is not None
        assert after.data_origin == "parser"
    finally:
        await database.engine.dispose()
