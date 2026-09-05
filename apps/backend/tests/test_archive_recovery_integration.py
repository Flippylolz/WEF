"""PostGIS proofs for original-event identity, commit boundaries and bounded recovery."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from alembic import command
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from wef_backend import archive_recovery_command
from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.ingestion.application.archive_processing import ArchivedEventProcessor
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    RunCheckpoint,
    RunCounts,
    RunMode,
)
from wef_backend.features.ingestion.application.raw_archive import RawEventDrainer
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel
from wef_backend.features.ingestion.domain.model import canonical_json_checksum
from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramChannelIdentity,
    default_live_channel_identity,
)
from wef_backend.features.ingestion.infrastructure import persistence_adapter
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.archive_evidence import (
    flatten_legacy_payload,
    write_resolution,
)
from wef_backend.features.ingestion.infrastructure.archive_recovery import SQLAlchemyArchiveRecovery
from wef_backend.features.ingestion.infrastructure.models import (
    SourceMessageRevisionRow,
    SourceMessageRow,
    TelegramArchiveRecoveryRow,
    TelegramArchiveResolutionRow,
    TelegramRawEventRow,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from wef_backend.features.ingestion.application.telegram_events import (
        RawArchiveKind,
        RawEventRecord,
    )

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]
NOW = datetime(2026, 9, 5, tzinfo=UTC)


def payload(message_id: int, *, edit: int = 0) -> dict[str, object]:
    """Invented non-candidate with historical mixed text, entities, media and reply."""
    result: dict[str, object] = {
        "id": message_id,
        "type": "message",
        "date_unixtime": str(int(NOW.timestamp())),
        "text": ["synthetic ", {"type": "bold", "text": f"record {edit}"}],
        "text_entities": [{"type": "plain", "text": f"synthetic record {edit}"}],
        "photo": "photos/synthetic.jpg",
        "reply_to_message_id": message_id - 1,
    }
    if edit:
        result["edited_unixtime"] = str(int(NOW.timestamp()) + edit)
    return result


@dataclass
class RecoveryDB:
    """Real persistence boundaries for a synthetic recovery cohort."""

    factory: async_sessionmaker[AsyncSession]
    identity: TelegramChannelIdentity
    archive: SQLAlchemyRawEventArchive
    store: SQLAlchemyIngestionPersistence

    def processor(self) -> ArchivedEventProcessor:
        return ArchivedEventProcessor(self.store, decode_archived_payload)

    def drainer(self, *, bounded: bool = False) -> RawEventDrainer:
        return RawEventDrainer(
            self.archive,
            self.processor(),
            self.identity,
            recovery=SQLAlchemyArchiveRecovery(self.factory) if bounded else None,
        )

    async def land(
        self, data: dict[str, object], *, kind: RawArchiveKind = "new", checksum: str | None = None
    ) -> RawEventRecord:
        event_id = await self.archive.land(
            event_kind=kind,
            channel_external_id=self.identity.channel_id,
            external_message_id=cast("int", data["id"]),
            payload=data,
            checksum=checksum or canonical_json_checksum(data),
        )
        records = await self.archive.unprocessed_batch(1000)
        return next(record for record in records if record.id == event_id)

    async def canonical(self, data: dict[str, object]) -> None:
        channel = source_identity_from_channel(self.identity)
        channel_id = await self.store.ensure_channel(
            platform="telegram", external_id=channel.channel_id, display_name=channel.channel_name
        )
        run_id = await self.store.start_run(
            channel_id=channel_id,
            mode=RunMode.LIVE,
            parser_version="test",
            source_checksum=None,
            release_sha=None,
        )
        await self.store.persist_live_upsert(
            channel_id=channel_id,
            run_id=run_id,
            message=PersistableMessage(decode_archived_payload(data, channel), None),
            checkpoint=RunCheckpoint(),
            counts=RunCounts(),
            advance_checkpoint=True,
        )

    async def counts(self) -> tuple[int, int, int]:
        async with self.factory() as session:
            return tuple(
                [
                    int(await session.scalar(select(func.count()).select_from(model)) or 0)
                    for model in (
                        SourceMessageRow,
                        SourceMessageRevisionRow,
                        TelegramArchiveResolutionRow,
                    )
                ]
            )  # type: ignore[return-value]

    async def due(self) -> None:
        async with self.factory() as session, session.begin():
            await session.execute(
                update(TelegramArchiveRecoveryRow).values(next_batch_at=NOW - timedelta(days=1))
            )


@pytest.fixture
async def recovery_db() -> AsyncIterator[RecoveryDB]:
    """Use only the configured disposable test database, never a live source."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(
        command.upgrade,
        alembic_config(
            Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))
        ),
        "head",
    )
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE source_channels, telegram_raw_events, "
                    "telegram_archive_recovery CASCADE"
                )
            )
        yield RecoveryDB(
            factory,
            replace(default_live_channel_identity(), channel_id="4242424242"),
            SQLAlchemyRawEventArchive(factory),
            SQLAlchemyIngestionPersistence(factory),
        )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE source_channels, telegram_raw_events, "
                    "telegram_archive_recovery CASCADE"
                )
            )
        await engine.dispose()


