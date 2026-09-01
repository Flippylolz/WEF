"""Historical persistence integration tests against disposable PostGIS."""

import asyncio
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text, update

from tests.test_persistence_application import _contact, _listing, _raw
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.domain import ContentType, OfferVisibility
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.complete_import import prepare_import
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistenceBatchError,
    PersistHistoricalIngestion,
    RunCounts,
    RunLockHeldError,
    RunMetadata,
)
from wef_backend.features.ingestion.application.source import ChannelExpectation
from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
    LiveTelegramEventProcessor,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointReconciler,
    TelegramReconciliationRequest,
)
from wef_backend.features.ingestion.domain.extraction import (
    CandidateDecision,
    CandidateReason,
    CandidateSignal,
    Confidence,
    DecimalRange,
    ExtractionResult,
    MoneyRange,
    RuleProvenance,
    SourceSpan,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
)
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        TEST_DATABASE_URL is None,
        reason="TEST_DATABASE_URL is not configured",
    ),
]

_PHONE = "+48 601 602 603"
_HANDLE = "@warsaw_sprzedaz"
PRICE_MARKER_RE = re.compile(r"\d{3} \d{3} zł")


class FailingStore(SQLAlchemyIngestionPersistence):
    """Adapter double that fails one in-transaction message deterministically."""

    def __init__(self, session_factory: object, fail_on_message_id: int) -> None:
        """Script the external message id that aborts its transaction."""
        super().__init__(session_factory)  # type: ignore[arg-type]
        self._fail_on_message_id = fail_on_message_id

    async def _persist_message(  # type: ignore[override]
        self,
        session: object,
        *,
        channel_id: object,
        persistable: PersistableMessage,
    ) -> object:
        """Raise the scripted failure before the message is reconciled."""
        if persistable.raw.external_message_id == self._fail_on_message_id:
            message = "injected failure"
            raise RuntimeError(message)
        return await super()._persist_message(
            session,  # type: ignore[arg-type]
            channel_id=channel_id,  # type: ignore[arg-type]
            persistable=persistable,
        )


def _candidate(
    message_id: int,
    body: str,
    checksum: str,
    *,
    location: str = "ul. Przykładowa 5, Warszawa",
) -> PersistableMessage:
    """Build one persistable candidate message with contacts and fields."""
    contacts = [
        _contact(body.index(value), body.index(value) + len(value), value)
        for value in (_PHONE, _HANDLE)
        if value in body
    ]
    area_marker = "40 m²"
    area_start = body.index(area_marker)
    price_marker = PRICE_MARKER_RE.search(body)
    price_value = (
        MoneyRange(
            DecimalRange(
                Decimal(price_marker.group(0).replace(" zł", "").replace(" ", "")),
                Decimal(price_marker.group(0).replace(" zł", "").replace(" ", "")),
            ),
            "PLN",
        )
        if price_marker is not None
        else None
    )
    price_span = (price_marker.start(), price_marker.end()) if price_marker is not None else None
    listing = _listing(
        text=body,
        price=price_value,
        price_span=price_span,
        area=DecimalRange(Decimal(40), Decimal(45)),
        area_span=(area_start, area_start + len(area_marker)),
        location=location,
        contacts=tuple(contacts),
    )
    signal = CandidateSignal(
        reason=CandidateReason.UNIT_MARKER,
        weight=5,
        provenance=RuleProvenance(
            rule_id="marker",
            rule_version="v1",
            confidence=Confidence.HIGH,
            spans=(SourceSpan(start=0, end=min(10, len(body))),),
        ),
    )
    decision = CandidateDecision(
        parser_version="integration@1",
        is_candidate=True,
        score=5,
        threshold=3,
        content_type=ContentType.UNIT,
        signals=(signal,),
    )
    return PersistableMessage(
        raw=_raw(message_id=message_id, text=body, checksum=checksum),
        extraction=ExtractionResult(decision=decision, listing=listing),
    )


def _plain(message_id: int, text: str, checksum: str) -> PersistableMessage:
    """Build one persistable non-candidate message."""
    return PersistableMessage(
        raw=_raw(message_id=message_id, text=text, checksum=checksum),
        extraction=None,
    )


def _settings() -> Settings:
    """Build test settings pointing at the disposable database."""
    assert TEST_DATABASE_URL is not None
    return Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )


async def _prepare() -> None:
    """Upgrade to head and remove every persisted ingestion row."""
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    await _purge()


