"""Historical source/version replay must preserve identity and guarded canonical state."""

# ruff: noqa: RUF001 - multilingual synthetic source evidence

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from tests.fakes import FakeChatCompletions, FakeClock
from tests.test_listing_extraction import _message
from tests.test_offer_ai_enrichment_integration import _owner, _runtime
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge
from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.admin.application.offer_enrichment import (
    ItemOutcome,
    ProcessOfferEnrichmentItem,
    StartOfferEnrichmentBatch,
)
from wef_backend.features.admin.infrastructure.ai_enrichment_store import (
    SQLAlchemyOfferAiEnrichmentStore,
)
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.parser_replay import (
    RELEASE,
    SQLAlchemyParserReplay,
)
from wef_backend.features.ingestion.infrastructure.parser_replay_rollback import (
    rollback_parser_work,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]
SOURCE = (
    "Продажа: квартира\nЦена апартамента: 780 000 PLN\n"
    "Площадь: 37.50 m²\nLokalizacja: Warszawa, Testowa 1"
)


@pytest.fixture
async def replay_db() -> AsyncIterator[DatabaseResources]:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    async with db.session_factory.begin() as session:
        await session.execute(text("DELETE FROM parser_replay_work"))
        await session.execute(text("DELETE FROM parser_replay_releases"))
    try:
        yield db
    finally:
        await _purge()
        async with db.session_factory.begin() as session:
            await session.execute(text("DELETE FROM parser_replay_releases"))
        await db.engine.dispose()


async def seed(db: DatabaseResources, *, count: int = 1) -> UUID:
    """Retain genuine original JSON while simulating a former parser's missing price."""
    source = _message(SOURCE).source
    messages = []
    for index in range(count):
        raw = decode_archived_payload(
            {
                "id": 501 + index,
                "type": "message",
                "date_unixtime": "1925089440",
                "text": SOURCE,
            },
            source,
        )
        extracted = extract_listing(raw)
        assert extracted.listing is not None
        old = replace(
            extracted,
            decision=replace(extracted.decision, parser_version="e2-v13"),
            listing=replace(extracted.listing, parser_version="e2-v13", apartment_price=None),
        )
        messages.append(PersistableMessage(raw, old))
    await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(db.session_factory))(
        channel=source, messages=messages, metadata=RunMetadata(parser_version="e2-v13")
    )
    async with db.session_factory() as session:
        offer = await session.scalar(select(OfferRow.id).order_by(OfferRow.id))
        assert offer is not None
        return offer


async def test_canary_apply_and_second_run_preserve_identity(replay_db: DatabaseResources) -> None:
    offer_id = await seed(replay_db)
    owner_id = await _owner(replay_db)
    now = datetime.now(UTC)
    replay = SQLAlchemyParserReplay(replay_db.session_factory)
    async with replay_db.session_factory.begin() as session:
        await session.execute(text("UPDATE offers SET visibility='hidden'"))
        await session.execute(
            text(
                """
INSERT INTO favorite_locations(user_id,location_id) SELECT
:owner,location_id FROM offers
"""
            ),
            {"owner": owner_id},
        )
        await session.execute(
            text("""
INSERT INTO
contact_points(id,offer_id,source_message_id,kind,value_ciphertext,
masked_value,fingerprint_hmac,is_revealable) SELECT
:id,o.id,m.id,'phone','synthetic-encrypted-envelope','***','fixture-hmac',false
FROM offers o CROSS JOIN source_messages m
"""),
            {"id": uuid4()},
        )
        original = (
            await session.execute(
                text("SELECT id,location_id,source_text_public_masked FROM offers")
            )
        ).one()
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert await replay.counts() == {"observed": 1}
    async with replay_db.session_factory() as session:
        assert await session.scalar(text("SELECT price_min_minor FROM offers")) is None
        assert await session.scalar(text("SELECT count(*) FROM parser_replay_field_events")) == 0
    apply_work = await replay.claim(now + timedelta(minutes=1), apply=True)
    assert apply_work is not None
    await replay.process(apply_work, now + timedelta(minutes=1), apply=True)
    assert await replay.counts() == {"updated": 1}
    async with replay_db.session_factory() as session:
        row = await session.get(OfferRow, offer_id)
        assert row is not None
        assert (row.price_min_minor, row.currency, row.visibility, row.parser_version) == (
            78000000,
            "PLN",
            "hidden",
            "e2-v14",
        )
        assert (
            row.id,
            row.location_id,
            row.source_text_public_masked,
        ) == original
        snapshot = (await session.execute(text("SELECT updated_at FROM offers"))).scalar_one()
        events = await session.scalar(text("SELECT count(*) FROM parser_replay_field_events"))
        assert (
            await session.scalar(
                text(
                    """
SELECT parser_version FROM offer_field_origins WHERE
field_name='apartment_price_min'
"""
                )
            )
            == "e2-v14"
        )
        assert (
            await session.scalar(
                text(
                    """
SELECT extraction_json->'apartment_price'->'value'->>'min_minor' FROM
offer_sources
"""
                )
            )
            == "78000000"
        )
    await replay.tick(now + timedelta(minutes=2), apply=True, live_ready=lambda: True)
    async with replay_db.session_factory() as session:
        assert await session.scalar(text("SELECT updated_at FROM offers")) == snapshot
        assert (
            await session.scalar(text("SELECT count(*) FROM parser_replay_field_events")) == events
        )
        assert await session.scalar(text("SELECT count(*) FROM offers")) == 1
        assert (
            await session.scalar(
                text("SELECT count(*) FROM favorite_locations WHERE user_id=:owner"),
                {"owner": owner_id},
            )
            == 1
        )
        assert (
            await session.scalar(text("SELECT value_ciphertext FROM contact_points"))
            == "synthetic-encrypted-envelope"
        )


