"""Recovery acquisition, outcome classification and malformed discovery boundaries."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from tests.test_archive_recovery_integration import NOW, RecoveryDB
from tests.test_archive_recovery_integration import recovery_db as _recovery_db
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_listing_extraction import _message
from tests.test_media_recovery_integration import canonical, media_payload
from tests.test_media_storage import _descriptor, _storage, _work
from wef_backend.features.ingestion.application.media_grouping import StatefulMediaGrouper
from wef_backend.features.ingestion.application.media_recovery import (
    MediaClaim,
    MediaSourceUnprovenError,
    MediaUnsupportedError,
)
from wef_backend.features.ingestion.application.media_storage import MediaProcessResult
from wef_backend.features.ingestion.domain.media_storage import (
    MediaObservation,
    ObservationReason,
    OriginalDisposition,
    descriptor_identity,
)
from wef_backend.features.ingestion.infrastructure import media_recovery_execution as execution
from wef_backend.features.ingestion.infrastructure.media_recovery_discovery import (
    _discover_revision,
    _seed_explicit,
    decode_media_source,
    discover_media,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaRecoveryOwnershipLostError,
)
from wef_backend.features.ingestion.infrastructure.models import (
    MediaRecoveryIntentionRow,
    SourceChannelRow,
    SourceMessageRow,
)

recovery_db = _recovery_db

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("reason", "failure", "expected"),
    [
        (ObservationReason.MISSING, None, OSError),
        (ObservationReason.STORAGE_FAILED, None, OSError),
        (ObservationReason.CHANGED_DURING_READ, None, OSError),
        (ObservationReason.VERIFIED, ObservationReason.STORAGE_FAILED, OSError),
        (ObservationReason.VERIFIED, ObservationReason.DECODE_FAILED, ValueError),
        (ObservationReason.UNSUPPORTED_DESCRIPTOR, None, None),
    ],
)
def test_recovery_distinguishes_transient_storage_from_unsupported_media(
    reason: ObservationReason, failure: ObservationReason | None, expected: type[Exception] | None
) -> None:
    """Transient I/O stays retryable; unsupported bytes receive a terminal media-only outcome."""
    observation = MagicMock(spec=MediaObservation, reason=reason)
    result = MediaProcessResult(
        OriginalDisposition.REJECTED, observation, (), failure, replayed=False
    )
    if expected is not None:
        with pytest.raises(expected, match="media"):
            execution._outcome(result)  # noqa: SLF001 - stable recovery classification
    else:
        assert execution._outcome(result).state == "unsupported"  # noqa: SLF001 - stable classification


def test_reacquired_filesystem_rejects_another_intended_descriptor(tmp_path: Path) -> None:
    filesystem = _storage(tmp_path)
    intended = _descriptor()
    wrapper = execution._RecoveryFilesystem(filesystem, intended, descriptor_identity(intended))  # noqa: SLF001 - acquisition adapter
    with pytest.raises(MediaSourceUnprovenError):
        wrapper.observe_and_store(replace(intended, path="other.jpg"))


@pytest.mark.parametrize("mode", ["unsupported", "unproven", "ownership", "completed"])
async def test_recovery_acquisition_releases_owned_download_after_processing(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Source refusal and ownership loss cannot leak staging or affect canonical ingestion."""
    filesystem = _storage(tmp_path)
    descriptor = _descriptor()
    work = replace(_work(), source_ordinal=0, descriptor=descriptor)
    claim = MediaClaim(uuid4(), uuid4(), uuid4(), _message("synthetic media"), work, None)
    source, lease = MagicMock(), MagicMock()
    source.acquire_media = AsyncMock(
        return_value=(replace(descriptor, path="downloaded.jpg"), lease)
    )
    if mode == "unsupported":
        source.acquire_media.side_effect = MediaUnsupportedError()
    elif mode == "unproven":
        source.acquire_media.side_effect = MediaSourceUnprovenError()
    monkeypatch.setattr(execution.RecoverStoredMedia, "_original", AsyncMock(return_value=None))
    observation = MagicMock(spec=MediaObservation, reason=ObservationReason.VERIFIED)
    processor = AsyncMock(
        return_value=MediaProcessResult(
            OriginalDisposition.STORED, observation, (), None, replayed=False
        )
    )
    if mode == "ownership":
        processor.side_effect = MediaRecoveryOwnershipLostError()
    monkeypatch.setattr(execution, "ProcessMedia", lambda _filesystem, _repository: processor)
    result = await execution.RecoverStoredMedia(MagicMock(), filesystem, source)(claim)
    expected = {
        "unsupported": "unsupported",
        "unproven": "quarantined",
        "ownership": "superseded",
        "completed": "completed",
    }
    assert result.state == expected[mode]
    assert lease.release.call_count == int(mode in {"ownership", "completed"})
    source.acquire_media.assert_awaited_once_with(claim.raw, 0)
    if mode in {"ownership", "completed"}:
        assert processor.await_args is not None
        submitted = processor.await_args.args[0]
        assert submitted.recovery_work_id == claim.id
        assert submitted.recovery_token == claim.token
        assert submitted.descriptor == descriptor


