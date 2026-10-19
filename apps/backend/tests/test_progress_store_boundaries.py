"""Progress readbacks keep durable waiting and admission evidence visible."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, text, update

from tests.test_archive_recovery_integration import RecoveryDB
from tests.test_archive_recovery_integration import recovery_db as _recovery_db
from tests.test_ingestion_monitoring_integration import progress as _progress
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_media_recovery_integration import canonical, media_payload
from wef_backend.features.ingestion.application.telegram_progress import SweepBatch
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.features.ingestion.infrastructure.models import (
    MediaRecoveryChannelRow,
    MediaRecoveryIntentionRow,
)
from wef_backend.features.ingestion.infrastructure.telegram_progress_store import (
    SQLAlchemyTelegramProgressStore,
)

if TYPE_CHECKING:
    from wef_backend.features.ingestion.infrastructure.ingestion_progress_store import (
        SQLAlchemyIngestionProgressStore,
    )

recovery_db = _recovery_db
progress = _progress


@pytest.mark.parametrize(
    "operation", ["read", "checkpoint", "sweep", "finish", "empty_finish", "defer"]
)
async def test_telegram_progress_missing_rows_are_safe_noops(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None), execute=AsyncMock())
    store = SQLAlchemyTelegramProgressStore(_factory(session))
    monkeypatch.setattr(store, "_locked", AsyncMock(return_value=None))
    if operation == "read":
        result = await store.channel_progress(channel_external_id="fixture")
        assert result.applied_high_water_id == 0
    elif operation == "checkpoint":
        assert (
            await store.advance_live_checkpoint(channel_external_id="fixture", external_id=7) == 0
        )
    elif operation == "sweep":
        assert await store.sweep_batch("fixture", 10) == SweepBatch()
    elif operation == "finish":
        await store.finish_sweep_batch("fixture", SweepBatch((7,), uuid4()), unknown=0)
    elif operation == "empty_finish":
        await store.finish_sweep_batch("fixture", SweepBatch(), unknown=0)
    else:
        await store.defer_source("fixture", seconds=5)
    session.execute.assert_not_awaited()


@pytest.mark.integration
async def test_progress_tracks_undiscovered_sources_and_media_source_wait(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    db = recovery_db
    await canonical(db, media_payload(101))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    assert await store.discover() == 1
    async with db.factory() as session, session.begin():
        # Legacy sources can have work while their discovery intention is absent.
        await session.execute(delete(MediaRecoveryIntentionRow))
        await session.execute(
            update(MediaRecoveryChannelRow).values(
                source_retry_at=datetime.now(UTC) + timedelta(minutes=5),
                scan_after_id=0,
            ),
        )
    await progress.sample()
    status = await progress.status()
    stages = status["snapshot"]["stages"]
    assert stages["media"]["eligible"] == 0
    assert stages["media"]["delayed"] == 1
    assert stages["media_discovery"]["eligible"] == 1


@pytest.mark.integration
async def test_progress_acceptance_reads_samples_since_enabled_instrumentation(
    recovery_db: RecoveryDB,
    progress: SQLAlchemyIngestionProgressStore,
) -> None:
    now = datetime.now(UTC)
    await progress.sample(now)
    async with recovery_db.factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE ingestion_progress_controls SET enabled=true,enabled_at=:start "
                "WHERE channel=:channel"
            ),
            {"start": now - timedelta(minutes=1), "channel": recovery_db.identity.channel_id},
        )
    status = await progress.status()
    assert status["incidents_enabled"] is True
    assert status["acceptance"]["status"] == "unhealthy"
    assert status["acceptance"]["seconds"] == 0
