"""Current-revision backfill includes missed offers without changing source checkpoints."""

from dataclasses import replace

import pytest
from sqlalchemy import func, select, text, update

from tests.test_current_offer_templates import APARTMENT
from tests.test_listing_extraction import _message
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge, _settings
from wef_backend import offer_backfill_command
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure.models import SourceMessageRow
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]


async def test_dry_run_apply_and_resume_preserve_identity_visibility_and_live_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _prepare()
    settings = _settings()
    monkeypatch.setattr(offer_backfill_command, "load_settings", lambda: settings)
    monkeypatch.setattr(offer_backfill_command, "build_contact_cipher", lambda _: None)
    database = create_database_resources(settings.database_url)
    try:
        raw = _message(APARTMENT)
        extraction = extract_listing(raw)
        missed = replace(
            extraction,
            listing=None,
            decision=replace(
                extraction.decision, is_candidate=False, score=0, signals=(), content_type=None
            ),
        )
        await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(database.session_factory))(
            channel=raw.source,
            messages=[PersistableMessage(raw, missed)],
            metadata=RunMetadata(parser_version="old"),
        )
        dry = await offer_backfill_command.run(
            channel=raw.source.channel_id,
            after_id=0,
            through_id=raw.external_message_id,
            limit=1,
            apply=False,
        )
        assert dry["counts"] == {"create_candidate": 1}
        async with database.session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(OfferRow)) == 0
            before = (
                await session.execute(
                    text("SELECT raw_checksum,current_revision_id FROM source_messages")
                )
            ).all()
        applied = await offer_backfill_command.run(
            channel=raw.source.channel_id,
            after_id=0,
            through_id=raw.external_message_id,
            limit=1,
            apply=True,
        )
        assert applied["counts"] == {"create_candidate": 1}
        assert applied["next_after_id"] == raw.external_message_id
        async with database.session_factory() as session, session.begin():
            offer = (await session.scalars(select(OfferRow))).one()
            offer_id = offer.id
            await session.execute(
                update(OfferRow).values(visibility="hidden", parser_version="old")
            )
        replay = await offer_backfill_command.run(
            channel=raw.source.channel_id,
            after_id=0,
            through_id=raw.external_message_id,
            limit=1,
            apply=True,
        )
        assert replay["counts"] == {"update_candidate": 1}
        async with database.session_factory() as session:
            offer = (await session.scalars(select(OfferRow))).one()
            assert offer.id == offer_id
            assert offer.visibility == "hidden"
            assert offer.price_min_minor == 81200000
            after = (
                await session.execute(
                    text("SELECT raw_checksum,current_revision_id FROM source_messages")
                )
            ).all()
            assert before == after
            assert await session.scalar(text("SELECT count(*) FROM source_message_revisions")) == 1
            assert await session.scalar(text("SELECT count(*) FROM telegram_channel_progress")) == 0
        async with database.session_factory() as session, session.begin():
            await session.execute(update(SourceMessageRow).values(deleted_at=func.now()))
        exhausted = await offer_backfill_command.run(
            channel=raw.source.channel_id,
            after_id=0,
            through_id=raw.external_message_id,
            limit=1,
            apply=False,
        )
        assert exhausted["scanned"] == 0
        assert exhausted["exhausted"] is True
    finally:
        await database.engine.dispose()
        await _purge()
