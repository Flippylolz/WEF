"""PostGIS generate/apply coverage for place AI review persistence."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import select, text

from tests.fakes import FakeChatCompletions, FakeClock
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    AiCurationRuntime,
    ApplyPlaceReview,
    GeneratePlaceReview,
    PlaceReviewStatus,
    ReviewRunState,
)
from wef_backend.features.admin.infrastructure.ai_review_store import SQLAlchemyPlaceAiReviewStore
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.features.ingestion.application.persistence import normalized_location_key
from wef_backend.features.ingestion.domain.geocoding import SelectionReason
from wef_backend.features.ingestion.infrastructure.models import LocationGeocodeSelectionRow
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

_NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


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
            "DELETE FROM place_ai_review_runs",
            "DELETE FROM offer_field_origins",
            "DELETE FROM offer_ai_field_events",
            "DELETE FROM offer_ai_enrichment_items",
            "DELETE FROM offer_ai_enrichment_batches",
            "DELETE FROM location_geocode_selections",
            "DELETE FROM admin_audit_events",
            "DELETE FROM source_message_parse_issues",
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
    return database


def _location(address: str, *, district: str = "Mokotów") -> LocationRow:
    return LocationRow(
        id=uuid4(),
        display_name=address.split(",", maxsplit=1)[0].strip(),
        display_address=address,
        normalized_address=address,
        normalized_address_hash=normalized_location_key(address),
        selected_geocode_result_id=None,
        district=district,
        city="Warszawa",
        country_code="PL",
        point=None,
        precision="unknown",
        confidence=Decimal("0.30"),
        review_status="needs_review",
        out_of_scope=False,
        updated_at=_NOW,
    )


async def _seed_place(
    database: DatabaseResources,
    location: LocationRow,
    source_text: str,
) -> UUID:
    channel_id, message_id, revision_id = uuid4(), uuid4(), uuid4()
    offer_id = uuid4()
    checksum = "d" * 64
    async with database.session_factory() as session, session.begin():
        session.add(location)
        session.add(
            OfferRow(
                id=offer_id,
                location_id=location.id,
                content_type="unit",
                market_type="primary",
                property_type="unknown",
                visibility="visible",
                published_at=_NOW,
                latest_source_at=_NOW,
                currency="PLN",
                price_min_minor=100_000,
                price_max_minor=100_000,
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
    return revision_id


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


def _payload(revision_id: UUID, *, address: str, district: str) -> dict[str, object]:
    return {
        "verdict": "corrections_proposed",
        "fields": [
            {
                "field_name": "display_name",
                "action": "correct",
                "current_value": "old",
                "proposed_value": "Osiedle Przykład",
                "confidence": "high",
                "evidence_revision_ids": [str(revision_id)],
                "rationale_code": "supported",
            },
            {
                "field_name": "display_address",
                "action": "correct",
                "current_value": "old",
                "proposed_value": address,
                "confidence": "high",
                "evidence_revision_ids": [str(revision_id)],
                "rationale_code": "supported",
            },
            {
                "field_name": "district",
                "action": "correct",
                "current_value": "old",
                "proposed_value": district,
                "confidence": "high",
                "evidence_revision_ids": [str(revision_id)],
                "rationale_code": "supported",
            },
        ],
        "warnings": [],
    }


async def test_generate_apply_lineage_and_collision() -> None:
    """Apply address/district appends AI lineage; colliding hashes are denied."""
    database = await _prepare()
    store = SQLAlchemyPlaceAiReviewStore(database.session_factory)
    audits = SQLAlchemyAdminAuditStore(database.session_factory)
    clock = FakeClock(moment=_NOW)
    owner_id = await _owner(database)
    location = _location("ul. Przykładowa 1, Warszawa")
    other = _location("ul. Kolizyjna 9, Warszawa")
    revision_id = await _seed_place(
        database,
        location,
        "Osiedle Przykład ul. Nowa 2 Mokotów +48111222333",
    )
    async with database.session_factory.begin() as session:
        session.add(other)
    provider = FakeChatCompletions(
        payload=_payload(revision_id, address="ul. Nowa 2, Warszawa", district="Mokotów"),
    )
    generate = GeneratePlaceReview(store, provider, audits, clock, _runtime())
    apply = ApplyPlaceReview(store, audits, clock, _runtime())

    generated = await generate(
        owner_id=owner_id,
        location_id=location.id,
        request_id=uuid4(),
    )
    assert generated.status is PlaceReviewStatus.GENERATED
    assert generated.run is not None
    assert generated.run.state is ReviewRunState.PENDING
    sent = provider.calls[0][1]["content"]
    assert "+48111222333" not in sent

    applied = await apply(
        owner_id=owner_id,
        run_id=generated.run.id,
        selected_fields=("display_address", "district"),
        request_id=uuid4(),
    )
    assert applied.state is ReviewRunState.APPLIED

    async with database.session_factory() as session:
        row = await session.get(LocationRow, location.id)
        selections = (
            await session.scalars(
                select(LocationGeocodeSelectionRow).where(
                    LocationGeocodeSelectionRow.location_id == location.id,
                ),
            )
        ).all()
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        pending = await session.scalar(
            text("SELECT count(*) FROM place_ai_review_runs WHERE state = 'pending'"),
        )
    assert row is not None
    assert row.display_address == "ul. Nowa 2, Warszawa"
    assert row.district == "Mokotów"
    assert row.review_status == "needs_review"
    assert row.point is None
    assert [item.reason_code for item in selections] == [
        SelectionReason.AI_ASSISTED_CORRECTION.value,
    ]
    assert selections[0].actor_type == "operator"
    assert selections[0].actor_id == str(owner_id)
    assert revision == EXPECTED_DATABASE_REVISION
    assert pending == 0

    colliding = _location("ul. Inna 3, Warszawa")
    collision_revision = await _seed_place(
        database,
        colliding,
        "ul. Kolizyjna 9 Mokotów",
    )
    collision_provider = FakeChatCompletions(
        payload=_payload(
            collision_revision,
            address="ul. Kolizyjna 9, Warszawa",
            district="Mokotów",
        ),
    )
    collision_generate = GeneratePlaceReview(
        store,
        collision_provider,
        audits,
        clock,
        _runtime(),
    )
    collision_review = await collision_generate(
        owner_id=owner_id,
        location_id=colliding.id,
        request_id=uuid4(),
    )
    assert collision_review.run is not None
    with pytest.raises(AdminDeniedError, match="collision"):
        await apply(
            owner_id=owner_id,
            run_id=collision_review.run.id,
            selected_fields=("display_address",),
            request_id=uuid4(),
        )
    async with database.session_factory() as session:
        unchanged = await session.get(LocationRow, colliding.id)
    assert unchanged is not None
    assert unchanged.display_address == "ul. Inna 3, Warszawa"
    await database.engine.dispose()


async def test_one_pending_run_per_location() -> None:
    """The partial unique index refuses a second pending review for one place."""
    database = await _prepare()
    store = SQLAlchemyPlaceAiReviewStore(database.session_factory)
    audits = SQLAlchemyAdminAuditStore(database.session_factory)
    owner_id = await _owner(database)
    location = _location("ul. Unikalna 1, Warszawa")
    revision_id = await _seed_place(database, location, "ul. Unikalna 1 Mokotów")
    provider = FakeChatCompletions(
        payload=_payload(revision_id, address="ul. Unikalna 1, Warszawa", district="Mokotów"),
    )
    generate = GeneratePlaceReview(store, provider, audits, FakeClock(moment=_NOW), _runtime())
    first = await generate(owner_id=owner_id, location_id=location.id, request_id=uuid4())
    second = await generate(owner_id=owner_id, location_id=location.id, request_id=uuid4())
    assert first.status is PlaceReviewStatus.GENERATED
    assert second.status is PlaceReviewStatus.DENIED
    assert second.reason == "in_flight"
    await database.engine.dispose()
