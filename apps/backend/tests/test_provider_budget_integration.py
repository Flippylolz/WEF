"""Real PostgreSQL races, restart uncertainty, rollover and shared legacy usage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_offer_ai_enrichment_integration import _owner, _seed_offer
from tests.test_persistence_integration import TEST_DATABASE_URL, _prepare
from wef_backend.database import create_database_resources
from wef_backend.features.admin.application.ai_review import ProviderOutcome, ProviderRequestError
from wef_backend.features.admin.infrastructure.provider_budget_store import SQLAlchemyProviderBudget

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required"),
]
NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)


async def test_concurrent_shared_reservation_restart_and_daily_ceiling() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    owner = uuid4()
    budget = SQLAlchemyProviderBudget(db.session_factory)
    try:
        results = await asyncio.gather(
            *(budget.reserve(owner, str(i), NOW, 20) for i in range(10)), return_exceptions=True
        )
        successful = [result for result in results if not isinstance(result, BaseException)]
        assert len(successful) == 1
        await budget.finish(successful[0], NOW, None, None)
        for i in range(1, 20):
            now = NOW + timedelta(minutes=i)
            attempt = await SQLAlchemyProviderBudget(db.session_factory).reserve(
                owner, f"next-{i}", now, 20
            )
            await budget.finish(attempt, now, None, None)
        with pytest.raises(ProviderRequestError) as exhausted:
            await budget.reserve(owner, "over", NOW + timedelta(hours=1), 20)
        assert exhausted.value.retry_at == datetime(2026, 9, 6, tzinfo=UTC)
        async with db.session_factory() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT used,next_eligible_at FROM ai_provider_accounts "
                        "WHERE owner_id=:owner"
                    ),
                    {"owner": owner},
                )
            ).one()
            assert row.used == 20
            assert row.next_eligible_at == exhausted.value.retry_at
            assert await session.scalar(text("SELECT count(*) FROM ai_provider_attempts")) == 20
        attempt = await budget.reserve(owner, "next-day", NOW + timedelta(days=1), 20)
        await budget.finish(attempt, NOW + timedelta(days=1), None, None)
        with pytest.raises(ProviderRequestError) as duplicate:
            await budget.reserve(owner, "next-day", NOW + timedelta(days=1, minutes=5), 20)
        assert duplicate.value.uncertain
    finally:
        await db.engine.dispose()


async def test_uncertain_submission_is_not_repeated_after_lease_expiry() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    owner = uuid4()
    budget = SQLAlchemyProviderBudget(db.session_factory)
    try:
        await budget.reserve(owner, "lost-response", NOW, 20)
        with pytest.raises(ProviderRequestError):
            await budget.reserve(owner, "other", NOW + timedelta(seconds=30), 20)
        with pytest.raises(ProviderRequestError) as uncertain:
            await budget.reserve(owner, "lost-response", NOW + timedelta(minutes=3), 20)
        assert uncertain.value.uncertain
        async with db.session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT state FROM ai_provider_attempts WHERE owner_id=:owner"),
                    {"owner": owner},
                )
                == "uncertain"
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


async def test_rate_limit_and_safe_retry_survive_restart() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    owner = uuid4()
    budget = SQLAlchemyProviderBudget(db.session_factory)
    try:
        attempt = await budget.reserve(owner, "rate", NOW, 20)
        later = NOW + timedelta(days=2)
        error = ProviderRequestError(ProviderOutcome.RATE_LIMITED, retry_at=later)
        await budget.finish(attempt, NOW, error, None)
        for when in (NOW + timedelta(hours=2), NOW + timedelta(days=1)):
            with pytest.raises(ProviderRequestError) as deferred:
                await budget.reserve(owner, "rate", when, 20)
            assert deferred.value.retry_at == later
        retry = await budget.reserve(owner, "rate", later, 20)
        await budget.finish(retry, later, None, None)
        owner = uuid4()
        attempt = await budget.reserve(owner, "server", NOW, 20)
        error = ProviderRequestError(ProviderOutcome.NETWORK, safe_retry=True)
        await budget.finish(attempt, NOW, error, None)
        assert error.retry_at == NOW + timedelta(minutes=1)
        retry = await budget.reserve(owner, "server", NOW + timedelta(minutes=1), 20)
        await budget.finish(
            retry,
            NOW + timedelta(minutes=1),
            ProviderRequestError(ProviderOutcome.NETWORK, safe_retry=True),
            None,
        )
        with pytest.raises(ProviderRequestError):
            await budget.reserve(owner, "server", NOW + timedelta(minutes=3), 20)
    finally:
        await db.engine.dispose()


async def test_preexisting_owner_usage_does_not_reset_on_ledger_adoption() -> None:
    await _prepare()
    assert TEST_DATABASE_URL
    db = create_database_resources(TEST_DATABASE_URL)
    owner = uuid4()
    try:
        owner = await _owner(db)
        _, revision = await _seed_offer(db, "Price: 780000 PLN")
        async with db.session_factory() as session:
            message = await session.scalar(
                text("SELECT source_message_id FROM source_message_revisions WHERE id=:id"),
                {"id": revision},
            )
        # Legacy generation rows must already consume the shared allowance.
        async with db.session_factory.begin() as session:
            for _ in range(20):
                await session.execute(
                    text("""
                    INSERT INTO ingestion_ai_parse_runs(id,owner_user_id,source_message_id,
                        source_message_revision_id,external_message_id,state,model,prompt_version,
                        schema_version,input_fingerprint,source_checksum,proposed_fields,warnings,
                        provider_outcome,created_at,expires_at)
                    VALUES (:id,:owner,:message,:revision,1,'failed','openai/gpt-oss-20b',
                        'fixture','fixture','fixture','fixture','[]','[]','timeout',:now,:expiry)
                """),
                    {
                        "id": uuid4(),
                        "owner": owner,
                        "message": message,
                        "revision": revision,
                        "now": NOW,
                        "expiry": NOW + timedelta(days=1),
                    },
                )
        with pytest.raises(ProviderRequestError):
            await SQLAlchemyProviderBudget(db.session_factory).reserve(owner, "new", NOW, 20)
    finally:
        async with db.session_factory.begin() as session:
            await session.execute(
                text("DELETE FROM ingestion_ai_parse_runs WHERE owner_user_id=:owner"),
                {"owner": owner},
            )
        await db.engine.dispose()
