"""Durable bounded queue selection, current-revision guards and claim recovery."""

# ruff: noqa: RUF001 - multilingual source-equivalent fixtures

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_listing_extraction import _message
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge
from wef_backend.database import create_database_resources
from wef_backend.features.admin.infrastructure.recovery_queue import SQLAlchemyRecoveryQueue
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.domain.extraction import ExtractionResult
from wef_backend.features.ingestion.domain.model import RawMessage
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]


async def test_queue_deduplicates_claims_and_rechecks_eligibility() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    now = datetime.now(UTC)
    owner = uuid4()
    queue = SQLAlchemyRecoveryQueue(db.session_factory)
    try:
        raw = _message("Продажа: квартира\nЦена апартамента: 780 000 PLN\nПлощадь: 37.50 m²")
        await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(db.session_factory))(
            channel=raw.source,
            messages=[PersistableMessage(raw, _missing_price(raw))],
            metadata=RunMetadata(parser_version=PARSER_VERSION),
        )
        assert await queue.enqueue(owner, now) == 1
        assert await queue.enqueue(owner, now) == 0
        work = await queue.claim(owner, now)
        assert work is not None
        assert await queue.claim(owner, now) is None
        reclaimed = await queue.claim(owner, now + timedelta(minutes=3))
        assert reclaimed is not None
        assert reclaimed.id == work.id
        assert reclaimed.claim_id != work.claim_id
        await queue.finish(work, "terminal", "stale_claim", now)
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT state FROM ai_recovery_work WHERE id=:id"), {"id": work.id}
                )
                == "claimed"
            )
        assert not await queue.defer_provider(reclaimed, now)
        assert not await queue.canary_passed()
        async with db.session_factory.begin() as session:
            await session.execute(text("UPDATE source_messages SET deleted_at=:now"), {"now": now})
        assert await queue.claim(owner, now + timedelta(minutes=6)) is None
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT state FROM ai_recovery_work WHERE id=:id"), {"id": work.id}
                )
                == "superseded"
            )
    finally:
        await _purge()
        await db.engine.dispose()


async def test_local_failure_backoff_and_provider_uncertainty_are_durable() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    now, owner = datetime.now(UTC), uuid4()
    queue = SQLAlchemyRecoveryQueue(db.session_factory)
    try:
        raw = _message("Продажа: квартира\nЦена апартамента: 780 000 PLN\nПлощадь: 37.50 m²")
        await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(db.session_factory))(
            channel=raw.source,
            messages=[PersistableMessage(raw, _missing_price(raw))],
            metadata=RunMetadata(parser_version=PARSER_VERSION),
        )
        await queue.enqueue(owner, now)
        for minutes in (0, 1, 3):
            work = await queue.claim(owner, now + timedelta(minutes=minutes))
            assert work is not None
            await queue.retry_local(work, now + timedelta(minutes=minutes))
        assert work is not None
        assert await queue.claim(owner, now + timedelta(hours=1)) is None
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT reason FROM ai_recovery_work WHERE id=:id"), {"id": work.id}
                )
                == "systemic_failure"
            )
        async with db.session_factory.begin() as session:
            await session.execute(
                text(
                    "UPDATE ai_recovery_work SET state='queued',next_eligible_at=:now WHERE id=:id"
                ),
                {"now": now, "id": work.id},
            )
            await session.execute(
                text("""
                INSERT INTO ai_provider_attempts
                    (id,owner_id,operation_id,work_key,ordinal,state,reason,created_at)
                VALUES (:id,:owner,:operation,'fixture',1,'uncertain','uncertain_submission',:now)
            """),
                {"id": uuid4(), "owner": owner, "operation": work.id, "now": now},
            )
        work = await queue.claim(owner, now)
        assert work is not None
        assert await queue.defer_provider(work, now)
        assert await queue.claim(owner, now + timedelta(days=1)) is None
        assert await queue.cohort_outcome(work) == ("terminal", "unsupported_or_failed_proposal")
    finally:
        await _purge()
        await db.engine.dispose()


def _missing_price(raw: RawMessage) -> ExtractionResult:
    """Inject a missed field so queue tests do not depend on a fixed parser defect."""
    result = extract_listing(raw)
    assert result.listing is not None
    return replace(result, listing=replace(result.listing, apartment_price=None))
