"""Ingestion transaction guards, contact backfill and development persistence."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update

from tests.test_archive_recovery_integration import payload as archive_payload
from tests.test_complete_import_integration import NOW
from tests.test_complete_import_repository_boundaries import import_database
from tests.test_current_offer_templates import APARTMENT
from tests.test_ingestion_ai_parse_integration import _seed_parse_miss
from tests.test_listing_extraction import _message as listing_message
from tests.test_offer_ai_enrichment_integration import TEST_DATABASE_URL
from tests.test_persistence_integration import _candidate
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.contacts.infrastructure.crypto import AesGcmContactCipher
from wef_backend.features.contacts.infrastructure.models import ContactPointRow
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import (
    MessageOutcome,
    PersistableMessage,
    PersistenceBatchError,
    PersistHistoricalIngestion,
    RunCheckpoint,
    RunCounts,
    RunMetadata,
)
from wef_backend.features.ingestion.application.telegram_events import RawEventRecord
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.archive_evidence import flatten_legacy_payload
from wef_backend.features.ingestion.infrastructure.models import (
    DevelopmentRow,
    MediaRecoveryIntentionRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
    TelegramArchiveResolutionRow,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
    _json_text,
    _raw_message_from_stored_revision,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from wef_backend.database import DatabaseResources


__all__ = ["import_database"]

_BODY = "Mieszkanie 40 m² cena 560 000 zł, tel. +48 601 602 603"


def _factory(session: MagicMock) -> MagicMock:
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    context = MagicMock(
        __aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock(return_value=None)
    )
    return MagicMock(return_value=context)


def test_source_json_rejects_nonserializable_values() -> None:
    """The immutable mapping fallback cannot stringify arbitrary source objects."""
    with pytest.raises(TypeError, match="not JSON serializable"):
        _json_text({"unsupported": object()})


def test_retained_revision_rebuild_handles_legacy_json_shapes() -> None:
    """Malformed legacy entities/payload use bounded empty fields, preserving identity."""
    raw = _raw_message_from_stored_revision(
        revision=SourceMessageRevisionRow(
            entities_json=None,
            raw_payload_json=None,
            published_at=NOW,
            edited_at=None,
            message_type="message",
            text_original="Synthetic retained text",
            raw_checksum="a" * 64,
        ),
        message=SourceMessageRow(external_message_id=7),
        channel=SourceChannelRow(
            platform="telegram", external_id="synthetic", display_name="Synthetic"
        ),
    )
    assert raw.text_entities == ()
    assert raw.raw_payload == {"id": 7}
    assert raw.text == "Synthetic retained text"


@pytest.mark.parametrize("operation", ["batch", "live"])
async def test_persistence_does_not_wrap_already_bounded_failures(
    operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nested transaction refusal retains its original bounded exception."""
    session = MagicMock()
    store = SQLAlchemyIngestionPersistence(_factory(session))
    error = PersistenceBatchError("bounded rejection")
    monkeypatch.setattr(store, "_persist_message", AsyncMock(side_effect=error))
    candidate = _candidate(1, _BODY, "a" * 64)
    request: Awaitable[object]
    if operation == "batch":
        request = store.persist_batch(
            channel_id=uuid4(),
            run_id=uuid4(),
            batch=((candidate, 1),),
            checkpoint=RunCheckpoint(),
            counts=RunCounts(),
        )
    else:
        request = store.persist_live_upsert(
            channel_id=uuid4(),
            run_id=uuid4(),
            message=candidate,
            checkpoint=RunCheckpoint(),
            counts=RunCounts(),
            advance_checkpoint=True,
        )
    with pytest.raises(PersistenceBatchError) as caught:
        await request
    assert caught.value is error
    assert session.begin.return_value.__aexit__.await_args.args[1] is error


async def test_source_deletion_wraps_database_failure_without_private_body() -> None:
    """Tombstone storage failure cannot escape as a provider/source-bearing exception."""
    session = MagicMock(execute=AsyncMock(side_effect=OSError("private database body")))
    with pytest.raises(PersistenceBatchError) as caught:
        await SQLAlchemyIngestionPersistence(_factory(session)).mark_source_deleted(
            channel_id=uuid4(), external_message_ids=(1,)
        )
    assert isinstance(caught.value.__cause__, OSError)
    assert "private database body" not in str(caught.value)