@pytest.mark.parametrize("payload", [{}, {"id": 1, "type": "unsupported"}])
def test_media_discovery_refuses_malformed_canonical_records(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="canonical media source is malformed"):
        decode_media_source(payload, _message("synthetic").source)


@pytest.mark.parametrize("mode", ["missing_channel", "missing_state"])
async def test_media_discovery_requires_durable_channel_and_state(mode: str) -> None:
    session = MagicMock(
        scalar=AsyncMock(
            side_effect=[None]
            if mode == "missing_channel"
            else [SourceChannelRow(id=uuid4()), None]
        ),
        execute=AsyncMock(),
    )
    if mode == "missing_channel":
        assert await discover_media(_factory(session), "synthetic", 10) == 0
        session.execute.assert_not_awaited()
    else:
        with pytest.raises(RuntimeError, match="discovery state missing"):
            await discover_media(_factory(session), "synthetic", 10)


@pytest.mark.parametrize("mode", ["missing_intention", "invalid_payload", "deleted"])
async def test_discovery_revision_requires_an_intention_and_resets_deleted_boundaries(
    mode: str,
) -> None:
    raw = _message("synthetic")
    source = SourceMessageRow(
        id=uuid4(),
        source_channel_id=uuid4(),
        external_message_id=7,
        current_revision_id=uuid4(),
        raw_payload_json=[] if mode == "invalid_payload" else media_payload(7),
        deleted_at=raw.published_at if mode == "deleted" else None,
    )
    intention = MediaRecoveryIntentionRow(discovered=False)
    session = MagicMock(
        execute=AsyncMock(),
        get=AsyncMock(return_value=None if mode == "missing_intention" else intention),
    )
    grouper = StatefulMediaGrouper()
    grouper.seed_anchor(9)
    if mode == "missing_intention":
        with pytest.raises(RuntimeError, match="intention missing"):
            await _discover_revision(session, raw.source, source, grouper)
    elif mode == "invalid_payload":
        with pytest.raises(TypeError, match="payload is invalid"):
            await _discover_revision(session, raw.source, source, grouper)
    else:
        await _discover_revision(session, raw.source, source, grouper)
        assert intention.discovered
        assert grouper.continuation() == StatefulMediaGrouper().continuation()


@pytest.mark.parametrize("kind", ["album", "reply"])
async def test_unknown_explicit_album_does_not_seed_an_invented_owner(kind: str) -> None:
    raw = replace(
        _message("synthetic"),
        media_group_id="unknown-album" if kind == "album" else None,
        reply_to_message_id=999 if kind == "reply" else None,
    )
    source = SourceMessageRow(
        source_channel_id=uuid4(), external_message_id=raw.external_message_id
    )
    grouper = StatefulMediaGrouper()
    before = grouper.continuation()
    session = MagicMock(scalar=AsyncMock(return_value=None))
    await _seed_explicit(session, source, raw, grouper)
    assert grouper.continuation() == before
    session.scalar.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("TEST_DATABASE_URL") is None, reason="PostGIS required")
@pytest.mark.parametrize("legacy_context", [False, True])
async def test_revised_attachment_discovery_reuses_retained_context_after_watermark(
    recovery_db: RecoveryDB,
    *,
    legacy_context: bool,
) -> None:
    data = media_payload(1)
    data["text"] = "synthetic non-listing attachment"
    await canonical(recovery_db, data)
    store = SQLAlchemyMediaRecoveryStore(recovery_db.factory, recovery_db.identity.channel_id)
    assert await store.discover() == 1
    if legacy_context:
        async with recovery_db.factory.begin() as session:
            await session.execute(update(MediaRecoveryIntentionRow).values(context_json=[]))
    data = {
        **data,
        "text": "synthetic changed attachment",
        "edited_unixtime": str(int(NOW.timestamp()) + 1),
    }
    await canonical(recovery_db, data)
    async with recovery_db.factory() as session:
        current = await session.scalar(select(SourceMessageRow.current_revision_id))
    assert current is not None
    assert await store.discover() == 1
    async with recovery_db.factory() as session:
        intention = await session.get(MediaRecoveryIntentionRow, current)
        assert intention is not None
        assert intention.discovered
        assert isinstance(intention.context_json, dict)
