"""Admin persistence guards for concurrent changes, provider evidence and bounded reads."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from tests.fakes import FakeChatCompletions, FakePlaceAiReviewStore
from tests.test_ai_review import _generate, _payload, _revision
from tests.test_complete_import_integration import NOW
from tests.test_complete_import_repository_boundaries import import_database
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_offer_ai_enrichment_integration import TEST_DATABASE_URL
from tests.test_persistence_integration import _candidate
from tests.test_place_ai_review_integration import _location
from wef_backend.features.admin.application.admin_ops import LocationStatusFilter
from wef_backend.features.admin.application.ai_review import AiApplyStatus, ReviewRunState
from wef_backend.features.admin.application.ingestion_ai_parse import IngestionAiApplyStatus
from wef_backend.features.admin.infrastructure.ai_models import IngestionAiParseRunRow
from wef_backend.features.admin.infrastructure.ai_review_store import (
    SQLAlchemyPlaceAiReviewStore,
    _snapshot,
    _to_row,
)
from wef_backend.features.admin.infrastructure.ingestion_ai_parse_store import (
    SQLAlchemyIngestionAiParseStore,
)
from wef_backend.features.admin.infrastructure.place_store import (
    SQLAlchemyLocationAdminStore,
    _has_usable_candidate,
    _latest_candidate,
    _usable_candidate_result,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.application.persistence import (
    PersistHistoricalIngestion,
    RunMetadata,
)
from wef_backend.features.ingestion.infrastructure.models import (
    LocationGeocodeSelectionRow,
    SourceMessageRevisionRow,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)

if TYPE_CHECKING:
    from wef_backend.database import DatabaseResources
    from wef_backend.features.admin.application.ai_review import LocationAiSnapshot, PlaceReviewRun

__all__ = ["import_database"]


def _transaction_factory(session: MagicMock) -> MagicMock:
    factory = _factory(session)
    factory.begin.return_value = factory()
    return factory


async def _review() -> tuple[LocationRow, LocationAiSnapshot, PlaceReviewRun]:
    location = _location("ul. Syntetyczna 1, Warszawa")
    snapshot = _snapshot(location)
    revision = _revision("synthetic source")
    store = FakePlaceAiReviewStore(snapshot=snapshot, revisions=(revision,))
    generate, _ = _generate(store, FakeChatCompletions(payload=_payload(revision.revision_id)))
    outcome = await generate(owner_id=uuid4(), location_id=location.id, request_id=uuid4())
    assert outcome.run is not None
    return location, snapshot, outcome.run


async def test_unknown_review_store_reads_are_empty() -> None:
    """Missing location and review identities do not fabricate owner-visible records."""
    session = MagicMock(get=AsyncMock(return_value=None))
    store = SQLAlchemyPlaceAiReviewStore(_factory(session))
    assert await store.get_location_snapshot(uuid4()) is None
    assert await store.get_run(uuid4()) is None


async def test_review_sources_are_distinct_and_capped() -> None:
    """A repeated offer-source join cannot consume the entire bounded review sample."""
    first = SourceMessageRevisionRow(
        id=uuid4(), raw_checksum="a" * 64, published_at=NOW, text_original="first"
    )
    second = SourceMessageRevisionRow(
        id=uuid4(), raw_checksum="b" * 64, published_at=NOW, text_original="second"
    )
    third = SourceMessageRevisionRow(
        id=uuid4(), raw_checksum="c" * 64, published_at=NOW, text_original="third"
    )
    query = MagicMock()
    query.scalars.return_value.all.return_value = [first, first, second, third]
    session = MagicMock(execute=AsyncMock(return_value=query))
    result = await SQLAlchemyPlaceAiReviewStore(_factory(session)).list_current_source_revisions(
        uuid4(), limit=2
    )
    assert [item.revision_id for item in result] == [first.id, second.id]
    assert [item.text_original for item in result] == ["first", "second"]


async def test_review_insert_rolls_back_on_uniqueness_race() -> None:
    """Only the winning pending review is acknowledged after an insert collision."""
    _, _, run = await _review()
    session = MagicMock(
        commit=AsyncMock(side_effect=IntegrityError("INSERT", {}, ValueError())),
        rollback=AsyncMock(),
    )
    assert not await SQLAlchemyPlaceAiReviewStore(_factory(session)).insert_run(run)
    session.rollback.assert_awaited_once()


async def test_review_reader_skips_malformed_legacy_field_rows() -> None:
    """An old invalid field entry cannot break the complete persisted review page."""
    _, _, run = await _review()
    row = _to_row(run)
    assert isinstance(row.proposed_fields, list)
    row.proposed_fields = [None, *row.proposed_fields]
    session = MagicMock(get=AsyncMock(return_value=row))
    result = await SQLAlchemyPlaceAiReviewStore(_factory(session)).get_run(run.id)
    assert result is not None
    assert result.proposed_fields == run.proposed_fields


@pytest.mark.parametrize(
    "mode",
    [
        "location_missing",
        "review_missing",
        "state_changed",
        "snapshot_changed",
        "integrity",
        "name_only",
    ],
)
async def test_review_apply_refuses_concurrent_changes_and_preserves_name_only_status(
    mode: str,
) -> None:
    """The store rechecks persisted inputs and treats unique-write races as collisions."""
    location, snapshot, run = await _review()
    review = _to_row(run)
    if mode == "state_changed":
        review.state = ReviewRunState.FAILED.value
    elif mode == "snapshot_changed":
        location.updated_at += timedelta(seconds=1)
    session = MagicMock(
        get=AsyncMock(
            side_effect=[
                None if mode == "location_missing" else location,
                None if mode == "review_missing" else review,
            ]
        ),
        scalar=AsyncMock(return_value=None),
        execute=AsyncMock(
            side_effect=IntegrityError("UPDATE", {}, ValueError()) if mode == "integrity" else None
        ),
    )
    status = await SQLAlchemyPlaceAiReviewStore(
        _transaction_factory(session)
    ).apply_selected_fields(
        run=run,
        snapshot=snapshot,
        display_name="New name",
        display_address=snapshot.display_address,
        district=snapshot.district,
        normalized_address="synthetic",
        normalized_address_hash="b" * 64,
        return_to_review=False,
        applied_fields=("display_name",),
        actor_id=str(run.owner_user_id),
        decided_at=NOW,
    )
    expected = {
        "location_missing": AiApplyStatus.UNKNOWN,
        "review_missing": AiApplyStatus.UNKNOWN,
        "state_changed": AiApplyStatus.STALE,
        "snapshot_changed": AiApplyStatus.STALE,
        "integrity": AiApplyStatus.COLLISION,
        "name_only": AiApplyStatus.APPLIED,
    }
    assert status is expected[mode]
    if mode == "name_only":
        updates = [call.args[0].compile().params for call in session.execute.await_args_list]
        assert updates[0]["review_status"] == location.review_status
        assert len(updates) == 2
    elif mode != "integrity":
        session.execute.assert_not_awaited()


@pytest.mark.parametrize("operation", ["apply", "fail"])
@pytest.mark.parametrize("rowcount", [0, 1])
async def test_parse_run_state_updates_acknowledge_only_one_pending_row(
    operation: str, rowcount: int
) -> None:
    """Conditional updates commit a single winner and roll back stale competing writes."""
    query = MagicMock(rowcount=rowcount)
    session = MagicMock(
        get=AsyncMock(return_value=IngestionAiParseRunRow(state="pending")),
        execute=AsyncMock(return_value=query),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    store = SQLAlchemyIngestionAiParseStore(_factory(session))
    if operation == "apply":
        assert await store.mark_applied(uuid4(), offer_id=uuid4(), applied_at=NOW) is (
            IngestionAiApplyStatus.APPLIED if rowcount else IngestionAiApplyStatus.COLLISION
        )
    else:
        assert await store.mark_failed(uuid4()) is bool(rowcount)
    assert session.commit.await_count == rowcount
    assert session.rollback.await_count == 1 - rowcount


async def test_parse_context_without_its_source_fails_closed() -> None:
    """A retained revision cannot be assigned an invented external message identity."""
    row = SourceMessageRevisionRow(
        id=uuid4(), source_message_id=uuid4(), raw_checksum="a" * 64, text_original="synthetic"
    )
    session = MagicMock(get=AsyncMock(return_value=row), scalar=AsyncMock(return_value=None))
    with pytest.raises(RuntimeError, match="source message not found"):
        await SQLAlchemyIngestionAiParseStore(_factory(session)).get_revision_context(row.id)


@pytest.mark.parametrize(
    "mode",
    [
        "no_selection",
        "no_result_id",
        "missing_row",
        "missing_point",
        "out_of_scope",
        "provider_error",
        "missing_coordinates",
    ],
)
async def test_latest_location_candidate_requires_valid_provider_point(mode: str) -> None:
    """An absent, failed or unprojectable provider result cannot become a map candidate."""
    latest = (
        None
        if mode == "no_selection"
        else LocationGeocodeSelectionRow(
            geocode_result_id=None if mode == "no_result_id" else uuid4()
        )
    )
    row = (
        None
        if mode == "missing_row"
        else SimpleNamespace(
            point=None if mode == "missing_point" else object(),
            within_scope=mode != "out_of_scope",
            error_code="transient" if mode == "provider_error" else None,
        )
    )
    first = MagicMock(one_or_none=MagicMock(return_value=row))
    second = MagicMock(one_or_none=MagicMock(return_value=None))
    session = MagicMock(execute=AsyncMock(side_effect=[first, second]))
    assert await _latest_candidate(session, latest) is None
    if mode == "provider_error":
        session.execute = AsyncMock(return_value=first)
        assert await _usable_candidate_result(session, uuid4()) is None


@pytest.mark.parametrize("mode", ["no_selection", "missing_coordinates"])
async def test_location_candidate_presence_requires_coordinates(mode: str) -> None:
    latest = (
        None if mode == "no_selection" else LocationGeocodeSelectionRow(geocode_result_id=uuid4())
    )
    query = MagicMock(one_or_none=MagicMock(return_value=None))
    session = MagicMock(execute=AsyncMock(return_value=query), scalars=AsyncMock())
    session.scalars.return_value = MagicMock(first=MagicMock(return_value=latest))
    assert not await _has_usable_candidate(session, uuid4())


@pytest.mark.parametrize("mode", ["no_selection", "missing_coordinates"])
async def test_accept_candidate_rechecks_latest_selection_and_coordinate_projection(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    location = _location("ul. Syntetyczna 1, Warszawa")
    session = MagicMock(get=AsyncMock(return_value=location), scalars=AsyncMock())
    latest = (
        None if mode == "no_selection" else LocationGeocodeSelectionRow(geocode_result_id=uuid4())
    )
    session.scalars.return_value = MagicMock(first=MagicMock(return_value=latest))
    monkeypatch.setattr(
        "wef_backend.features.admin.infrastructure.place_store._usable_candidate_result",
        AsyncMock(return_value=SimpleNamespace(precision="building", confidence=Decimal("0.9"))),
    )
    monkeypatch.setattr(
        "wef_backend.features.admin.infrastructure.place_store._point_coordinates",
        AsyncMock(return_value=None),
    )
    assert not await SQLAlchemyLocationAdminStore(
        _transaction_factory(session)
    ).apply_accept_candidate(location_id=location.id, actor_id="synthetic", decided_at=NOW)


@pytest.mark.integration
@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="PostGIS required")
async def test_location_store_projects_offer_context_and_specific_status_filter(
    import_database: DatabaseResources,
) -> None:
    candidate = _candidate(1, "Mieszkanie 40 m² cena 560 000 zł", "a" * 64)
    await PersistHistoricalIngestion(
        SQLAlchemyIngestionPersistence(import_database.session_factory)
    )(
        channel=candidate.raw.source,
        messages=(candidate,),
        metadata=RunMetadata(parser_version="integration@1"),
    )
    async with import_database.session_factory.begin() as session:
        await session.execute(update(LocationRow).values(review_status="rejected"))
    store = SQLAlchemyLocationAdminStore(import_database.session_factory)
    rows = await store.list_locations(status=LocationStatusFilter.REJECTED, search="Przykładowa")
    assert len(rows) == 1
    detail = await store.get_edit_detail(rows[0].id)
    assert detail is not None
    assert len(detail.offers) == 1
    assert detail.offers[0].price_min_minor == 56_000_000
    assert not detail.summary.has_candidate
    assert detail.candidate is None
    assert not await store.apply_set_point(
        location_id=uuid4(),
        longitude=Decimal(21),
        latitude=Decimal("52.2"),
        actor_id="synthetic",
        decided_at=NOW,
    )
