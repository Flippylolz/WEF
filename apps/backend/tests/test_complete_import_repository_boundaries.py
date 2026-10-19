"""Real import planning/reconciliation queries and fenced lease failure boundaries."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete

from tests.test_complete_import_integration import NOW
from tests.test_offer_ai_enrichment_integration import TEST_DATABASE_URL, _prepare
from tests.test_persistence_integration import _candidate
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    CompleteImportStage,
    CompleteImportStatus,
)
from wef_backend.features.ingestion.application.media_grouping import GROUPING_VERSION
from wef_backend.features.ingestion.application.persistence import (
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    ImportVerification,
    SQLAlchemyCompleteImportRepository,
    StaleCompleteImportLeaseError,
)
from wef_backend.features.ingestion.infrastructure.models import (
    CompleteImportRunRow,
    MediaDispositionAttemptRow,
    SourceMessageParseIssueRow,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from wef_backend.database import DatabaseResources


@pytest.fixture
async def import_database() -> AsyncIterator[DatabaseResources]:
    database = await _prepare()
    try:
        yield database
    finally:
        async with database.session_factory.begin() as session:
            await session.execute(delete(MediaDispositionAttemptRow))
            await session.execute(delete(SourceMessageParseIssueRow))
            await session.execute(delete(CompleteImportRunRow))
        await database.engine.dispose()
        # Other integration suites also own this disposable database. Leave no
        # canonical catalog/source rows for their independent setup assumptions.
        cleaned = await _prepare()
        await cleaned.engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_planning_queries_distinguish_missing_channel_from_current_source(
    import_database: DatabaseResources,
) -> None:
    """Read-only planning never creates state; persisted anchors/replay keys match exactly."""
    database = import_database
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    candidate = _candidate(1, "Mieszkanie 40 m² cena 560 000 zł", "b" * 64)
    channel = candidate.raw.source
    assert await repository.resolve_source_channel_id(channel) is None
    assert await repository.existing_source_checksums(channel) == {}
    assert await repository.source_anchors(channel) == {}
    assert await repository.existing_media_replays(channel) == set()
    assert await repository.verify(channel, uuid4()) == ImportVerification(
        0, 0, 0, 0, 0, 0, 0, 0, 0
    )
    result = await PersistHistoricalIngestion(
        SQLAlchemyIngestionPersistence(database.session_factory)
    )(
        channel=channel,
        messages=(candidate,),
        metadata=RunMetadata(parser_version="integration@1"),
    )
    assert await repository.resolve_source_channel_id(channel) is not None
    assert await repository.existing_source_checksums(channel) == {1: "b" * 64}
    anchors = await repository.source_anchors(channel)
    assert set(anchors) == {1}
    source = anchors[1]
    assert source.offer_id is not None
    async with database.session_factory.begin() as session:
        session.add(
            MediaDispositionAttemptRow(
                id=uuid4(),
                source_message_id=source.source_message_id,
                source_ordinal=0,
                source_message_revision_id=source.revision_id,
                source_descriptor_identity="c" * 64,
                observation_status="unread_unavailable",
                observation_reason_code="missing_path",
                observed_checksum_sha256=None,
                observed_byte_size=None,
                content_identity="unread:synthetic",
                attempt_number=1,
                verifier_version="test-v1",
                association_version=GROUPING_VERSION,
                disposition="missing",
                reason_code="missing_path",
                media_asset_id=None,
                attempted_at=NOW,
            )
        )
    assert await repository.existing_media_replays(channel) == {
        (
            source.source_message_id,
            0,
            source.revision_id,
            "c" * 64,
            GROUPING_VERSION,
        )
    }
    verification = await repository.verify(channel, result.run_id)
    assert verification.source_messages == verification.source_revisions == verification.offers == 1
    assert verification.locations == 1
    assert (
        verification.accepted_locations
        == verification.media_assets
        == verification.media_derivatives
        == verification.provider_attempts
        == 0
    )
    assert verification.media_dispositions == 1


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_recurring_geocode_sentinel_is_reused_only_for_matching_pipeline(
    import_database: DatabaseResources,
) -> None:
    """Resumed ticks share one ledger run; a changed pipeline receives a new identity."""
    database = import_database
    persistence = SQLAlchemyIngestionPersistence(database.session_factory)
    channel_id = await persistence.ensure_channel(
        platform="telegram", external_id="recurring-boundary", display_name="Synthetic"
    )
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    first = await repository.recurring_geocode_run_id(
        source_channel_id=channel_id, pipeline_version=PIPELINE_VERSION, now=NOW
    )
    assert (
        await repository.recurring_geocode_run_id(
            source_channel_id=channel_id,
            pipeline_version=PIPELINE_VERSION,
            now=NOW + timedelta(seconds=1),
        )
        == first
    )
    assert (
        await repository.recurring_geocode_run_id(
            source_channel_id=channel_id, pipeline_version="next-pipeline", now=NOW
        )
        != first
    )
    reservation = await repository.reserve_provider_attempt(
        run_id=first,
        provider=GeocodeProvider.GEOAPIFY,
        account_identity="synthetic-repository-boundary",
        query_hash="a" * 64,
        daily_limit=10,
        minimum_interval=timedelta(seconds=1),
        now=NOW,
    )
    assert reservation is not None
    await repository.complete_provider_attempt(
        reservation.attempt_id, status="succeeded", error_code=None, completed_at=NOW
    )
    channel = replace(
        _candidate(1, "Mieszkanie 40 m²", "b" * 64).raw.source, channel_id="recurring-boundary"
    )
    assert (await repository.verify(channel, first)).provider_attempts == 1


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_stale_owner_cannot_checkpoint_or_release_taken_over_run(
    import_database: DatabaseResources,
) -> None:
    """Both mutation endpoints enforce the same fencing token after lease takeover."""
    database = import_database
    channel_id = await SQLAlchemyIngestionPersistence(database.session_factory).ensure_channel(
        platform="telegram", external_id="fenced-boundary", display_name="Synthetic"
    )
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    first = await repository.claim_run(
        source_channel_id=channel_id,
        source_checksum="a" * 64,
        source_size=1,
        pipeline_version=PIPELINE_VERSION,
        owner_id="first",
        stage=CompleteImportStage.PERSISTENCE,
        now=NOW,
        lease_duration=timedelta(seconds=1),
    )
    second = await repository.claim_run(
        source_channel_id=channel_id,
        source_checksum="a" * 64,
        source_size=1,
        pipeline_version=PIPELINE_VERSION,
        owner_id="second",
        stage=CompleteImportStage.GEOCODE,
        now=NOW + timedelta(seconds=2),
        lease_duration=timedelta(minutes=1),
    )
    assert second.fencing_token > first.fencing_token
    with pytest.raises(StaleCompleteImportLeaseError):
        await repository.checkpoint_run(
            first,
            stage=CompleteImportStage.VERIFY,
            status=CompleteImportStatus.SUCCEEDED,
            checkpoint={},
            counts={},
            now=NOW,
            lease_duration=timedelta(minutes=1),
        )
    with pytest.raises(StaleCompleteImportLeaseError):
        await repository.release_run(first, now=NOW)
    released = await repository.release_run(second, now=NOW + timedelta(seconds=3))
    assert released.status is CompleteImportStatus.PAUSED
    assert released.owner_id == "second"


@pytest.mark.parametrize("operation", ["claim", "recurring"])
async def test_insert_readback_disappearance_fails_closed(operation: str) -> None:
    """An unacknowledged database identity cannot escape as a valid import lease."""
    session = MagicMock(scalar=AsyncMock(return_value=None))
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    context = MagicMock(
        __aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock(return_value=None)
    )
    repository = SQLAlchemyCompleteImportRepository(MagicMock(return_value=context))
    if operation == "claim":
        with pytest.raises(RuntimeError, match="disappeared during claim"):
            await repository.claim_run(
                source_channel_id=uuid4(),
                source_checksum="a" * 64,
                source_size=1,
                pipeline_version=PIPELINE_VERSION,
                owner_id="synthetic",
                stage=CompleteImportStage.PERSISTENCE,
                now=NOW,
                lease_duration=timedelta(seconds=1),
            )
    else:
        with pytest.raises(RuntimeError, match="disappeared during ensure"):
            await repository.recurring_geocode_run_id(
                source_channel_id=uuid4(), pipeline_version=PIPELINE_VERSION, now=NOW
            )
    assert session.scalar.await_count == 2