async def test_original_completes_without_touching_terminal_live_sibling(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    original = await db.land(payload(101))
    await db.canonical(payload(101))
    sibling_payload = {
        "id": 101,
        "type": "message",
        "date_unixtime": str(int(NOW.timestamp())),
        "text": "synthetic record 0",
        "from_live": True,
    }
    sibling = await db.land(sibling_payload)
    await db.archive.mark_attempt(sibling.id, outcome="processed")
    second = await db.land(payload(102))
    drainer = replace(db.drainer(), batch_size=1)
    first_result = await drainer.drain_once()
    assert first_result.newly_terminal == 1
    assert [row.id for row in await db.archive.unprocessed_batch(10)] == [second.id]
    assert (await drainer.drain_once()).newly_terminal == 1
    assert (await drainer.drain_once()).newly_terminal == 0
    assert await db.counts() == (2, 2, 2)
    assert not await db.archive.mark_attempt(original.id, outcome="failed", error_category="late")
    assert not await db.archive.mark_attempt(sibling.id, outcome="processed")
    async with db.factory() as session:
        rows = (await session.scalars(select(TelegramRawEventRow))).all()
        assert len(rows) == 3
        assert all(row.attempts == 1 for row in rows)
        original_row = await session.get(TelegramRawEventRow, original.id)
        assert original_row is not None
        assert original_row.payload_json == payload(101)
        source = await session.scalar(
            select(SourceMessageRow).where(SourceMessageRow.external_message_id == 101)
        )
        assert source is not None
        assert source.raw_payload_json == payload(101)


@pytest.mark.parametrize("cancel", [False, True])
async def test_restart_after_commit_before_acknowledgement(
    recovery_db: RecoveryDB, monkeypatch: pytest.MonkeyPatch, *, cancel: bool
) -> None:
    db = recovery_db
    record = await db.land(payload(201))
    mark = db.archive.mark_attempt

    async def unavailable(event_id: UUID, **kwargs: object) -> bool:
        if kwargs["outcome"] != "failed":
            if cancel:
                raise asyncio.CancelledError
            msg = "synthetic acknowledgement outage"
            raise OSError(msg)
        return await mark(event_id, outcome="failed", error_category="OSError")

    monkeypatch.setattr(db.archive, "mark_attempt", unavailable)
    if cancel:
        with pytest.raises(asyncio.CancelledError):
            await db.drainer().drain_once()
    else:
        assert (await db.drainer().drain_once()).failed == 1
    assert await db.counts() == (1, 1, 1)
    monkeypatch.setattr(db.archive, "mark_attempt", mark)

    def forbidden_decode(*_args: object) -> None:
        pytest.fail("a committed receipt must not decode or extract again")

    processor = replace(db.processor(), decoder=forbidden_decode)  # type: ignore[arg-type]
    result = await replace(db.drainer(), processor=processor).drain_once()
    assert result.newly_terminal == 1
    assert await db.counts() == (1, 1, 1)
    async with db.factory() as session:
        row = await session.get(TelegramRawEventRow, record.id)
        assert row is not None
        assert row.attempts == (1 if cancel else 2)


async def test_failure_before_receipt_rolls_back_canonical_effect(
    recovery_db: RecoveryDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = recovery_db
    await db.land(payload(301))
    original = write_resolution

    async def fail_receipt(*_args: object, **_kwargs: object) -> None:
        msg = "synthetic precommit failure"
        raise OSError(msg)

    monkeypatch.setattr(persistence_adapter, "write_resolution", fail_receipt)
    failed = await db.drainer().drain_once()
    assert failed.failed == 1
    assert failed.last_committed_at is None
    assert await db.counts() == (0, 0, 0)
    monkeypatch.setattr(persistence_adapter, "write_resolution", original)
    assert (await db.drainer().drain_once()).newly_terminal == 1
    assert await db.counts() == (1, 1, 1)


async def test_newer_edit_survives_old_replay_and_delete_blocks_recreation(
    recovery_db: RecoveryDB,
) -> None:
    db = recovery_db
    newer = await db.land(payload(401, edit=20), kind="edit")
    await db.processor()(record=newer, identity=db.identity)
    old = await db.land(payload(401))
    assert (await db.processor()(record=old, identity=db.identity)).disposition == "superseded"
    async with db.factory() as session:
        source = await session.scalar(select(SourceMessageRow))
        assert source is not None
        assert source.raw_payload_json == payload(401, edit=20)
    deletion = await db.land(
        {"id": 402, "type": "deleted_message", "from_live": True}, kind="delete"
    )
    not_yet_canonical = await db.land(payload(402))
    receipt = await db.processor()(record=not_yet_canonical, identity=db.identity)
    assert receipt.disposition == "deleted"
    await db.processor()(record=deletion, identity=db.identity)
    assert await db.counts() == (1, 1, 4)
    deletion_existing = await db.land({"id": 401, "type": "deleted_message"}, kind="delete")
    await db.processor()(record=deletion_existing, identity=db.identity)
    latest = await db.land(payload(401, edit=40), kind="edit")
    assert (await db.processor()(record=latest, identity=db.identity)).disposition == "deleted"


async def test_legacy_flattening_requires_retained_checksum_proof(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    data = payload(501)
    await db.canonical(data)
    flattened = flatten_legacy_payload(data)
    record = await db.land(flattened, checksum=canonical_json_checksum(data))
    assert (
        await db.processor()(record=record, identity=db.identity)
    ).disposition == "already_canonical"
    bad = await db.land(payload(502), checksum="a" * 64)
    with pytest.raises(ValueError, match="source proof"):
        await db.processor()(record=bad, identity=db.identity)
    conflict = await db.land({**data, "text": "different equal-time content"})
    with pytest.raises(ValueError, match="equal source time"):
        await db.processor()(record=conflict, identity=db.identity)
    with pytest.raises(ValueError, match="channel mismatch"):
        await db.processor()(
            record=replace(record, channel_external_id="other"), identity=db.identity
        )
    with pytest.raises(ValueError, match="identity mismatch"):
        await db.processor()(record=replace(record, external_message_id=999), identity=db.identity)
    assert await db.counts() == (1, 1, 1)
    async with db.factory() as session:
        row = await session.get(TelegramRawEventRow, record.id)
        assert row is not None
        assert row.payload_json == flattened
        assert row.checksum == canonical_json_checksum(data)


async def test_canary_preflight_restart_pause_and_empty_start(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    recovery = SQLAlchemyArchiveRecovery(db.factory)
    before = await recovery.preflight(db.identity.channel_id)
    assert before["phase"] == "not_started"
    assert before["eligible"] == 0
    assert (await db.drainer(bounded=True).drain_once()).selected == 0
    await db.land(payload(601))
    await db.due()
    assert (await db.drainer(bounded=True).drain_once()).newly_terminal == 1
    await recovery.set_paused(db.identity.channel_id, paused=True)
    await db.land(payload(602))
    assert (await db.drainer(bounded=True).drain_once()).selected == 0
    await recovery.set_paused(db.identity.channel_id, paused=False)
    # Resuming an originally empty canary must not exclude later arrivals forever.
    await db.due()
    assert (await db.drainer(bounded=True).drain_once()).newly_terminal == 1
    assert (await recovery.preflight(db.identity.channel_id))["eligible"] == 0


async def test_canary_is_bounded_and_expands_only_after_receipts(recovery_db: RecoveryDB) -> None:
    db = recovery_db
    for message_id in range(701, 802):
        await db.land(payload(message_id))
    recovery = SQLAlchemyArchiveRecovery(db.factory)
    assert (await recovery.preflight(db.identity.channel_id))["eligible"] == 101
    for _ in range(4):
        await db.due()
        assert (await db.drainer(bounded=True).drain_once()).newly_terminal == 25
    assert (await recovery.preflight(db.identity.channel_id))["phase"] == "running"
    await db.due()
    assert (await db.drainer(bounded=True).drain_once()).newly_terminal == 1
    await db.due()
    assert (await db.drainer(bounded=True).drain_once()).newly_terminal == 0
    assert await db.counts() == (101, 101, 101)


async def test_offer_effect_is_once_and_pending_delete_hides_existing_offer(
    recovery_db: RecoveryDB,
) -> None:
    """A receipt prevents duplicate offers, and retained deletion wins before its own drain."""
    db = recovery_db
    body = (
        "Kupno | Mieszkanie\nLokalizacja: Testowa 901, Miasto Testowe\n"
        "Cena: 501000 PLN\nPowierzchnia: 45.5 m2\nPokoje: 2"
    )
    record = await db.land({**payload(901), "text": body})
    assert (await db.processor()(record=record, identity=db.identity)).disposition == "applied"
    assert (await db.drainer().drain_once()).newly_terminal == 1
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(OfferRow)) == 1
    await db.land({"id": 901, "type": "deleted_message"}, kind="delete")
    newer = await db.land({**payload(901, edit=60), "text": body}, kind="edit")
    assert (await db.processor()(record=newer, identity=db.identity)).disposition == "deleted"
    async with db.factory() as session:
        assert await session.scalar(select(func.count()).select_from(OfferRow)) == 1
        assert await session.scalar(select(OfferRow.visibility)) == "hidden"
        assert await session.scalar(select(SourceMessageRow.deleted_at)) is not None
    assert (await db.counts())[:2] == (1, 1)


async def test_operator_preflight_apply_pause_and_resume(
    recovery_db: RecoveryDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator entry uses the same bounded state without exposing raw evidence."""
    assert TEST_DATABASE_URL is not None
    db = recovery_db
    monkeypatch.setattr(
        archive_recovery_command,
        "load_settings",
        lambda: Settings(env="test", database_url=TEST_DATABASE_URL),
    )
    monkeypatch.setattr(
        archive_recovery_command, "default_live_channel_identity", lambda: db.identity
    )
    await db.land(payload(1001))
    assert (await archive_recovery_command.run("preflight"))["eligible"] == 1
    assert (await archive_recovery_command.run("pause"))["phase"] == "paused"
    assert (await archive_recovery_command.run("apply"))["selected"] == 0
    assert (await archive_recovery_command.run("resume"))["phase"] == "canary"
    result = await archive_recovery_command.run("apply")
    assert result["newly_terminal"] == 1
    assert "synthetic" not in str(result)
