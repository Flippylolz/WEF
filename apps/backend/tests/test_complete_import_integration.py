"""Disposable-PostGIS tests for complete-import leases and provider budgets."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    CompleteImportStage,
    CompleteImportStatus,
)
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    CompleteImportLeaseHeldError,
    SQLAlchemyCompleteImportRepository,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]

NOW = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
CHANNEL = SourceIdentity(
    SourcePlatform.TELEGRAM,
    "complete-import-test",
    "Complete Import Test",
    "public_channel",
)


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )


async def test_run_lease_pause_takeover_and_durable_provider_budget() -> None:
    """Fence active owners and cap/space provider slots across resumptions."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    persistence = SQLAlchemyIngestionPersistence(database.session_factory)
    channel_id = await persistence.ensure_channel(
        platform=CHANNEL.platform.value,
        external_id=CHANNEL.channel_id,
        display_name=CHANNEL.channel_name,
    )
    checksum = "a" * 64
    try:
        first = await repository.claim_run(
            source_channel_id=channel_id,
            source_checksum=checksum,
            source_size=100,
            pipeline_version=PIPELINE_VERSION,
            owner_id="owner-one",
            stage=CompleteImportStage.PERSISTENCE,
            now=NOW,
            lease_duration=timedelta(minutes=5),
        )
        with pytest.raises(CompleteImportLeaseHeldError):
            await repository.claim_run(
                source_channel_id=channel_id,
                source_checksum=checksum,
                source_size=100,
                pipeline_version=PIPELINE_VERSION,
                owner_id="owner-two",
                stage=CompleteImportStage.PERSISTENCE,
                now=NOW + timedelta(seconds=1),
                lease_duration=timedelta(minutes=5),
            )
        await repository.checkpoint_run(
            first,
            stage=CompleteImportStage.GEOCODE,
            status=CompleteImportStatus.PAUSED,
            checkpoint={"locations": 3},
            counts={"remaining": 2},
            now=NOW + timedelta(seconds=2),
            lease_duration=timedelta(minutes=5),
            pause_reason="operator_batch_limit",
            next_eligible_at=NOW + timedelta(seconds=2),
        )
        resumed = await repository.claim_run(
            source_channel_id=channel_id,
            source_checksum=checksum,
            source_size=100,
            pipeline_version=PIPELINE_VERSION,
            owner_id="owner-two",
            stage=CompleteImportStage.GEOCODE,
            now=NOW + timedelta(seconds=3),
            lease_duration=timedelta(minutes=5),
        )
        assert resumed.fencing_token == first.fencing_token + 1

        released = await repository.release_run(
            resumed,
            now=NOW + timedelta(seconds=4),
        )
        assert released.status is CompleteImportStatus.PAUSED
        resumed = await repository.claim_run(
            source_channel_id=channel_id,
            source_checksum=checksum,
            source_size=100,
            pipeline_version=PIPELINE_VERSION,
            owner_id="owner-three",
            stage=CompleteImportStage.GEOCODE,
            now=NOW + timedelta(seconds=4),
            lease_duration=timedelta(minutes=5),
        )
        assert resumed.fencing_token == released.fencing_token + 1

        one = await repository.reserve_provider_attempt(
            run_id=resumed.run_id,
            provider=GeocodeProvider.GEOAPIFY,
            account_identity="integration-test",
            query_hash="b" * 64,
            daily_limit=2,
            minimum_interval=timedelta(milliseconds=250),
            now=NOW,
        )
        two = await repository.reserve_provider_attempt(
            run_id=resumed.run_id,
            provider=GeocodeProvider.GEOAPIFY,
            account_identity="integration-test",
            query_hash="c" * 64,
            daily_limit=2,
            minimum_interval=timedelta(milliseconds=250),
            now=NOW,
        )
        blocked = await repository.reserve_provider_attempt(
            run_id=resumed.run_id,
            provider=GeocodeProvider.GEOAPIFY,
            account_identity="integration-test",
            query_hash="d" * 64,
            daily_limit=2,
            minimum_interval=timedelta(milliseconds=250),
            now=NOW,
        )
        assert one is not None
        assert two is not None
        assert two.not_before - one.not_before == timedelta(milliseconds=250)
        assert blocked is None
        await repository.complete_provider_attempt(
            one.attempt_id,
            status="succeeded",
            error_code=None,
            completed_at=NOW + timedelta(seconds=1),
        )

        async with database.session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT used_attempts, "
                        "(SELECT count(*) FROM provider_attempts "
                        " WHERE complete_import_run_id = :run_id) "
                        "FROM provider_daily_budgets "
                        "WHERE account_identity = 'integration-test'"
                    ),
                    {"run_id": resumed.run_id},
                )
            ).one()
        assert tuple(rows) == (2, 2)
    finally:
        async with database.session_factory() as session:
            await session.execute(
                text(
                    "DELETE FROM provider_attempts WHERE complete_import_run_id IN "
                    "(SELECT id FROM complete_import_runs WHERE source_channel_id = :channel_id)"
                ),
                {"channel_id": channel_id},
            )
            await session.execute(
                text(
                    "DELETE FROM provider_daily_budgets WHERE account_identity = 'integration-test'"
                ),
            )
            await session.execute(
                text("DELETE FROM complete_import_runs WHERE source_channel_id = :channel_id"),
                {"channel_id": channel_id},
            )
            await session.execute(
                text("DELETE FROM source_channels WHERE id = :channel_id"),
                {"channel_id": channel_id},
            )
            await session.commit()
        await database.engine.dispose()
