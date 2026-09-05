"""PostGIS transaction, deduplication, recovery selection and lifecycle tests."""

from __future__ import annotations

# ruff: noqa: RUF001 - intentional multilingual source-equivalent fixtures
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from tests.test_listing_extraction import _message
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge, _settings
from wef_backend.batch_ingestion_ai_parse_command import _CANDIDATES_SQL
from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.domain.extraction import (
    Confidence,
    DecimalRange,
    ExtractedValue,
    MoneyRange,
    RuleProvenance,
    SourceSpan,
)
from wef_backend.features.ingestion.infrastructure.models import (
    ParseEvaluationRow,
    ParseEvaluationTransitionRow,
    SourceMessageParseIssueRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.parse_evaluation_store import (
    record_parse_evaluation,
)
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import backfill_parse_issues
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]


@pytest.mark.asyncio
async def test_unchanged_version_is_noop_and_new_success_resolves_with_history() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        raw = _message("Продажа: квартира\nЦена апартамента: 780 000 PLN\nПлощадь: 37.50 m²")
        extraction = extract_listing(raw)
        assert extraction.listing
        assert extraction.listing.area_sqm
        extraction = replace(
            extraction,
            listing=replace(extraction.listing, apartment_price=None, parser_version="e2-v13"),
            decision=replace(extraction.decision, parser_version="e2-v13"),
        )
        service = PersistHistoricalIngestion(
            store=SQLAlchemyIngestionPersistence(database.session_factory)
        )
        for _ in range(2):
            await service(
                channel=raw.source,
                messages=[PersistableMessage(raw, extraction)],
                metadata=RunMetadata(parser_version=extraction.decision.parser_version),
            )
        async with database.session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(ParseEvaluationRow)) == 1
            assert (
                await session.scalar(select(func.count()).select_from(SourceMessageParseIssueRow))
                == 1
            )
            message = (await session.scalars(select(SourceMessageRow))).one()
            message_id, revision_id = message.id, message.current_revision_id
        assert extraction.listing is not None
        listing = replace(
            extraction.listing,
            apartment_price=ExtractedValue(
                MoneyRange(DecimalRange(Decimal(780000), Decimal(780000)), "PLN"),
                RuleProvenance(
                    "price-test",
                    "e2-v14",
                    Confidence.HIGH,
                    (
                        SourceSpan(
                            raw.text.index("780 000 PLN"),
                            raw.text.index("780 000 PLN") + len("780 000 PLN"),
                        ),
                    ),
                ),
            ),
        )
        improved = replace(
            extraction,
            listing=listing,
            decision=replace(extraction.decision, parser_version="e2-v14"),
        )
        async with database.session_factory() as session, session.begin():
            assert await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=revision_id,
                text=raw.text,
                extraction=improved,
            )
        async with database.session_factory() as session, session.begin():
            assert not await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=revision_id,
                text=raw.text,
                extraction=improved,
            )
            assert not await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=uuid4(),
                text=raw.text,
                extraction=improved,
            )
            older = replace(
                extraction, decision=replace(extraction.decision, parser_version="e2-v12")
            )
            assert not await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=revision_id,
                text=raw.text,
                extraction=older,
            )
            rows = (await session.scalars(select(ParseEvaluationRow))).all()
            assert {row.parser_version: row.state for row in rows} == {
                "e2-v13": "resolved",
                "e2-v14": "open",
                "e2-v12": "superseded",
            }
            assert (
                await session.scalar(select(func.count()).select_from(ParseEvaluationTransitionRow))
                == 1
            )
            assert (
                await session.scalar(select(func.count()).select_from(SourceMessageParseIssueRow))
                == 1
            )
    finally:
        await database.engine.dispose()
        await _purge()


@pytest.mark.asyncio
async def test_backfill_finishes_clean_rows_and_resumes_without_repeating() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        service = PersistHistoricalIngestion(
            store=SQLAlchemyIngestionPersistence(database.session_factory)
        )
        samples = [
            "For sale: apartment\nPrice: 700 000 PLN",
            "Photo album",
            "For sale apartment\nParking: 45 000 PLN",
        ]
        for index, body in enumerate(samples):
            raw = replace(_message(body), external_message_id=500 + index)
            await service(
                channel=raw.source,
                messages=[PersistableMessage(raw, extract_listing(raw))],
                metadata=RunMetadata(parser_version="e2-v13"),
            )
        async with database.session_factory() as session, session.begin():
            await session.execute(text("DELETE FROM parse_evaluations"))
            await session.execute(text("DELETE FROM source_message_parse_issues"))
        first = await backfill_parse_issues(database.session_factory, limit=1, batch_size=1)
        assert first.processed == 1
        second = await backfill_parse_issues(database.session_factory, batch_size=1)
        assert second.processed == 2
        assert (await backfill_parse_issues(database.session_factory, batch_size=1)).processed == 0
        async with database.session_factory() as session:
            candidates = (
                await session.execute(_CANDIDATES_SQL, {"limit": 100, "min_text_length": 1})
            ).all()
            assert len(candidates) == 1
            assert candidates[0].external_message_id == 502
            assert await session.scalar(select(func.count()).select_from(ParseEvaluationRow)) == 3
    finally:
        await database.engine.dispose()
        await _purge()


@pytest.mark.asyncio
async def test_rolled_back_evaluation_can_retry_and_source_edit_supersedes_old_work() -> None:
    await _prepare()
    database = create_database_resources(_settings().database_url)
    try:
        raw = _message("For sale apartment\nParking: 45 000 PLN")
        extraction = extract_listing(raw)
        service = PersistHistoricalIngestion(
            store=SQLAlchemyIngestionPersistence(database.session_factory)
        )
        await service(
            channel=raw.source,
            messages=[PersistableMessage(raw, extraction)],
            metadata=RunMetadata(parser_version="e2-v13"),
        )
        async with database.session_factory() as session:
            message = (await session.scalars(select(SourceMessageRow))).one()
            old_revision, message_id = message.current_revision_id, message.id
            changed = replace(
                extraction, decision=replace(extraction.decision, parser_version="e2-v15")
            )
            assert await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=old_revision,
                text=raw.text,
                extraction=changed,
            )
            await session.rollback()
        async with database.session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(ParseEvaluationRow)) == 1
        edited = _message("Photo album")
        await service(
            channel=edited.source,
            messages=[PersistableMessage(edited, extract_listing(edited))],
            metadata=RunMetadata(parser_version="e2-v13"),
        )
        async with database.session_factory() as session, session.begin():
            assert not await record_parse_evaluation(
                session,
                message_id=message_id,
                revision_id=old_revision,
                text=raw.text,
                extraction=changed,
            )
            candidates = (
                await session.execute(_CANDIDATES_SQL, {"limit": 100, "min_text_length": 1})
            ).all()
            assert not candidates
            assert (
                await session.scalar(select(func.count()).select_from(ParseEvaluationTransitionRow))
                == 1
            )
    finally:
        await database.engine.dispose()
        await _purge()
