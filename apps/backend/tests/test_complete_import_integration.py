"""Disposable-PostGIS tests for complete-import leases and provider budgets."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    CompleteImportStage,
    CompleteImportStatus,
)
from wef_backend.features.ingestion.application.persistence import normalized_location_key
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.domain.geocoding import (
    NORMALIZER_VERSION,
    REQUEST_VERSION,
    GeocodeProvider,
)
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


async def test_pending_locations_exclude_unknown_location_sentinel() -> None:
    """The no-address sentinel is never queued for provider geocoding."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    sentinel_id = uuid4()
    address_id = uuid4()
    async with database.session_factory() as session:
        for location_id, display, key in (
            (sentinel_id, "Unknown location", normalized_location_key(None)),
            (
                address_id,
                "ul. Testowa 1, Warszawa",
                normalized_location_key("ul. Testowa 1, Warszawa"),
            ),
        ):
            await session.execute(
                text(
                    "INSERT INTO locations (id, display_name, display_address, "
                    "normalized_address, normalized_address_hash, precision, confidence, "
                    "review_status, out_of_scope) "
                    "VALUES (:id, :display, :display, :normalized, :key, 'unknown', 0, "
                    "'ungeocoded', false)"
                ),
                {
                    "id": str(location_id),
                    "display": display,
                    "normalized": display.casefold(),
                    "key": key,
                },
            )
        await session.commit()
    try:
        pending = await repository.pending_locations()
        assert [item.location_id for item in pending if item.location_id == address_id] == [
            address_id
        ]
        assert all(item.location_id != sentinel_id for item in pending)
        assert all(item.address != "Unknown location" for item in pending)
    finally:
        async with database.session_factory() as session:
            await session.execute(
                text("DELETE FROM locations WHERE id IN (:a, :b)"),
                {"a": str(sentinel_id), "b": str(address_id)},
            )
            await session.commit()
        await database.engine.dispose()


async def test_pending_locations_retry_stale_request_and_out_of_scope() -> None:
    """Stale request_version and out_of_scope needs_review rows re-enter the queue."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    stale_out_of_scope_id = uuid4()
    fresh_out_of_scope_id = uuid4()
    stale_provider_error_id = uuid4()
    result_ids = (uuid4(), uuid4(), uuid4())
    future = datetime.now(UTC) + timedelta(days=7)

    async with database.session_factory() as session:
        for location_id, display, status, out_of_scope in (
            (stale_out_of_scope_id, "ul. Stara 1, Warszawa", "needs_review", True),
            (fresh_out_of_scope_id, "ul. Swieza 2, Warszawa", "needs_review", True),
            (stale_provider_error_id, "ul. Blad 3, Warszawa", "ungeocoded", False),
        ):
            await session.execute(
                text(
                    "INSERT INTO locations (id, display_name, display_address, "
                    "normalized_address, normalized_address_hash, precision, confidence, "
                    "review_status, out_of_scope) "
                    "VALUES (:id, :display, :display, :normalized, :key, 'unknown', 0, "
                    ":status, :out_of_scope)"
                ),
                {
                    "id": str(location_id),
                    "display": display,
                    "normalized": display.casefold(),
                    "key": normalized_location_key(display),
                    "status": status,
                    "out_of_scope": out_of_scope,
                },
            )
        for result_id, request_version, with_point, error_code in (
            (result_ids[0], "forward-geocode-v1", True, None),
            (result_ids[1], REQUEST_VERSION, True, None),
            (result_ids[2], "forward-geocode-v1", False, "no_result"),
        ):
            await session.execute(
                text(
                    "INSERT INTO geocode_results ("
                    "id, query_hash, query_original, query_normalized, normalizer_version, "
                    "scope_version, request_version, provider, precision, confidence, "
                    "within_scope, point, response_json, attribution_text, attempted_at, "
                    "expires_at, error_code"
                    ") VALUES ("
                    ":id, :query_hash, 'ul. Retry', 'ul. retry, warszawa, pl', "
                    ":normalizer_version, 'warsaw-scope-v1', :request_version, 'fixture', "
                    "'unknown', 0, :within_scope, "
                    "CASE WHEN :with_point THEN "
                    "ST_SetSRID(ST_MakePoint(18.65, 54.35), 4326) ELSE NULL END, "
                    "'{}'::jsonb, 'fixture', :attempted_at, :expires_at, :error_code)"
                ),
                {
                    "id": str(result_id),
                    "query_hash": (uuid4().hex + uuid4().hex)[:64],
                    "normalizer_version": NORMALIZER_VERSION,
                    "request_version": request_version,
                    "within_scope": False if with_point else None,
                    "with_point": with_point,
                    "attempted_at": NOW,
                    "expires_at": future,
                    "error_code": error_code,
                },
            )
        for location_id, result_id, reason_code, to_state in (
            (stale_out_of_scope_id, result_ids[0], "out_of_scope", "needs_review"),
            (fresh_out_of_scope_id, result_ids[1], "out_of_scope", "needs_review"),
            (stale_provider_error_id, result_ids[2], "provider_error", "ungeocoded"),
        ):
            await session.execute(
                text(
                    "INSERT INTO location_geocode_selections ("
                    "id, location_id, geocode_result_id, from_state, to_state, reason_code, "
                    "actor_type, review_policy_version, selection_version, decided_at"
                    ") VALUES ("
                    ":id, :location_id, :result_id, 'ungeocoded', :to_state, :reason_code, "
                    "'system', 'warsaw-review-v1', 1, :decided_at)"
                ),
                {
                    "id": str(uuid4()),
                    "location_id": str(location_id),
                    "result_id": str(result_id),
                    "to_state": to_state,
                    "reason_code": reason_code,
                    "decided_at": NOW,
                },
            )
        await session.commit()
    try:
        pending_ids = {item.location_id for item in await repository.pending_locations()}
        assert stale_out_of_scope_id in pending_ids
        assert stale_provider_error_id in pending_ids
        assert fresh_out_of_scope_id not in pending_ids
    finally:
        async with database.session_factory() as session:
            await session.execute(
                text("DELETE FROM location_geocode_selections WHERE location_id IN (:a, :b, :c)"),
                {
                    "a": str(stale_out_of_scope_id),
                    "b": str(fresh_out_of_scope_id),
                    "c": str(stale_provider_error_id),
                },
            )
            await session.execute(
                text("DELETE FROM geocode_results WHERE id IN (:a, :b, :c)"),
                {
                    "a": str(result_ids[0]),
                    "b": str(result_ids[1]),
                    "c": str(result_ids[2]),
                },
            )
            await session.execute(
                text("DELETE FROM locations WHERE id IN (:a, :b, :c)"),
                {
                    "a": str(stale_out_of_scope_id),
                    "b": str(fresh_out_of_scope_id),
                    "c": str(stale_provider_error_id),
                },
            )
            await session.commit()
        await database.engine.dispose()


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