async def test_owner_change_during_canary_is_preserved(replay_db: DatabaseResources) -> None:
    await seed(replay_db)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.tick(now, apply=False, live_ready=lambda: True)
    async with replay_db.session_factory.begin() as session:
        await session.execute(
            text(
                """
UPDATE offers SET
price_min_minor=99000000,price_max_minor=99000000,currency='EUR'
"""
            )
        )
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert await replay.counts() == {"protected_conflict": 1}
    async with replay_db.session_factory() as session:
        assert (
            await session.execute(
                text("SELECT price_min_minor,currency,parser_version FROM offers")
            )
        ).one() == (99000000, "EUR", "e2-v13")
        assert (
            await session.scalar(
                text("""
SELECT count(*) FROM parser_replay_field_events WHERE
field_name='currency'
""")
            )
            == 0
        )


async def test_claim_restart_stale_finish_and_deleted_source(replay_db: DatabaseResources) -> None:
    await seed(replay_db)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.discover(now)
    first = await replay.claim(now, apply=True)
    assert first is not None
    assert await replay.claim(now, apply=True) is None
    second = await replay.claim(now + timedelta(minutes=3), apply=True)
    assert second is not None
    assert first["claim_id"] != second["claim_id"]
    await replay.finish(first, "failed", "stale", now)
    assert await replay.counts() == {"claimed": 1}
    async with replay_db.session_factory.begin() as session:
        await session.execute(text("UPDATE source_messages SET deleted_at=:now"), {"now": now})
    await replay.process(second, now, apply=True)
    assert await replay.counts() == {"excluded": 1}


async def test_failure_backoff_terminal_and_version_downgrade(replay_db: DatabaseResources) -> None:
    await seed(replay_db)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.discover(now)
    for minutes in (0, 1, 3):
        work = await replay.claim(now + timedelta(minutes=minutes), apply=True)
        assert work is not None
        await replay.fail(work, now + timedelta(minutes=minutes))
    assert await replay.counts() == {"failed": 1}
    await replay.promote()
    async with replay_db.session_factory.begin() as session:
        assert (
            await session.scalar(
                text("""
SELECT phase FROM parser_replay_releases WHERE version=:version
"""),
                {"version": RELEASE},
            )
            == "canary"
        )
        await session.execute(
            text(
                """
INSERT INTO
parser_replay_releases(version,parser_version,policy_version,phase)
VALUES ('future','e2-v15','source-evidence-v1','running')
"""
            )
        )
    await replay.discover(now)
    assert await replay.claim(now + timedelta(days=1), apply=True) is None
    async with replay_db.session_factory() as session:
        assert (
            await session.scalar(
                text("""
SELECT phase FROM parser_replay_releases WHERE version=:version
"""),
                {"version": RELEASE},
            )
            == "paused"
        )


@pytest.mark.parametrize(
    ("mutation", "outcome"),
    [
        (
            """
UPDATE source_message_revisions SET raw_payload_json='null'::jsonb
""",
            "source_absent",
        ),
        (
            """
UPDATE source_message_revisions SET raw_payload_json='{}'::jsonb
""",
            "excluded",
        ),
        (
            """
UPDATE source_message_revisions SET text_original='different'
""",
            "source_absent",
        ),
        ("DELETE FROM offer_sources", "excluded"),
        ("UPDATE offers SET parser_version='owner-ai-v1'", "excluded"),
        ("UPDATE offers SET parser_version='e2-v15'", "excluded"),
    ],
)
async def test_explicit_terminal_populations_do_not_starve(
    replay_db: DatabaseResources, mutation: str, outcome: str
) -> None:
    await seed(replay_db)
    async with replay_db.session_factory.begin() as session:
        await session.execute(text(mutation))
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert await replay.counts() == {outcome: 1}
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert sum((await replay.counts()).values()) == 1


async def test_read_only_canary_is_bounded_at_25_and_live_priority(
    replay_db: DatabaseResources,
) -> None:
    await seed(replay_db, count=30)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.tick(now, apply=True, live_ready=lambda: False)
    assert await replay.counts() == {}
    await replay.tick(now, apply=False, live_ready=lambda: True)
    assert await replay.counts() == {"observed": 25, "queued": 5}
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert await replay.counts() == {"updated": 30}


