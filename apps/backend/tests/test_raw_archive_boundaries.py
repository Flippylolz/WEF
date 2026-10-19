"""Archive insert acknowledgment, durable receipts and chunked historical seeding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from tests.test_complete_import_integration import NOW
from tests.test_complete_import_repository_boundaries import import_database
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_offer_ai_enrichment_integration import TEST_DATABASE_URL
from tests.test_persistence_integration import _plain
from wef_backend.features.ingestion.application.archive_retry import MAX_DATA_FAILURES
from wef_backend.features.ingestion.application.persistence import (
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.domain.model import canonical_json_checksum, freeze_json
from wef_backend.features.ingestion.infrastructure.models import (
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)

if TYPE_CHECKING:
    from wef_backend.database import DatabaseResources

__all__ = ["import_database"]


async def test_archive_insert_requires_a_retrievable_acknowledgment() -> None:
    """A conflicted insert with no retained identity cannot return a fabricated event ID."""
    session = MagicMock(scalar=AsyncMock(return_value=None), execute=AsyncMock())
    archive = SQLAlchemyRawEventArchive(_factory(session))
    with pytest.raises(RuntimeError, match="without a retrievable row"):
        await archive.land(
            event_kind="new",
            channel_external_id="synthetic",
            external_message_id=7,
            payload={"id": 7},
            checksum="a" * 64,
        )
    assert session.scalar.await_count == 2


async def test_committed_archive_receipt_allows_acknowledgment_after_retry_exhaustion() -> None:
    """A committed canonical result can be acknowledged without spending another data retry."""
    event_id = uuid4()
    row = TelegramRawEventRow(
        id=event_id,
        processed_at=None,
        data_failure_count=MAX_DATA_FAILURES,
        retry_policy_version="old-policy",
    )
    receipt = TelegramArchiveResolutionRow(
        event_id=event_id, disposition="applied", committed_at=NOW
    )
    session = MagicMock(get=AsyncMock(side_effect=[row, receipt]))
    assert await SQLAlchemyRawEventArchive(_factory(session)).can_attempt(event_id)


async def test_terminal_acknowledgment_of_unknown_event_is_a_noop() -> None:
    """A missing archive ID cannot increment observations for an invented channel."""
    result = MagicMock(rowcount=0)
    session = MagicMock(execute=AsyncMock(return_value=result), scalar=AsyncMock(return_value=None))
    assert not await SQLAlchemyRawEventArchive(_factory(session)).mark_attempt(
        uuid4(), outcome="processed"
    )
    session.execute.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
@pytest.mark.parametrize("chunk_size", [1, 10])
async def test_historical_seed_skips_malformed_text_and_retains_original_mixed_payload(
    chunk_size: int, import_database: DatabaseResources
) -> None:
    """Chunk boundaries never flatten retained source bytes or count malformed rows as seeded."""
    source = replace(
        _plain(1, "synthetic", "a" * 64).raw.source, channel_id=f"archive-seed-{uuid4()}"
    )
    inputs = []
    payloads = [
        {
            "id": 1,
            "text": ["synthetic ", {"text": "mixed"}],
            "text_entities": [{"type": "bold", "text": "mixed"}],
        },
        {"id": 2, "text": "synthetic plain"},
        {"id": 3, "text": ["synthetic ", {"text": 3}]},
        {"id": 4, "text": 3},
    ]
    for index, payload in enumerate(payloads, start=1):
        frozen = freeze_json(payload)
        assert isinstance(frozen, Mapping)
        persistable = _plain(index, "synthetic", canonical_json_checksum(payload))
        inputs.append(
            replace(persistable, raw=replace(persistable.raw, source=source, raw_payload=frozen))
        )
    try:
        await PersistHistoricalIngestion(
            SQLAlchemyIngestionPersistence(import_database.session_factory)
        )(
            channel=source,
            messages=inputs,
            metadata=RunMetadata(parser_version="legacy-seed"),
        )
        archive = SQLAlchemyRawEventArchive(import_database.session_factory)
        assert await archive.seed_from_history(chunk_size=chunk_size) == (2, 2)
        async with import_database.session_factory() as session:
            rows = (
                await session.scalars(
                    select(TelegramRawEventRow)
                    .where(TelegramRawEventRow.channel_external_id == source.channel_id)
                    .order_by(TelegramRawEventRow.external_message_id)
                )
            ).all()
            assert [row.external_message_id for row in rows] == [1, 2]
            assert rows[0].payload_json == payloads[0]
            assert rows[0].checksum == canonical_json_checksum(payloads[0])
        assert await archive.seed_from_history(chunk_size=chunk_size) == (0, 2)
    finally:
        async with import_database.session_factory.begin() as session:
            await session.execute(
                delete(TelegramRawEventRow).where(
                    TelegramRawEventRow.channel_external_id == source.channel_id
                )
            )
