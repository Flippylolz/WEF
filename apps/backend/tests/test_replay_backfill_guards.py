"""Replay and observation maintenance preserve bounded claims and source evidence."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_listing_extraction import _message
from tests.test_parser_replay import SOURCE
from tests.test_parser_replay_integration import replay_db as _replay_db
from tests.test_parser_replay_integration import seed
from wef_backend.features.admin.application.offer_enrichment import value_fingerprint
from wef_backend.features.admin.infrastructure.ai_enrichment_models import OfferFieldOriginRow
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.parse_quality import POLICY_VERSION
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.infrastructure import parse_issue_backfill as backfill
from wef_backend.features.ingestion.infrastructure import parser_replay as replay
from wef_backend.features.ingestion.infrastructure.archive_decoder import decode_archived_payload
from wef_backend.features.ingestion.infrastructure.archive_recovery import SQLAlchemyArchiveRecovery
from wef_backend.features.ingestion.infrastructure.models import (
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)
from wef_backend.features.ingestion.infrastructure.parser_replay_rollback import (
    rollback_parser_work,
)
from wef_backend.features.ingestion.infrastructure.provider_budget import SQLAlchemyProviderBudget

if TYPE_CHECKING:
    from wef_backend.database import DatabaseResources

replay_db = _replay_db

NOW = datetime(2026, 10, 19, tzinfo=UTC)


@pytest.mark.parametrize("payload", [json.dumps({"id": 7}), [7], "[]", 7])
def test_backfill_legacy_payloads_accept_only_objects(payload: object) -> None:
    assert backfill._payload_for_message(payload=payload, external_message_id=7) == {"id": 7}  # noqa: SLF001


@pytest.mark.parametrize("limit", [0, None, 2])
async def test_backfill_stops_for_zero_limit_and_exhaustion_without_inventing_progress(
    limit: int | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock(side_effect=[(0, 1, 1, uuid4()), (0, 0, 0, None)])
    monkeypatch.setattr(backfill, "_process_batch", process)
    summary = await backfill.backfill_parse_issues(_factory(MagicMock()), limit=limit, batch_size=1)
    assert summary.processed == summary.skipped_clean == int(limit != 0)
    assert summary.inserted == 0
    assert process.await_count == (0 if limit == 0 else 2)


async def test_backfill_skips_already_observed_revision_before_issue_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = SourceMessageRow(
        id=uuid4(),
        source_channel_id=uuid4(),
        current_revision_id=uuid4(),
        external_message_id=7,
        raw_payload_json={"id": 7},
        published_at=NOW,
        edited_at=None,
        text_original="Service note",
        raw_checksum="a" * 64,
        message_type="message",
    )
    monkeypatch.setattr(
        backfill, "_eligible_messages", AsyncMock(return_value=[(row, "fixture", "Synthetic")])
    )
    monkeypatch.setattr(backfill, "record_parse_evaluation", AsyncMock(return_value=False))
    insert = AsyncMock()
    monkeypatch.setattr(backfill, "insert_parse_issue", insert)
    assert await backfill._process_batch(MagicMock(), batch_size=1) == (0, 1, 1, row.id)  # noqa: SLF001
    insert.assert_not_awaited()


@pytest.mark.parametrize("mode", ["yield_discovery", "yield_work", "failed_work", "bounded"])
async def test_replay_ticks_yield_retry_and_bound_transactions(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(replay, "ACCEPTED_RELEASE", (PARSER_VERSION, POLICY_VERSION))
    store = replay.SQLAlchemyParserReplay(MagicMock())
    discover = AsyncMock(return_value=(10 if mode == "bounded" else 0, uuid4()))
    work = {"id": uuid4()}
    claim = AsyncMock(return_value=work)
    if mode != "bounded":
        claim.side_effect = [work, None]
    process = AsyncMock(
        side_effect=RuntimeError("private source") if mode == "failed_work" else None
    )
    fail, promote = AsyncMock(), AsyncMock()
    for name, callback in (
        ("discover", discover),
        ("claim", claim),
        ("process", process),
        ("fail", fail),
        ("promote", promote),
    ):
        monkeypatch.setattr(store, name, callback)
    monkeypatch.setattr(time, "monotonic", lambda: 0)
    ready = MagicMock(return_value=True)
    if mode == "yield_discovery":
        ready.side_effect = [True, False]
    elif mode == "yield_work":
        ready.side_effect = [True, True, False]
    await store.tick(NOW, apply=True, live_ready=ready)
    if mode == "yield_discovery":
        discover.assert_not_awaited()
        promote.assert_not_awaited()
    elif mode == "yield_work":
        claim.assert_not_awaited()
        promote.assert_awaited_once_with()
    else:
        assert claim.await_count == (100 if mode == "bounded" else 2)
        assert process.await_count == (100 if mode == "bounded" else 1)
        assert discover.await_count == (10 if mode == "bounded" else 1)
        assert fail.await_count == int(mode == "failed_work")


async def test_unaccepted_incident_parser_cannot_start_automatic_history_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = replay.SQLAlchemyParserReplay(MagicMock())
    discover = AsyncMock()
    monkeypatch.setattr(store, "discover", discover)
    await store.tick(NOW, apply=True, live_ready=lambda: True)
    discover.assert_not_awaited()


@pytest.mark.parametrize("link", [None, "missing_offer"])
async def test_replay_apply_refuses_missing_current_offer_link_or_row(link: str | None) -> None:
    revision = uuid4()
    message = SourceMessageRow(current_revision_id=revision, deleted_at=None)
    session = MagicMock(
        get=AsyncMock(side_effect=[message, None]),
        scalar=AsyncMock(side_effect=["running", uuid4(), None if link is None else MagicMock()]),
    )
    factory = _factory(session)
    factory.begin.return_value = factory.return_value
    store = replay.SQLAlchemyParserReplay(factory)
    finish = AsyncMock()
    store._finish = finish  # type: ignore[method-assign]  # noqa: SLF001
    work: dict[str, object] = {
        "id": uuid4(),
        "claim_id": uuid4(),
        "message_id": uuid4(),
        "revision_id": revision,
    }
    await store.apply(work, NOW, extract_listing(_message(SOURCE)), SOURCE, enabled=True)
    finish.assert_awaited_once_with(
        session,
        work,
        "excluded",
        "no_current_offer_link" if link is None else "non_parser_offer",
        NOW,
    )


async def test_archive_recovery_missing_state_after_insert_is_an_explicit_failure() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None), execute=AsyncMock())
    store = SQLAlchemyArchiveRecovery(_factory(session))
    store._archive = MagicMock(unprocessed_batch=AsyncMock(return_value=()))  # noqa: SLF001
    with pytest.raises(RuntimeError, match="archive recovery state is missing"):
        await store._state(session, "fixture")  # noqa: SLF001


async def test_failed_archive_canary_pauses_before_examining_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = MagicMock(phase="canary", pause_reason=None)
    store = SQLAlchemyArchiveRecovery(_factory(MagicMock()))
    monkeypatch.setattr(store, "_state", AsyncMock(return_value=state))
    await store.finish_batch("fixture", failed=True)
    assert state.phase == "paused"
    assert state.pause_reason == "canary_requires_review"


async def test_provider_reservation_requires_its_inserted_budget_row() -> None:
    session = MagicMock(execute=AsyncMock(), scalar=AsyncMock(return_value=None))
    store = SQLAlchemyProviderBudget(_factory(session))
    with pytest.raises(RuntimeError, match="budget disappeared"):
        await store.reserve_provider_attempt(
            run_id=uuid4(),
            provider=GeocodeProvider.GEOAPIFY,
            account_identity="fixture",
            query_hash="a" * 64,
            daily_limit=3,
            minimum_interval=timedelta(seconds=1),
            now=NOW,
        )


async def test_replay_excludes_retained_source_that_is_no_longer_a_listing() -> None:
    source = _message("Service note").source
    payload = {"id": 7, "type": "message", "date_unixtime": "1792368000", "text": "Service note"}
    raw = decode_archived_payload(payload, source)
    message = SourceMessageRow(source_channel_id=uuid4(), external_message_id=7, deleted_at=None)
    revision = SourceMessageRevisionRow(
        raw_payload_json=payload,
        raw_checksum=raw.checksum,
        text_original=raw.text,
    )
    channel = SourceChannelRow(external_id=source.channel_id, display_name=source.channel_name)
    session = MagicMock(get=AsyncMock(side_effect=[message, revision, channel]))
    store = replay.SQLAlchemyParserReplay(_factory(session))
    store.finish = AsyncMock()  # type: ignore[method-assign]
    work: dict[str, object] = {"message_id": uuid4(), "revision_id": uuid4()}
    await store.process(work, NOW, apply=True)
    store.finish.assert_awaited_once_with(work, "excluded", "non_candidate", NOW)


async def test_replay_apply_lost_claim_does_not_touch_offer() -> None:
    revision = uuid4()
    session = MagicMock(
        get=AsyncMock(return_value=SourceMessageRow(current_revision_id=revision, deleted_at=None)),
        scalar=AsyncMock(side_effect=["running", None]),
    )
    store = replay.SQLAlchemyParserReplay(_factory(session))
    await store.apply(
        {"message_id": uuid4(), "revision_id": revision, "id": uuid4(), "claim_id": uuid4()},
        NOW,
        extract_listing(_message(SOURCE)),
        SOURCE,
        enabled=True,
    )
    assert session.scalar.await_count == 2
    session.add.assert_not_called()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("TEST_DATABASE_URL") is None, reason="PostGIS required")
async def test_replay_rollback_restores_prior_parser_origin(replay_db: DatabaseResources) -> None:
    offer = await seed(replay_db)
    async with replay_db.session_factory.begin() as session:
        revision = await session.scalar(select(SourceMessageRow.current_revision_id))
        assert revision is not None
        await session.merge(
            OfferFieldOriginRow(
                offer_id=offer,
                field_name="apartment_price_min",
                origin="parser",
                state="active",
                parser_version="e2-v13",
                canonical_value=None,
                value_fingerprint=value_fingerprint(None),
                source_revision_id=revision,
                field_event_id=None,
            )
        )
    store = replay.SQLAlchemyParserReplay(replay_db.session_factory)
    await store.tick(NOW, apply=True, live_ready=lambda: True)
    await store.tick(NOW, apply=True, live_ready=lambda: True)
    async with replay_db.session_factory() as session:
        work = await session.scalar(text("SELECT id FROM parser_replay_work"))
        assert work is not None
        changed = await session.get(OfferFieldOriginRow, (offer, "apartment_price_min"))
        assert changed is not None
        assert changed.canonical_value == 78000000
    result = await rollback_parser_work(replay_db.session_factory, work, NOW)
    assert result["reverted"] > 0
    assert result["protected_conflict"] == 0
    async with replay_db.session_factory() as session:
        restored = await session.get(OfferFieldOriginRow, (offer, "apartment_price_min"))
        assert restored is not None
        assert restored.origin == "parser"
        assert restored.parser_version == "e2-v13"
        assert restored.canonical_value is None
        assert restored.value_fingerprint == value_fingerprint(None)
        assert restored.source_revision_id == revision