async def _purge() -> None:
    """Remove every persisted ingestion row between tests."""
    assert TEST_DATABASE_URL is not None
    database = create_database_resources(TEST_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            for statement in (
                "DELETE FROM offer_field_origins",
                "DELETE FROM offer_ai_field_events",
                "DELETE FROM offer_ai_enrichment_items",
                "DELETE FROM offer_ai_enrichment_batches",
                "DELETE FROM place_ai_review_runs",
                "DELETE FROM source_message_parse_issues",
                "DELETE FROM offer_sources",
                "DELETE FROM offers",
                "DELETE FROM developments",
                "DELETE FROM source_messages",
                "DELETE FROM ingest_runs",
                "DELETE FROM source_channels",
                "DELETE FROM locations",
            ):
                await session.execute(text(statement))
            await session.commit()
    finally:
        await database.engine.dispose()


async def test_migration_and_replay_reconciliation() -> None:
    """Upgrade, persist, replay unchanged and changed, and reconcile."""
    assert TEST_DATABASE_URL is not None
    await _prepare()

    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    service = PersistHistoricalIngestion(store=store, batch_size=2)
    body = f"Mieszkanie 40 m², tel. {_PHONE}, {_HANDLE}, cena 560 000 zł"

    first = await service(
        channel=_raw().source,
        messages=[
            _candidate(1, body, "b" * 64),
            _plain(2, "random service message", "c" * 64),
            _candidate(3, body.replace("560 000", "590 000"), "d" * 64),
        ],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    assert first.counts == RunCounts(
        seen=3,
        created=2,
        unchanged=0,
        revised=0,
        skipped_non_candidate=1,
        offers=2,
    )
    async with database.session_factory() as session:
        revision_count = await session.scalar(
            text("SELECT count(*) FROM source_message_revisions"),
        )
        offer_count = await session.scalar(text("SELECT count(*) FROM offers"))
        offer_source_count = await session.scalar(
            text("SELECT count(*) FROM offer_sources"),
        )
        run = (
            await session.execute(
                text(
                    "SELECT status, counts_json->>'seen' AS seen "
                    "FROM ingest_runs WHERE id = :run_id"
                ),
                {"run_id": first.run_id},
            )
        ).one()
    assert revision_count == 3
    assert offer_count == 2
    assert offer_source_count == 2
    assert run.status == "succeeded"
    assert run.seen == "3"
    async with database.session_factory() as session:
        parse_issue_count = await session.scalar(
            text("SELECT count(*) FROM source_message_parse_issues"),
        )
        parse_issue = (
            await session.execute(
                text(
                    "SELECT issue_outcome, message_outcome, external_message_id "
                    "FROM source_message_parse_issues LIMIT 1"
                ),
            )
        ).one()
    assert parse_issue_count == 1
    assert parse_issue.issue_outcome == "parser_miss"
    assert parse_issue.message_outcome == "skipped_non_candidate"
    assert parse_issue.external_message_id == 2

    replay = await service(
        channel=_raw().source,
        messages=[
            _candidate(1, body, "b" * 64),
            _plain(2, "random service message", "c" * 64),
        ],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    assert replay.counts.created == 0
    assert replay.counts.unchanged == 2
    async with database.session_factory() as session:
        revisions_after_replay = await session.scalar(
            text("SELECT count(*) FROM source_message_revisions"),
        )
        offers_after_replay = await session.scalar(text("SELECT count(*) FROM offers"))
    assert revisions_after_replay == 3
    assert offers_after_replay == 2

    changed_text = body.replace("560 000 zł", "610 000 zł")
    revised = await service(
        channel=_raw().source,
        messages=[_candidate(1, changed_text, "e" * 64)],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    assert revised.counts.revised == 1
    async with database.session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT m.raw_checksum = r.raw_checksum AS current_matches, "
                    "m.text_original = r.text_original AS text_matches, "
                    "r.revision_number, "
                    "(SELECT count(*) FROM source_message_revisions mr "
                    " WHERE mr.source_message_id = m.id) AS total_revisions "
                    "FROM source_messages m "
                    "JOIN source_message_revisions r "
                    " ON r.id = m.current_revision_id "
                    "WHERE m.external_message_id = 1"
                ),
            )
        ).one()
        offer_link_count = (
            await session.execute(
                text(
                    "SELECT count(*) FROM offer_sources os "
                    "JOIN source_messages m ON m.id = os.source_message_id "
                    "WHERE m.external_message_id = 1"
                ),
            )
        ).scalar_one()
        offer_price = (
            await session.execute(
                text(
                    "SELECT DISTINCT o.price_min_minor FROM offers o "
                    "JOIN offer_sources os ON os.offer_id = o.id "
                    "JOIN source_messages m ON m.id = os.source_message_id "
                    "WHERE m.external_message_id = 1"
                ),
            )
        ).scalar_one()
    assert row.current_matches
    assert row.text_matches
    assert row.revision_number == 2
    assert row.total_revisions == 2
    assert offer_link_count == 2
    assert offer_price == 61_000_000
    await database.engine.dispose()


def _live_message(message_id: int, *, candidate: bool = False) -> LiveTelegramMessage:
    text_value = (
        "Kupno | Mieszkanie\n"
        f"Lokalizacja: Testowa {message_id}, Miasto Testowe\n"
        f"Cena: {500_000 + message_id} PLN\n"
        "Powierzchnia: 45.5 m2\n"
        "Pokoje: 2"
        if candidate
        else f"service update {message_id}"
    )
    return LiveTelegramMessage(
        external_message_id=message_id,
        text=text_value,
        published_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        edited_at=None,
        media_group_id=(
            f"incident-album-{(message_id - 29_203) // 10}"
            if 29_203 <= message_id <= 29_257
            else None
        ),
    )


async def test_checkpoint_reconciliation_converges_and_replays_in_postgres() -> None:
    """The observed incident suffix commits once and a recent-overlap replay is stable."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    identity = default_live_channel_identity()
    entity = TelegramChannelEntity(
        username=identity.username,
        channel_id=identity.channel_id,
        title=identity.channel_title,
    )
    baseline_client = FakeTelegramLiveClient(entity=entity, connected=True)
    persistence = SQLAlchemyIngestionPersistence(database.session_factory)
    await LiveTelegramEventProcessor(store=persistence, client=baseline_client)(
        identity=identity,
        events=(
            LiveTelegramEvent(
                kind=LiveTelegramEventKind.NEW,
                message=_live_message(29_202),
            ),
        ),
        manage_connection=False,
    )
    messages = tuple(
        _live_message(message_id, candidate=message_id < 29_209)
        for message_id in range(29_203, 29_258)
    )
    client = FakeTelegramLiveClient(entity=entity, messages=messages, connected=True)
    status_store = SQLAlchemyTelegramWorkerStatusStore(database.session_factory)
    reconciler = TelegramCheckpointReconciler(
        store=status_store,
        client=client,
        processor=LiveTelegramEventProcessor(store=persistence, client=client),
        processing_lock=asyncio.Lock(),
    )
    request = TelegramReconciliationRequest(identity=identity)

    first = await reconciler(request)
    assert first.starting_checkpoint_external_id == 29_202
    assert first.messages_fetched == 55
    assert first.checkpoint_external_id == 29_257
    checkpoint, _ = await status_store.latest_live_checkpoint(
        channel_external_id=identity.channel_id,
    )
    assert checkpoint == 29_257
    async with database.session_factory() as session:
        before = (
            await session.execute(
                text(
                    "SELECT (SELECT count(*) FROM source_messages) AS messages, "
                    "(SELECT count(*) FROM source_message_revisions) AS revisions, "
                    "(SELECT count(*) FROM offers) AS offers"
                ),
            )
        ).one()
    assert before.messages == 56
    assert before.offers == 6

    replay = await reconciler(request)
    assert replay.starting_checkpoint_external_id == 29_257
    assert replay.messages_fetched == 20
    assert replay.checkpoint_external_id == 29_257
    async with database.session_factory() as session:
        after = (
            await session.execute(
                text(
                    "SELECT (SELECT count(*) FROM source_messages) AS messages, "
                    "(SELECT count(*) FROM source_message_revisions) AS revisions, "
                    "(SELECT count(*) FROM offers) AS offers"
                ),
            )
        ).one()
    assert after == before
    await database.engine.dispose()


async def test_checkpoint_reconciliation_resumes_after_partial_database_failure() -> None:
    """A committed prefix remains durable and the next cycle resumes its unseen suffix."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    identity = default_live_channel_identity()
    entity = TelegramChannelEntity(
        username=identity.username,
        channel_id=identity.channel_id,
        title=identity.channel_title,
    )
    client = FakeTelegramLiveClient(
        entity=entity,
        messages=(_live_message(101), _live_message(102)),
        connected=True,
    )
    status_store = SQLAlchemyTelegramWorkerStatusStore(database.session_factory)
    failing = TelegramCheckpointReconciler(
        store=status_store,
        client=client,
        processor=LiveTelegramEventProcessor(
            store=FailingStore(database.session_factory, fail_on_message_id=102),
            client=client,
        ),
        processing_lock=asyncio.Lock(),
    )
    request = TelegramReconciliationRequest(identity=identity, overlap=0)

    with pytest.raises(PersistenceBatchError, match="ingestion batch failed"):
        await failing(request)
    checkpoint, _ = await status_store.latest_live_checkpoint(
        channel_external_id=identity.channel_id,
    )
    assert checkpoint == 101

    resumed = await TelegramCheckpointReconciler(
        store=status_store,
        client=client,
        processor=LiveTelegramEventProcessor(
            store=SQLAlchemyIngestionPersistence(database.session_factory),
            client=client,
        ),
        processing_lock=asyncio.Lock(),
    )(request)
    assert resumed.starting_checkpoint_external_id == 101
    assert resumed.checkpoint_external_id == 102
    await database.engine.dispose()


async def test_real_adapter_payloads_persist_in_bounded_batches() -> None:
    """Recursively immutable Telegram JSON persists losslessly as JSONB."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    fixture = Path(__file__).parent / "fixtures/telegram_export/sanitized-complete.json"
    prepared = prepare_import(
        TelegramDesktopExportAdapter(
            fixture,
            ChannelExpectation("9001", "public_channel", "Sanitized Fixture Channel"),
        ),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    summary = await PersistHistoricalIngestion(
        store=SQLAlchemyIngestionPersistence(database.session_factory),
        batch_size=2,
    )(
        channel=prepared.channel,
        messages=prepared.messages,
        metadata=RunMetadata(parser_version="integration@1"),
    )

    async with database.session_factory() as session:
        payload_shape = await session.scalar(
            text(
                "SELECT jsonb_typeof(raw_payload_json->'text_entities') "
                "FROM source_messages WHERE external_message_id = 101"
            ),
        )
    assert summary.counts.seen == 8
    assert payload_shape == "array"
    await database.engine.dispose()


async def test_long_location_text_persists_without_truncation() -> None:
    """Source-derived location fields preserve values beyond legacy limits."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    location = "ul. " + "Bardzo Długa Nazwa Lokalizacji " * 12 + "Warszawa"
    body = "Mieszkanie 40 m², cena 560 000 zł"

    summary = await PersistHistoricalIngestion(
        store=SQLAlchemyIngestionPersistence(database.session_factory),
        batch_size=1,
    )(
        channel=_raw().source,
        messages=[_candidate(31, body, "8" * 64, location=location)],
        metadata=RunMetadata(parser_version="integration@1"),
    )

    async with database.session_factory() as session:
        persisted = (
            await session.execute(
                text("SELECT display_name, display_address, normalized_address FROM locations"),
            )
        ).one()
    assert summary.counts.offers == 1
    assert persisted.display_name == location
    assert persisted.display_address == location
    assert persisted.normalized_address == " ".join(location.casefold().split())
    await database.engine.dispose()


async def test_reprocess_preserves_visible_catalog_visibility() -> None:
    """Live or replayed upserts must not downgrade promoted public offers."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    service = PersistHistoricalIngestion(store=store, batch_size=1)
    body = "Sprzedam mieszkanie 40 m², cena 560 000 zł"
    await service(
        channel=_raw().source,
        messages=[_candidate(51, body, "a" * 64)],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OfferRow).values(visibility=OfferVisibility.VISIBLE.value),
        )
    await service(
        channel=_raw().source,
        messages=[_candidate(51, body + " edited", "b" * 64)],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session:
        visibility = await session.scalar(text("SELECT visibility FROM offers LIMIT 1"))
    assert visibility == OfferVisibility.VISIBLE.value
    await database.engine.dispose()


async def test_contacts_never_leak_into_persisted_projections() -> None:
    """Contact values stay out of every persisted public/operational field."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    service = PersistHistoricalIngestion(store=store)
    body = f"Sprzedam mieszkanie 40 m², tel. {_PHONE}, {_HANDLE}"
    await service(
        channel=_raw().source,
        messages=[_candidate(7, body, "f" * 64)],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session:
        surfaces = (
            await session.execute(
                text(
                    "SELECT o.source_text_excerpt, o.source_text_public_masked, "
                    "os.extraction_json::text AS extraction, "
                    "ir.error_summary FROM offers o "
                    "JOIN offer_sources os ON os.offer_id = o.id "
                    "CROSS JOIN ingest_runs ir"
                ),
            )
        ).all()
    for excerpt, masked, extraction, error_summary in surfaces:
        combined = f"{excerpt}{masked}{extraction}{error_summary or ''}"
        assert _PHONE not in combined
        assert _HANDLE not in combined
        assert "602 603" not in combined
        assert "•••" in masked
    await database.engine.dispose()


async def test_run_lock_excludes_cross_process_attempts() -> None:
    """One complete-run lock excludes other processes across commits."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    first = create_database_resources(TEST_DATABASE_URL)
    second = create_database_resources(TEST_DATABASE_URL)
    first_store = SQLAlchemyIngestionPersistence(first.session_factory)
    second_store = SQLAlchemyIngestionPersistence(second.session_factory)
    async with first_store.run_lock("telegram:2180077318"):
        with pytest.raises(RunLockHeldError):
            async with second_store.run_lock("telegram:2180077318"):
                pass
        async with second_store.run_lock("telegram:other-channel"):
            pass
    async with second_store.run_lock("telegram:2180077318"):
        pass
    await first.engine.dispose()
    await second.engine.dispose()


async def test_failed_batch_rolls_back_and_resume_converges() -> None:
    """A failing bounded transaction leaves no partial rows and resumes."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    store = FailingStore(database.session_factory, fail_on_message_id=13)
    service = PersistHistoricalIngestion(store=store, batch_size=2)
    body = f"Mieszkanie 40 m², tel. {_PHONE}, {_HANDLE}, cena 560 000 zł"
    messages = [
        _candidate(11, body, "1" * 64),
        _candidate(12, body, "2" * 64),
        _candidate(13, body, "3" * 64),
    ]
    with pytest.raises(Exception, match="batch failed"):
        await service(
            channel=_raw().source,
            messages=messages,
            metadata=RunMetadata(parser_version="integration@1"),
        )
    async with database.session_factory() as session:
        failed_run = (
            await session.execute(
                text(
                    "SELECT status, error_summary, counts_json->>'seen' AS seen "
                    "FROM ingest_runs ORDER BY started_at DESC LIMIT 1"
                ),
            )
        ).one()
        source_count = await session.scalar(
            text("SELECT count(*) FROM source_messages WHERE external_message_id = 13"),
        )
    assert failed_run.status == "failed"
    assert failed_run.error_summary == "PersistenceBatchError"
    assert failed_run.seen == "2"
    assert source_count == 0

    healthy = SQLAlchemyIngestionPersistence(database.session_factory)
    resumed = await PersistHistoricalIngestion(store=healthy, batch_size=2)(
        channel=_raw().source,
        messages=messages,
        metadata=RunMetadata(parser_version="integration@1"),
    )
    assert resumed.counts.seen == 3
    async with database.session_factory() as session:
        final_count = await session.scalar(text("SELECT count(*) FROM source_messages"))
        duplicate_offers = await session.scalar(text("SELECT count(*) FROM offers"))
    assert final_count == 3
    assert duplicate_offers == 3
    await database.engine.dispose()


async def test_multilingual_offsets_reproduce_python_slicing() -> None:
    """Persisted offsets slice the exact preserved multilingual text."""
    assert TEST_DATABASE_URL is not None
    await _prepare()
    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    service = PersistHistoricalIngestion(store=store)
    source_text = "Цена квартиры — 560 000 zł, 𝔘𝔫𝔦𝔠𝔬𝔡𝔢 40 m²"  # noqa: RUF001
    message = _candidate(21, source_text, "7" * 64)
    await service(
        channel=_raw().source,
        messages=[message],
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT m.text_original, os.extraction_json::text AS extraction "
                    "FROM source_messages m "
                    "JOIN offer_sources os ON os.source_message_id = m.id "
                    "WHERE m.external_message_id = 21"
                ),
            )
        ).one()
    assert row.text_original == source_text
    provenance = json.loads(row.extraction)
    price_offsets = provenance["apartment_price"]
    assert source_text[price_offsets["source_start"] : price_offsets["source_end"]] == (
        "560 000 zł"
    )
    area_offsets = provenance["area_sqm"]
    assert source_text[area_offsets["source_start"] : area_offsets["source_end"]] == "40 m²"
    await database.engine.dispose()