@pytest.mark.parametrize(
    "mode",
    ["missing_source", "stale", "deleted", "already_linked", "missing_proposal", "missing_channel"],
)
async def test_owner_listing_guards_refuse_lost_or_concurrently_changed_state(mode: str) -> None:
    """Owner approval never bypasses current-source, unique-offer or proposal checks."""
    revision_id, source_id = uuid4(), uuid4()
    revision = SourceMessageRevisionRow(id=revision_id, source_message_id=source_id)
    source = SourceMessageRow(
        id=source_id,
        source_channel_id=uuid4(),
        current_revision_id=uuid4() if mode == "stale" else revision_id,
        deleted_at=NOW if mode == "deleted" else None,
    )
    session = MagicMock()
    session.get = AsyncMock(
        side_effect=[revision, None if mode == "missing_source" else source, None]
    )
    session.scalar = AsyncMock(return_value=uuid4() if mode == "already_linked" else None)
    query = MagicMock()
    query.mappings.return_value.one_or_none.return_value = None
    session.execute = AsyncMock(return_value=query)
    store = SQLAlchemyIngestionPersistence(_factory(session))
    extraction = _candidate(1, _BODY, "a" * 64).extraction
    assert extraction is not None
    listing = extraction.listing
    assert listing is not None
    expected = {
        "missing_source": "source message not found",
        "stale": "revision is no longer current",
        "deleted": "revision is no longer current",
        "already_linked": "already has a primary offer",
        "missing_proposal": "proposal is no longer pending",
        "missing_channel": "channel not found",
    }
    with pytest.raises(PersistenceBatchError, match=expected[mode]):
        await store.persist_owner_ai_listing(
            source_message_revision_id=revision_id,
            listing=listing,
            run_id=uuid4() if mode == "missing_proposal" else None,
        )
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "mode", ["missing_revision", "missing_source", "stale", "deleted", "missing_channel"]
)
async def test_parser_replay_skips_unusable_retained_revisions(mode: str) -> None:
    """No replay mutation follows an absent, changed or deleted source boundary."""
    revision_id = uuid4()
    revision = SourceMessageRevisionRow(id=revision_id, source_message_id=uuid4())
    source = SourceMessageRow(
        source_channel_id=uuid4(),
        current_revision_id=uuid4() if mode == "stale" else revision_id,
        deleted_at=NOW if mode == "deleted" else None,
    )
    session = MagicMock(
        get=AsyncMock(
            side_effect=[
                None if mode == "missing_revision" else revision,
                None if mode == "missing_source" else source,
                None,
            ]
        )
    )
    assert (
        await SQLAlchemyIngestionPersistence(_factory(session)).replay_current_revision(revision_id)
        == "stale"
    )
    session.execute.assert_not_called()


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_development_names_are_normalized_and_not_duplicated(
    import_database: DatabaseResources,
) -> None:
    """Repeated offers in one development share its normalized location-scoped identity."""
    candidates = []
    for index, name in enumerate(("  Osiedle Testowe  ", "osiedle testowe"), start=1):
        candidate = _candidate(index, _BODY, str(index) * 64)
        extraction = candidate.extraction
        assert extraction is not None
        listing = extraction.listing
        assert listing is not None
        assert listing.location is not None
        listing = replace(listing, development_name=replace(listing.location, value=name))
        candidates.append(replace(candidate, extraction=replace(extraction, listing=listing)))
    await PersistHistoricalIngestion(
        SQLAlchemyIngestionPersistence(import_database.session_factory)
    )(
        channel=candidates[0].raw.source,
        messages=candidates,
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with import_database.session_factory() as session:
        rows = (await session.scalars(select(DevelopmentRow))).all()
        assert len(rows) == 1
        assert rows[0].display_name == "Osiedle Testowe"
        assert rows[0].normalized_name == "osiedle testowe"
        location_id = rows[0].location_id
    assert listing is not None
    async with import_database.session_factory.begin() as session:
        await SQLAlchemyIngestionPersistence(import_database.session_factory)._resolve_development(  # noqa: SLF001 - idempotent development boundary
            session, location_id, listing
        )
        assert await session.scalar(select(func.count()).select_from(DevelopmentRow)) == 1


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
@pytest.mark.parametrize("mode", ["available", "unavailable", "no_contacts"])
async def test_cipher_backfill_is_missing_only_and_never_exposes_plaintext(
    mode: str, import_database: DatabaseResources
) -> None:
    """Previously keyless offers gain encrypted contacts once keys are available."""
    candidate = _candidate(
        1, _BODY if mode != "no_contacts" else "Mieszkanie 40 m² cena 560 000 zł", "b" * 64
    )
    database = import_database
    await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(database.session_factory))(
        channel=candidate.raw.source,
        messages=(candidate,),
        metadata=RunMetadata(parser_version="integration@1"),
    )
    cipher = AesGcmContactCipher(
        encryption_key=b"c" * 32 if mode != "unavailable" else None, hmac_key=b"d" * 32
    )
    persist = PersistHistoricalIngestion(
        SQLAlchemyIngestionPersistence(database.session_factory, contact_cipher=cipher)
    )
    for _ in range(2):
        await persist(
            channel=candidate.raw.source,
            messages=(candidate,),
            metadata=RunMetadata(parser_version="integration@1"),
        )
    async with database.session_factory() as session:
        contacts = (await session.scalars(select(ContactPointRow))).all()
        offer = await session.scalar(select(OfferRow))
        assert offer is not None
        assert "+48 601 602 603" not in offer.source_text_public_masked
        assert len(contacts) == (1 if mode == "available" else 0)
        if contacts:
            assert "601602603" not in contacts[0].value_ciphertext
            assert cipher.decrypt(contacts[0].value_ciphertext) == "+48 601 602 603"


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_parser_upsert_keeps_protected_ai_field(import_database: DatabaseResources) -> None:
    """A parser replay may update other fields while retaining an active AI-owned floor."""
    database = import_database
    candidate = _candidate(1, _BODY, "b" * 64)
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    await PersistHistoricalIngestion(store)(
        channel=candidate.raw.source,
        messages=(candidate,),
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory.begin() as session:
        await session.execute(update(OfferRow).values(floor_label="4"))
    sync = MagicMock(
        protected_field_names=AsyncMock(return_value=frozenset({"floor_label"})),
        after_offer_upsert=AsyncMock(),
    )
    await PersistHistoricalIngestion(
        SQLAlchemyIngestionPersistence(database.session_factory, field_origin_sync=sync)
    )(
        channel=candidate.raw.source,
        messages=(candidate,),
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with database.session_factory() as session:
        assert await session.scalar(select(OfferRow.floor_label)) == "4"
    sync.protected_field_names.assert_awaited_once()
    sync.after_offer_upsert.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_owner_listing_without_run_id_persists_current_parse_miss(
    import_database: DatabaseResources,
) -> None:
    """Explicit owner approval can persist a current revision without an AI run record."""
    database = import_database
    _, revision_id = await _seed_parse_miss(database)
    extraction = _candidate(1, _BODY, "b" * 64).extraction
    assert extraction is not None
    listing = extraction.listing
    assert listing is not None
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    offer = await store.persist_owner_ai_listing(
        source_message_revision_id=revision_id, listing=listing
    )
    async with database.session_factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(OfferRow).where(OfferRow.id == offer)
            )
            == 1
        )
    with pytest.raises(PersistenceBatchError, match="already has a primary offer"):
        await store.persist_owner_ai_listing(
            source_message_revision_id=revision_id, listing=listing
        )


