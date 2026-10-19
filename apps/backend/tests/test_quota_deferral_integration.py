"""Budget refusal survives restart without losing or resubmitting recovery work."""

# Fixtures deliberately exercise Cyrillic source text.
# ruff: noqa: RUF001

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_listing_extraction import _message
from tests.test_offer_ai_enrichment_integration import _owner, _seed_offer
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare, _purge
from tests.test_recovery_queue_integration import _missing_price
from wef_backend.database import create_database_resources
from wef_backend.features.admin.infrastructure.provider_budget_store import SQLAlchemyProviderBudget
from wef_backend.features.admin.infrastructure.recovery_queue import SQLAlchemyRecoveryQueue
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]
NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
RESET = datetime(2026, 9, 6, tzinfo=UTC)


@pytest.mark.parametrize(
    "prior_state",
    ["unsubmitted", "local_limit", "uncertain", "submitted_marker", "manual_pause", "stale"],
)
async def test_unsubmitted_terminal_reconciliation_and_quota_rollover(  # noqa: PLR0915
    prior_state: str,
) -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    owner = await _owner(db)
    queue = SQLAlchemyRecoveryQueue(db.session_factory)
    try:
        raw = _message("Продажа: квартира\nЦена апартамента: 780 000 PLN\nПлощадь: 37.50 m²")
        await PersistHistoricalIngestion(SQLAlchemyIngestionPersistence(db.session_factory))(
            channel=raw.source,
            messages=[PersistableMessage(raw, _missing_price(raw))],
            metadata=RunMetadata(parser_version=PARSER_VERSION),
        )
        assert await queue.enqueue(owner, NOW) == 1
        work = await queue.claim(owner, NOW)
        assert work is not None
        await queue.finish(work, "terminal", "unsupported_or_failed_proposal", NOW)
        offer_id, _ = await _seed_offer(db, "Synthetic quota fixture")
        async with db.session_factory.begin() as session:
            await session.execute(
                text("""
                INSERT INTO ai_provider_accounts(owner_id,budget_day,used,next_eligible_at)
                VALUES (:owner,:day,20,:now)
            """),
                {"owner": owner, "day": NOW.date(), "now": NOW},
            )
            await session.execute(
                text("""
                INSERT INTO offer_ai_enrichment_batches(id,owner_user_id,scope_json,candidate_count,
                    model,prompt_version,schema_version,state,checkpoint_ordinal,processed_count,
                    applied_count,skipped_count,failed_count)
                VALUES (:id,:owner,'{}',1,'openai/gpt-oss-20b','fixture','fixture',
                    'running',0,0,0,0,0)
            """),
                {"id": work.id, "owner": owner},
            )
            await session.execute(
                text("""
                INSERT INTO offer_ai_enrichment_items(id,batch_id,offer_id,ordinal,
                    input_fingerprint,
                    state,attempt_count)
                VALUES (:item,:batch,:offer,0,'fixture','processing',0)
            """),
                {"item": uuid4(), "batch": work.id, "offer": offer_id},
            )
            if prior_state == "local_limit":
                await session.execute(text("UPDATE ai_provider_accounts SET used=0"))
                await session.execute(
                    text(
                        "UPDATE offer_ai_enrichment_batches "
                        "SET state='paused',failure_category='daily_limit'"
                    )
                )
            if prior_state == "submitted_marker":
                await session.execute(
                    text("UPDATE offer_ai_enrichment_items SET provider_called_at=:now"),
                    {"now": NOW},
                )
            if prior_state == "manual_pause":
                await session.execute(text("UPDATE offer_ai_enrichment_batches SET state='paused'"))
            if prior_state == "uncertain":
                await session.execute(
                    text("""
                    INSERT INTO ai_provider_attempts(id,owner_id,operation_id,work_key,
                        ordinal,state,created_at)
                    VALUES (:id,:owner,:work,'uncertain',1,'uncertain',:now)
                """),
                    {"id": uuid4(), "owner": owner, "work": work.id, "now": NOW},
                )
            if prior_state == "stale":
                await session.execute(
                    text("UPDATE ai_recovery_work SET parser_version='e2-v1' WHERE id=:id"),
                    {"id": work.id},
                )
        assert await queue.reconcile_unsubmitted(uuid4(), NOW) == 0
        restored = await queue.reconcile_unsubmitted(owner, NOW)
        blocked = prior_state in {"uncertain", "submitted_marker", "manual_pause"}
        assert restored == (0 if blocked else 1)
        assert await queue.reconcile_unsubmitted(owner, NOW) == 0
        claimed = await SQLAlchemyRecoveryQueue(db.session_factory).claim(owner, NOW)
        if blocked or prior_state == "stale":
            assert claimed is None
            async with db.session_factory() as session:
                state = await session.scalar(
                    text("SELECT state FROM ai_recovery_work WHERE id=:id"), {"id": work.id}
                )
                assert state == ("terminal" if blocked else "superseded")
            return
        assert claimed is not None
        assert claimed.id == work.id
        assert await queue.defer_provider(claimed, NOW)
        assert await queue.claim(owner, RESET - timedelta(seconds=1)) is None
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT next_eligible_at FROM ai_recovery_work WHERE id=:id"),
                    {"id": work.id},
                )
                == RESET
            )
            assert (
                await session.scalar(
                    text("SELECT count(*) FROM ai_provider_attempts WHERE owner_id=:owner"),
                    {"owner": owner},
                )
                == 0
            )
            assert await session.scalar(
                text("SELECT used FROM ai_provider_accounts WHERE owner_id=:owner"),
                {"owner": owner},
            ) == (0 if prior_state == "local_limit" else 20)
        resumed = await SQLAlchemyRecoveryQueue(db.session_factory).claim(owner, RESET)
        assert resumed is not None
        assert resumed.id == work.id
        budget = SQLAlchemyProviderBudget(db.session_factory)
        attempt = await budget.reserve(
            owner, "first-real-submission", RESET, 20, operation_id=work.id
        )
        await budget.finish(attempt, RESET, None, None)
        assert not await queue.defer_provider(resumed, RESET)
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT count(*) FROM ai_provider_attempts WHERE owner_id=:owner"),
                    {"owner": owner},
                )
                == 1
            )
            assert (
                await session.scalar(
                    text("SELECT used FROM ai_provider_accounts WHERE owner_id=:owner"),
                    {"owner": owner},
                )
                == 1
            )
    finally:
        await db.engine.dispose()
        await _purge()