async def test_concurrent_workers_share_one_claim_and_source_edit_wins(
    replay_db: DatabaseResources,
) -> None:
    await seed(replay_db, count=2)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.discover(now)
    claims = await asyncio.gather(*(replay.claim(now, apply=True) for _ in range(5)))
    held = [claim for claim in claims if claim is not None]
    assert len(held) == 1
    work = held[0]
    async with replay_db.session_factory.begin() as session:
        new_revision = uuid4()
        await session.execute(
            text("""
INSERT INTO
source_message_revisions(id,source_message_id,revision_number,captured_at,
message_type,published_at,edited_at,text_original,entities_json,raw_payload_json,raw_checksum)
SELECT
:new,source_message_id,revision_number+1,captured_at,message_type,published_at,
edited_at,text_original,entities_json,raw_payload_json,raw_checksum FROM
source_message_revisions WHERE id=:old
"""),
            {"new": new_revision, "old": work["revision_id"]},
        )
        await session.execute(
            text("""
UPDATE source_messages SET current_revision_id=:new WHERE id=:message
"""),
            {"new": new_revision, "message": work["message_id"]},
        )
    await replay.process(work, now, apply=True)
    assert (await replay.counts())["excluded"] == 1
    async with replay_db.session_factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM parser_replay_field_events")) == 0


@pytest.mark.parametrize("owner_change", [False, True])
async def test_rollback_is_guarded_and_restart_safe(
    replay_db: DatabaseResources, *, owner_change: bool
) -> None:
    await seed(replay_db)
    replay, now = SQLAlchemyParserReplay(replay_db.session_factory), datetime.now(UTC)
    await replay.tick(now, apply=True, live_ready=lambda: True)
    await replay.tick(now, apply=True, live_ready=lambda: True)
    async with replay_db.session_factory.begin() as session:
        work_id = await session.scalar(text("SELECT id FROM parser_replay_work"))
        assert isinstance(work_id, UUID)
        if owner_change:
            await session.execute(
                text("""
UPDATE offers SET price_min_minor=99000000,price_max_minor=99000000
""")
            )
    result = await rollback_parser_work(replay_db.session_factory, work_id, now)
    assert result["reverted"] > 0
    assert bool(result["protected_conflict"]) == owner_change
    async with replay_db.session_factory() as session:
        assert await session.scalar(text("SELECT price_min_minor FROM offers")) == (
            99000000 if owner_change else None
        )
        assert await session.scalar(text("SELECT phase FROM parser_replay_releases")) == "paused"
    second = await rollback_parser_work(replay_db.session_factory, work_id, now)
    assert second["reverted"] == 0
    assert await rollback_parser_work(replay_db.session_factory, uuid4(), now) == {
        "reverted": 0,
        "protected_conflict": 0,
    }


async def test_active_ai_origin_survives_parser_replay(replay_db: DatabaseResources) -> None:
    offer_id = await seed(replay_db)
    owner, now = await _owner(replay_db), datetime.now(UTC)
    async with replay_db.session_factory() as session:
        revision = await session.scalar(text("SELECT current_revision_id FROM source_messages"))
    store = SQLAlchemyOfferAiEnrichmentStore(replay_db.session_factory)
    audits = SQLAlchemyAdminAuditStore(replay_db.session_factory)
    clock = FakeClock(moment=now)
    provider = FakeChatCompletions(
        payload={
            "fields": [
                {
                    "field_name": "apartment_price_min",
                    "proposed_value": "780000",
                    "source_revision_id": str(revision),
                    "evidence_fragment": "780 000 PLN",
                    "confidence": "high",
                },
                {
                    "field_name": "currency",
                    "proposed_value": "PLN",
                    "source_revision_id": str(revision),
                    "evidence_fragment": "PLN",
                    "confidence": "high",
                },
            ]
        }
    )
    runtime = replace(_runtime(), auto_apply_fields=frozenset({"apartment_price_min", "currency"}))
    batch = await StartOfferEnrichmentBatch(store, audits, clock, runtime)(
        owner_id=owner, request_id=uuid4(), offer_ids=(offer_id,)
    )
    outcome = await ProcessOfferEnrichmentItem(store, provider, audits, clock, runtime)(
        owner_id=owner, request_id=uuid4(), batch_id=batch.id
    )
    assert outcome is ItemOutcome.APPLIED
    async with replay_db.session_factory() as session:
        origins = (
            await session.execute(
                text("""
SELECT field_name,field_event_id,value_fingerprint,state FROM
offer_field_origins WHERE origin='ai' ORDER BY field_name
""")
            )
        ).all()
    replay = SQLAlchemyParserReplay(replay_db.session_factory)
    await replay.tick(now, apply=True, live_ready=lambda: True)
    await replay.tick(now, apply=True, live_ready=lambda: True)
    assert await replay.counts() == {"protected_conflict": 1}
    async with replay_db.session_factory() as session:
        assert (
            await session.execute(
                text("""
SELECT field_name,field_event_id,value_fingerprint,state FROM
offer_field_origins WHERE origin='ai' ORDER BY field_name
""")
            )
        ).all() == origins
