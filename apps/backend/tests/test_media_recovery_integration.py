"""Real transaction proofs for durable media intentions and lease/retry recovery."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from sqlalchemy import func, select, update

from tests.test_archive_recovery_integration import RecoveryDB
from tests.test_archive_recovery_integration import payload as historical_payload
from tests.test_archive_recovery_integration import recovery_db as _recovery_db
from wef_backend.features.ingestion.application.archive_retry import ArchiveFailure
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.media_recovery import MediaRecoveryOutcome
from wef_backend.features.ingestion.application.media_storage import ProcessMedia
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    RunCheckpoint,
    RunCounts,
    RunMode,
)
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel
from wef_backend.features.ingestion.domain.media_storage import ObservationReason
from wef_backend.features.ingestion.infrastructure.media_filesystem import (
    LocalMediaStorage,
    MediaDerivativeError,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_execution import (
    RecoverStoredMedia,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaRecoveryOwnershipLostError,
    SQLAlchemyMediaRepository,
)
from wef_backend.features.ingestion.infrastructure.models import (
    MediaDerivativeRow,
    MediaDispositionAttemptRow,
    MediaRecoveryChannelRow,
    MediaRecoveryIntentionRow,
    MediaRecoveryWorkRow,
    OfferMediaRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from pathlib import Path

    from wef_backend.features.ingestion.application.telegram_live import MediaLease
    from wef_backend.features.ingestion.domain.media_storage import (
        MediaObservation,
        PublicDerivative,
        VerifiedOriginal,
    )
    from wef_backend.features.ingestion.domain.model import MediaDescriptor, RawMessage

recovery_db = _recovery_db
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TEST_DATABASE_URL") is None, reason="TEST_DATABASE_URL is not configured"
    ),
]


def media_payload(number: int) -> dict[str, object]:
    result = historical_payload(number)
    result.pop("reply_to_message_id", None)
    result["photo"] = f"photos/{number}.jpg"
    result["text"] = (
        "Kupno | Mieszkanie\nLokalizacja: Testowa 9, Miasto Testowe\n"
        "Cena: 500000 PLN\nPowierzchnia: 45.5 m2\nPokoje: 2"
    )
    result.pop("text_entities", None)
    return result


async def canonical(db: RecoveryDB, data: dict[str, object]) -> None:
    source = source_identity_from_channel(db.identity)
    channel_id = await db.store.ensure_channel(
        platform="telegram",
        external_id=source.channel_id,
        display_name=source.channel_name,
    )
    run_id = await db.store.start_run(
        channel_id=channel_id,
        mode=RunMode.LIVE,
        parser_version="test",
        source_checksum=None,
        release_sha=None,
    )
    raw = convert_record(data, 0, source).result.message
    assert raw is not None
    await db.store.persist_live_upsert(
        channel_id=channel_id,
        run_id=run_id,
        message=PersistableMessage(raw, extract_listing(raw)),
        checkpoint=RunCheckpoint(),
        counts=RunCounts(),
        advance_checkpoint=True,
    )


async def test_commit_crash_then_unchanged_replay_retains_one_media_intention(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    await canonical(db, media_payload(1))
    # No media code runs before this new repository instance (simulated restart).
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    async with db.factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(MediaRecoveryIntentionRow)) == 1
        )
    await canonical(db, media_payload(1))
    assert await store.discover() == 1
    claim = await store.claim()
    assert claim is not None
    assert claim.item.offer_id is not None
    assert claim.item.descriptor.path == "photos/1.jpg"
    assert await store.finish(claim, MediaRecoveryOutcome("completed"))
    assert await store.claim() is None
    await store.discover()
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(MediaRecoveryWorkRow)) == 1


async def test_two_claimants_and_expired_owner_cannot_complete(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    await canonical(db, media_payload(2))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    claims = await asyncio.gather(store.claim(), store.claim())
    owned = [claim for claim in claims if claim is not None]
    assert len(owned) == 1
    stale = owned[0]
    async with db.factory() as session, session.begin():
        await session.execute(
            update(MediaRecoveryWorkRow).values(
                lease_until=datetime.now(UTC) - timedelta(seconds=1)
            )
        )
    current = await store.claim()
    assert current is not None
    assert current.token != stale.token
    assert not await store.renew(stale)
    assert not await store.finish(stale, MediaRecoveryOutcome("completed"))
    assert await store.finish(current, MediaRecoveryOutcome("completed"))


async def test_media_deferrals_survive_eight_failures_without_data_budget(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    await canonical(db, media_payload(3))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    for _ in range(8):
        claim = await store.claim()
        assert claim is not None
        assert await store.fail(claim, ArchiveFailure("deferred", "OSError"))
        assert await store.claim() is None
        async with db.factory() as session, session.begin():
            await session.execute(
                update(MediaRecoveryWorkRow).values(
                    next_attempt_at=datetime.now(UTC) - timedelta(seconds=1)
                )
            )
    async with db.factory() as session:
        row = await session.scalar(select(MediaRecoveryWorkRow))
        assert row is not None
        assert row.data_failures == 0
        assert row.deferrals == 8
    current = await store.claim()
    assert current is not None
    assert await store.finish(current, MediaRecoveryOutcome("completed"))


async def test_deleted_source_cannot_be_claimed_for_publication(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    await canonical(db, media_payload(4))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    async with db.factory() as session, session.begin():
        await session.execute(update(SourceMessageRow).values(deleted_at=datetime.now(UTC)))
    assert await store.claim() is None
    async with db.factory() as session:
        row = await session.scalar(select(MediaRecoveryWorkRow))
        assert row is not None
        assert row.state == "superseded"


async def test_text_only_anchor_and_boundary_survive_discovery_pages(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    anchor = media_payload(10)
    anchor.pop("photo")
    child = media_payload(11)
    child["text"] = ""
    boundary = media_payload(12)
    boundary["text"] = "synthetic unrelated text"
    boundary.pop("photo")
    orphan = media_payload(13)
    orphan["text"] = ""
    for data in (anchor, child, boundary, orphan):
        await canonical(db, data)
    for _ in range(4):
        # Fresh store per page exercises persisted grouping continuation.
        store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
        assert await store.discover(1) == 1
    async with db.factory() as session:
        rows = list(
            await session.scalars(
                select(MediaRecoveryWorkRow).order_by(MediaRecoveryWorkRow.created_at)
            )
        )
        assert [row.state for row in rows] == ["pending", "unsupported"]
        assert rows[0].association_rule == "time_burst"
        assert rows[1].offer_id is None


@pytest.mark.parametrize("anchor_kind", ["reply", "album"])
async def test_explicit_associations_survive_pages(
    recovery_db: RecoveryDB, anchor_kind: str
) -> None:
    db = recovery_db
    anchor = media_payload(20)
    anchor.pop("photo")
    child = media_payload(21)
    child["text"] = ""
    child["date_unixtime"] = str(int(str(child["date_unixtime"])) + 1000)
    if anchor_kind == "reply":
        child["reply_to_message_id"] = 20
    else:
        anchor["media_group_id"] = "synthetic-album"
        child["media_group_id"] = "synthetic-album"
    await canonical(db, anchor)
    await canonical(db, child)
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    assert await store.discover(1) == 1
    assert await store.discover(1) == 1
    claim = await store.claim()
    assert claim is not None
    assert claim.item.association_rule is not None
    assert claim.item.association_rule.value == (
        "reply" if anchor_kind == "reply" else "explicit_group"
    )


async def test_poison_fairness_and_policy_scoped_re_evaluation(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    await canonical(db, media_payload(30))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    for _ in range(5):
        claim = await store.claim()
        assert claim is not None
        await store.fail(claim, ArchiveFailure("data", "ValueError"))
        async with db.factory() as session, session.begin():
            await session.execute(
                update(MediaRecoveryWorkRow).values(
                    next_attempt_at=datetime.now(UTC) - timedelta(seconds=1)
                )
            )
    assert await store.claim() is None
    await canonical(db, media_payload(31))
    await store.discover()
    await store.discover()
    healthy = await store.claim()
    assert healthy is not None
    assert healthy.raw.external_message_id == 31
    await store.finish(healthy, MediaRecoveryOutcome("completed"))
    async with db.factory() as session, session.begin():
        await session.execute(
            update(MediaRecoveryWorkRow)
            .where(MediaRecoveryWorkRow.state == "quarantined")
            .values(policy_version="older-policy")
        )
    renewed = await store.claim()
    assert renewed is not None
    assert renewed.raw.external_message_id == 30
    async with db.factory() as session:
        row = await session.get(MediaRecoveryWorkRow, renewed.id)
        assert row is not None
        assert row.data_failures == 0
    await store.finish(
        renewed, MediaRecoveryOutcome("quarantined", "source_media_equivalence_unproven")
    )
    assert await store.claim() is None


async def test_provider_delay_and_media_only_pause_are_durable(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    assert (await store.status())["phase"] == "not_started"
    await canonical(db, media_payload(40))
    await store.discover()
    claim = await store.claim()
    assert claim is not None
    await store.fail(claim, ArchiveFailure("deferred", "FloodWaitError", 900))
    assert await SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id).claim() is None
    # Canonical ingestion succeeds while media is deferred or paused.
    await store.control("pause")
    await canonical(db, media_payload(41))
    assert (await store.status())["phase"] == "paused"
    assert await store.discover() == 0
    await store.control("resume")
    assert (await store.status())["phase"] == "canary"
    assert await store.claim() is None


async def test_finished_claim_cannot_be_renewed_or_failed(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    await canonical(db, media_payload(50))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    claim = await store.claim()
    assert claim is not None
    assert await store.renew(claim)
    with pytest.raises(ValueError, match="invalid media"):
        await store.finish(claim, MediaRecoveryOutcome("invalid"))
    assert await store.finish(
        claim, MediaRecoveryOutcome("unsupported", "unsupported_source_media")
    )
    assert not await store.renew(claim)
    assert not await store.fail(claim, ArchiveFailure("data", "ValueError"))


@pytest.mark.parametrize("initial_variants", [0, 1])
async def test_failed_or_partial_derivatives_recover_from_restricted_original(
    recovery_db: RecoveryDB,
    tmp_path: Path,
    initial_variants: int,
) -> None:
    db = recovery_db
    await canonical(db, media_payload(60))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    claim = await store.claim()
    assert claim is not None
    storage = LocalMediaStorage(tmp_path / "source", tmp_path / "originals", tmp_path / "public")
    source_path = storage.source_root / claim.item.descriptor.path
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (20, 20), "blue").save(source_path, format="JPEG")

    class PartialFilesystem:
        def observe_and_store(
            self, descriptor: MediaDescriptor, expected_checksum_sha256: str | None = None
        ) -> MediaObservation:
            return storage.observe_and_store(descriptor, expected_checksum_sha256)

        def create_derivatives(self, original: VerifiedOriginal) -> tuple[PublicDerivative, ...]:
            if initial_variants == 0:
                raise MediaDerivativeError(ObservationReason.DECODE_FAILED)
            return storage.create_derivatives(original)[:1]

    await ProcessMedia(PartialFilesystem(), SQLAlchemyMediaRepository(db.factory))(claim.item)
    source_path.unlink()  # Initial temporary download is gone, as after a restart.

    class NoFetch:
        async def acquire_media(
            self, raw: RawMessage, ordinal: int
        ) -> tuple[MediaDescriptor, MediaLease]:
            _ = raw, ordinal
            pytest.fail("verified restricted original must avoid provider acquisition")

    recover = RecoverStoredMedia(db.factory, storage, NoFetch())
    result = await recover(claim)
    assert result.state == "completed"
    assert await store.finish(claim, result)
    async with db.factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(MediaDispositionAttemptRow)) == 1
        )
        assert await session.scalar(select(func.count()).select_from(MediaDerivativeRow)) == 2
        assert await session.scalar(select(func.count()).select_from(OfferMediaRow)) == 1
    # A late worker cannot republish the same asset after claim completion.
    assert (await recover(claim)).state == "superseded"
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(MediaDerivativeRow)) == 2


async def test_source_revision_change_fences_public_association(
    recovery_db: RecoveryDB, tmp_path: Path
) -> None:
    db = recovery_db
    await canonical(db, media_payload(70))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    claim = await store.claim()
    assert claim is not None
    storage = LocalMediaStorage(tmp_path / "source", tmp_path / "originals", tmp_path / "public")
    source_path = storage.source_root / claim.item.descriptor.path
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (10, 10), "red").save(source_path, format="JPEG")
    edited = media_payload(70)
    edited["edited_unixtime"] = str(int(str(edited["date_unixtime"])) + 60)
    edited["text"] = str(edited["text"]) + " edited"
    await canonical(db, edited)
    item = replace(
        claim.item,
        recovery_work_id=claim.id,
        recovery_token=claim.token,
        association_revision_id=claim.association_revision_id,
    )
    with pytest.raises(MediaRecoveryOwnershipLostError):
        await ProcessMedia(storage, SQLAlchemyMediaRepository(db.factory))(item)
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(OfferMediaRow)) == 0
    await store.discover()
    await store.discover()
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(MediaRecoveryWorkRow)) == 2


async def test_canary_stops_at_limit_and_resume_preserves_counters(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    await canonical(db, media_payload(80))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    async with db.factory() as session, session.begin():
        await session.execute(update(MediaRecoveryChannelRow).values(canary_completed=100))
    assert await store.claim() is None
    assert (await store.status())["phase"] == "canary_ready"
    await store.control("resume")
    assert (await store.status())["phase"] == "running"
    claim = await store.claim()
    assert claim is not None
    await store.fail(claim, ArchiveFailure("systemic", "TelegramSecretError"))
    assert (await store.status())["phase"] == "paused"
    await store.pause("ValueError")
    assert (await store.status())["reason"] == "ValueError"
    with pytest.raises(ValueError, match="invalid media control"):
        await store.control("invalid")


async def test_verified_complete_assets_are_not_transformed_again(
    recovery_db: RecoveryDB,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = recovery_db
    await canonical(db, media_payload(90))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    await store.discover()
    claim = await store.claim()
    assert claim is not None
    storage = LocalMediaStorage(tmp_path / "source", tmp_path / "originals", tmp_path / "public")
    source_path = storage.source_root / claim.item.descriptor.path
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (10, 10), "green").save(source_path, format="JPEG")
    await ProcessMedia(storage, SQLAlchemyMediaRepository(db.factory))(claim.item)
    monkeypatch.setattr(
        LocalMediaStorage, "create_derivatives", lambda *_args: pytest.fail("already complete")
    )
    result = await RecoverStoredMedia(db.factory, storage, AsyncMock())(claim)
    assert result.state == "completed"


async def test_non_listing_attachment_does_not_stop_discovery(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    attachment = media_payload(100)
    attachment.pop("photo")
    attachment.update(text="", file="files/synthetic.pdf", mime_type="application/pdf")
    await canonical(db, attachment)
    await canonical(db, media_payload(101))
    store = SQLAlchemyMediaRecoveryStore(db.factory, db.identity.channel_id)
    assert await store.discover() == 2
    claim = await store.claim()
    assert claim is not None
    assert claim.raw.external_message_id == 101
    async with db.factory() as session:
        row = await session.scalar(
            select(MediaRecoveryWorkRow).where(MediaRecoveryWorkRow.state == "unsupported")
        )
        assert row is not None
        assert row.offer_id is None
