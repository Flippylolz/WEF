"""Archive identity, retained deletion evidence and equal-version recovery boundaries."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_archive_recovery_integration import NOW, payload
from wef_backend.features.ingestion.application.telegram_events import RawEventRecord
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel
from wef_backend.features.ingestion.domain.model import canonical_json_checksum
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.archive_evidence import (
    ArchiveEvidenceError,
    ensure_tombstone,
    flatten_legacy_payload,
    legacy_projection_checksums,
    proven_payload,
    retained_delete,
    source_disposition,
    write_resolution,
)
from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    SourceMessageRow,
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import _flatten_text


@pytest.mark.parametrize("invalid", [3, {"text": 3}, {"other": "unquoted"}])
def test_legacy_text_must_remain_reconstructible(invalid: object) -> None:
    """Invalid mixed text cannot seed unverifiable history or bypass provenance checks."""
    data = {"text": ["quoted ", invalid]}
    assert _flatten_text(data) is None
    with pytest.raises(ArchiveEvidenceError, match="invalid legacy text"):
        flatten_legacy_payload(data)
    assert _flatten_text({"text": invalid}) is None


def test_legacy_projection_preserves_edit_and_album_identity() -> None:
    """Historical projection hashes include source time and album ID, never private extras."""
    original = payload(7, edit=1)
    original["media_group_id"] = 88
    expected = {
        "id": 7,
        "type": "message",
        "date_unixtime": str(original["date_unixtime"]),
        "text": "synthetic record 1",
        "from_live": True,
        "edited_unixtime": str(original["edited_unixtime"]),
        "media_group_id": "88",
    }
    assert canonical_json_checksum(expected) in legacy_projection_checksums(original)
    assert flatten_legacy_payload(expected) == expected
    flattened = _flatten_text(original)
    assert flattened is not None
    assert flattened["text"] == "synthetic record 1"


@pytest.mark.parametrize("changed", ["absent", "channel", "message", "kind", "checksum", "payload"])
async def test_proven_archive_payload_rejects_any_changed_retained_identity(changed: str) -> None:
    """Callers cannot substitute a payload or metadata under another archive ID."""
    data = payload(7)
    record = RawEventRecord(
        uuid4(), "new", "synthetic", 7, data, NOW, 0, canonical_json_checksum(data)
    )
    values: dict[str, object] = {
        "id": record.id,
        "channel_external_id": record.channel_external_id,
        "external_message_id": 7,
        "event_kind": "new",
        "checksum": record.checksum,
        "payload_json": data,
    }
    field = {
        "channel": "channel_external_id",
        "message": "external_message_id",
        "kind": "event_kind",
        "checksum": "checksum",
        "payload": "payload_json",
    }.get(changed)
    if field is not None:
        values[field] = {"changed": True} if changed == "payload" else "different"
    session = MagicMock(
        get=AsyncMock(return_value=None if changed == "absent" else TelegramRawEventRow(**values))
    )
    with pytest.raises(ArchiveEvidenceError, match="differs from retained identity"):
        await proven_payload(session, record)
    session.scalars.assert_not_called()


async def test_legacy_payload_search_skips_nonmatching_revision_proof() -> None:
    """Only the retained exact checksum plus known flattening transform can recover bytes."""
    original = payload(7)
    flattened = flatten_legacy_payload(original)
    record = RawEventRecord(
        uuid4(), "new", "synthetic", 7, flattened, NOW, 0, canonical_json_checksum(original)
    )
    stored = TelegramRawEventRow(
        id=record.id,
        channel_external_id="synthetic",
        external_message_id=7,
        event_kind="new",
        checksum=record.checksum,
        payload_json=flattened,
    )
    session = MagicMock(
        get=AsyncMock(return_value=stored), scalars=AsyncMock(return_value=[payload(8), original])
    )
    assert await proven_payload(session, record) == original


async def test_missing_tombstone_readback_fails_closed() -> None:
    """A failed insert/readback cannot certify a committed deletion."""
    session = MagicMock(execute=AsyncMock(), scalar=AsyncMock(return_value=None))
    with pytest.raises(ArchiveEvidenceError, match="missing committed deletion evidence"):
        await ensure_tombstone(session, uuid4(), 7, NOW)


@pytest.mark.parametrize("valid_delete", [False, True])
async def test_retained_delete_ignores_invalid_ids_and_checksums(*, valid_delete: bool) -> None:
    """Boolean IDs and unproven archive checksums cannot create tombstones."""
    rows = [
        TelegramRawEventRow(
            payload_json={"id": True},
            checksum=canonical_json_checksum({"id": True}),
            received_at=NOW,
        ),
        TelegramRawEventRow(payload_json={"id": 1}, checksum="wrong", received_at=NOW),
    ]
    if valid_delete:
        rows.append(
            TelegramRawEventRow(
                payload_json={"id": 1}, checksum=canonical_json_checksum({"id": 1}), received_at=NOW
            )
        )
    session = MagicMock(
        scalars=AsyncMock(return_value=rows),
        scalar=AsyncMock(return_value=uuid4()),
        execute=AsyncMock(),
    )
    assert await retained_delete(session, uuid4(), 1) is valid_delete
    assert session.execute.await_count == int(valid_delete)


async def test_existing_deletion_is_promoted_to_durable_tombstone() -> None:
    """A legacy deleted source cannot become live again when the explicit tombstone is absent."""
    raw = decode_archived_payload(
        payload(7), source_identity_from_channel(default_live_channel_identity())
    )
    existing = SourceMessageRow(deleted_at=NOW)
    session = MagicMock(scalar=AsyncMock(side_effect=[None, uuid4()]), execute=AsyncMock())
    assert (
        await source_disposition(
            session, channel_id=uuid4(), existing=existing, raw=raw, enforce_order=True
        )
        == "deleted"
    )
    session.execute.assert_awaited_once()


@pytest.mark.parametrize("newer_retained", [False, True])
async def test_original_recovery_checks_for_newer_retained_versions(
    *, newer_retained: bool
) -> None:
    """Rehydrating a legacy projection cannot roll back a retained newer source version."""
    original = payload(7)
    legacy = {
        "id": 7,
        "type": "message",
        "date_unixtime": original["date_unixtime"],
        "text": flatten_legacy_payload(original)["text"],
        "from_live": True,
    }
    raw = decode_archived_payload(
        original, source_identity_from_channel(default_live_channel_identity())
    )
    existing = SourceMessageRow(
        id=uuid4(),
        deleted_at=None,
        raw_checksum=canonical_json_checksum(legacy),
        published_at=raw.published_at,
        edited_at=None,
        raw_payload_json=legacy,
    )
    session = MagicMock(
        scalar=AsyncMock(side_effect=[None, uuid4(), uuid4() if newer_retained else None]),
        scalars=AsyncMock(return_value=[]),
    )
    if newer_retained:
        with pytest.raises(ArchiveEvidenceError, match="conflicting source revisions"):
            await source_disposition(
                session, channel_id=uuid4(), existing=existing, raw=raw, enforce_order=True
            )
    else:
        assert (
            await source_disposition(
                session, channel_id=uuid4(), existing=existing, raw=raw, enforce_order=True
            )
            is None
        )


@pytest.mark.parametrize("mismatch", ["event", "channel", "channel_id", "message_id"])
async def test_canonical_receipt_requires_exact_event_channel_and_message(mismatch: str) -> None:
    """Canonical commits cannot acknowledge an unrelated raw event."""
    event = TelegramRawEventRow(channel_external_id="synthetic", external_message_id=7)
    channel = SourceChannelRow(external_id="synthetic")
    if mismatch == "channel_id":
        channel.external_id = "other"
    elif mismatch == "message_id":
        event.external_message_id = 8
    session = MagicMock(
        get=AsyncMock(
            side_effect=[
                None,
                None if mismatch == "event" else event,
                None if mismatch == "channel" else channel,
            ]
        )
    )
    with pytest.raises(ArchiveEvidenceError, match="receipt identity mismatch"):
        await write_resolution(
            session, event_id=uuid4(), channel_id=uuid4(), external_id=7, disposition="applied"
        )
    session.add.assert_not_called()


async def test_canonical_receipt_replay_returns_the_committed_proof() -> None:
    """An already committed receipt is reused without writing a second decision."""
    receipt = TelegramArchiveResolutionRow(
        event_id=uuid4(), disposition="deleted", committed_at=NOW
    )
    session = MagicMock(get=AsyncMock(return_value=receipt))
    result = await write_resolution(
        session, event_id=receipt.event_id, channel_id=uuid4(), external_id=7, disposition="applied"
    )
    assert result.disposition == "deleted"
    assert result.committed_at == NOW
    session.add.assert_not_called()
