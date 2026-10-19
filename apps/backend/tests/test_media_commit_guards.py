"""Media commits fence ownership and preserve idempotent object/attempt receipts."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_media_storage import _work
from wef_backend.features.ingestion.domain.media_storage import (
    DerivativeVariant,
    MediaObservation,
    ObservationReason,
    ObservationStatus,
    OriginalDisposition,
    StorageClass,
    StoredObject,
)
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaRecoveryOwnershipLostError,
    SQLAlchemyMediaRepository,
    _disposition_reason,
)


@pytest.mark.parametrize("associated", [False, True])
async def test_media_commit_rechecks_primary_owner_before_association(*, associated: bool) -> None:
    item = replace(_work(associated=associated), recovery_work_id=uuid4(), recovery_token=uuid4())
    source = MagicMock(deleted_at=None, current_revision_id=item.source_message_revision_id)
    session = MagicMock(scalar=AsyncMock(side_effect=[source, MagicMock(), None]))
    if associated:
        with pytest.raises(MediaRecoveryOwnershipLostError):
            await SQLAlchemyMediaRepository.validate_recovery(session, item)
        assert session.scalar.await_count == 3
    else:
        await SQLAlchemyMediaRepository.validate_recovery(session, item)
        assert session.scalar.await_count == 2


async def test_media_object_conflict_requires_a_matching_durable_readback() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None))
    stored = StoredObject(
        StorageClass.RESTRICTED_ORIGINAL, "v1/a/b/file.jpg", "a" * 64, "image/jpeg", 1
    )
    with pytest.raises(RuntimeError, match="deduplication produced no durable row"):
        await SQLAlchemyMediaRepository(MagicMock())._upsert_object(session, stored)  # noqa: SLF001


async def test_unassociated_media_does_not_write_offer_link() -> None:
    session = MagicMock(scalar=AsyncMock())
    await SQLAlchemyMediaRepository(MagicMock())._associate_offer(  # noqa: SLF001
        session,
        _work(associated=False),
        uuid4(),
    )
    session.scalar.assert_not_awaited()
    session.add.assert_not_called()


async def test_missing_original_does_not_write_derivative_attempts() -> None:
    observation = MediaObservation(
        ObservationStatus.UNREAD_REJECTED, ObservationReason.MISSING, "a" * 64, None, None
    )
    session = MagicMock()
    await SQLAlchemyMediaRepository(MagicMock())._record_derivatives(  # noqa: SLF001
        session,
        uuid4(),
        observation,
        (),
        None,
    )
    session.add.assert_not_called()


async def test_duplicate_failed_derivative_attempt_is_not_appended() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=uuid4()))
    await SQLAlchemyMediaRepository(MagicMock())._record_derivative_failure(  # noqa: SLF001
        session,
        uuid4(),
        DerivativeVariant.THUMBNAIL_WEBP_V1,
        "a" * 64,
        ObservationReason.DECODE_FAILED,
    )
    session.add.assert_not_called()


async def test_replayed_unread_recovery_receipt_does_not_invent_asset() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=uuid4()))
    repository = SQLAlchemyMediaRepository(_factory(session))
    item = replace(_work(), recovery_work_id=uuid4(), recovery_token=uuid4())
    observation = MediaObservation(
        ObservationStatus.UNREAD_REJECTED, ObservationReason.MISSING, "a" * 64, None, None
    )
    repository.validate_recovery = AsyncMock()  # type: ignore[method-assign]
    assert await repository.persist_media_result(
        item=item,
        observation=observation,
        disposition=OriginalDisposition.MISSING,
        derivatives=(),
        derivative_failure=None,
    )
    session.add.assert_not_called()


def test_unassociated_disposition_retains_its_distinct_reason() -> None:
    observation = MediaObservation(
        ObservationStatus.UNREAD_REJECTED, ObservationReason.MISSING, "a" * 64, None, None
    )
    assert _disposition_reason(OriginalDisposition.UNASSOCIATED, observation) == "unassociated"