@pytest.mark.parametrize("prior_receipt", [False, True])
async def test_archived_upsert_requires_payload_unless_already_committed(
    *, prior_receipt: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing receipt is idempotent; an uncommitted upsert requires its payload."""
    event_id = uuid4()
    receipt = TelegramArchiveResolutionRow(
        event_id=event_id, disposition="applied", committed_at=NOW
    )
    session = MagicMock(
        get=AsyncMock(return_value=receipt if prior_receipt else None), flush=AsyncMock()
    )
    store = SQLAlchemyIngestionPersistence(_factory(session))
    monkeypatch.setattr(store, "ensure_channel", AsyncMock(return_value=uuid4()))
    record = RawEventRecord(event_id, "new", "synthetic", 7, {}, NOW, 0)
    if prior_receipt:
        result = await store.persist_archived_event(
            record=record, identity=default_live_channel_identity(), message=None, release_sha=None
        )
        assert result.event_id == event_id
        assert result.disposition == "applied"
        session.add.assert_not_called()
    else:
        with pytest.raises(ValueError, match="archived message is required"):
            await store.persist_archived_event(
                record=record,
                identity=default_live_channel_identity(),
                message=None,
                release_sha=None,
            )


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_parser_replay_classifies_non_candidates_without_mutating_sources(
    import_database: DatabaseResources,
) -> None:
    """A retained non-listing remains a no-op when replayed directly."""
    database = import_database
    source_id, revision_id = await _seed_parse_miss(database)
    async with database.session_factory.begin() as session:
        await session.execute(
            update(SourceMessageRevisionRow)
            .where(SourceMessageRevisionRow.id == revision_id)
            .values(text_original="synthetic non-listing")
        )
    assert (
        await SQLAlchemyIngestionPersistence(database.session_factory).replay_current_revision(
            revision_id
        )
        == "non_candidate"
    )
    async with database.session_factory() as session:
        assert (
            await session.scalar(
                select(SourceMessageRow.current_revision_id).where(SourceMessageRow.id == source_id)
            )
            == revision_id
        )


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_legacy_equivalent_live_replay_restores_media_intention_without_rewriting_source(
    import_database: DatabaseResources,
) -> None:
    """A legacy flattened observation requeues recovery for the canonical revision."""
    database = import_database
    identity = default_live_channel_identity()
    original = archive_payload(7)
    raw = decode_archived_payload(original, source_identity_from_channel(identity))
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    result = await PersistHistoricalIngestion(store)(
        channel=raw.source,
        messages=(PersistableMessage(raw, extract_listing(raw)),),
        metadata=RunMetadata(parser_version="original"),
    )
    async with database.session_factory.begin() as session:
        channel_id = await session.scalar(select(SourceChannelRow.id))
        source = await session.scalar(select(SourceMessageRow))
        assert source is not None
        revision_id = source.current_revision_id
        await session.execute(delete(MediaRecoveryIntentionRow))
    assert channel_id is not None
    legacy = decode_archived_payload(
        {
            "id": original["id"],
            "type": "message",
            "date_unixtime": original["date_unixtime"],
            "text": flatten_legacy_payload(original)["text"],
            "from_live": True,
        },
        raw.source,
    )
    assert legacy.checksum != raw.checksum
    outcome, _, _, _ = await store.persist_live_upsert(
        channel_id=channel_id,
        run_id=result.run_id,
        message=PersistableMessage(legacy, extract_listing(legacy)),
        checkpoint=RunCheckpoint(),
        counts=RunCounts(),
        advance_checkpoint=True,
    )
    assert outcome.outcome is MessageOutcome.UNCHANGED
    async with database.session_factory() as session:
        assert (
            await session.scalar(select(MediaRecoveryIntentionRow.source_revision_id))
            == revision_id
        )
        source = await session.scalar(select(SourceMessageRow))
        assert source is not None
        assert source.raw_checksum == raw.checksum
        assert source.raw_payload_json == original
    deletions = await store.mark_source_deleted(
        channel_id=channel_id, external_message_ids=(7, 999), archive_event_ids={}
    )
    assert tuple(item.outcome.value for item in deletions) == ("deleted", "missing")


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_parser_replay_can_replace_only_unknown_location_sentinel(
    import_database: DatabaseResources,
) -> None:
    """Newly extracted source evidence can resolve an old parser's unknown address."""
    database = import_database
    raw = listing_message(APARTMENT)
    extraction = extract_listing(raw)
    assert extraction.listing is not None
    old_listing = replace(extraction.listing, location=None, parser_version="old-location-miss")
    store = SQLAlchemyIngestionPersistence(database.session_factory)
    result = await PersistHistoricalIngestion(store)(
        channel=raw.source,
        messages=(PersistableMessage(raw, replace(extraction, listing=old_listing)),),
        metadata=RunMetadata(parser_version="old-location-miss"),
    )
    async with database.session_factory() as session:
        old_location = await session.scalar(select(OfferRow.location_id))
        assert (
            await session.scalar(
                select(LocationRow.display_name).where(LocationRow.id == old_location)
            )
            == "Unknown location"
        )
        revision = await session.scalar(select(SourceMessageRow.current_revision_id))
    assert revision is not None
    assert await store.replay_current_revision(revision, run_id=result.run_id) == "update_candidate"
    async with database.session_factory() as session:
        assert await session.scalar(select(OfferRow.location_id)) != old_location
