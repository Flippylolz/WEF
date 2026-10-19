"""Durable claim readbacks, stale ownership and safe validation rollback guards."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_complete_import_integration import NOW
from tests.test_geocoding import _result
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_location_resolution import resolution
from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.application.geocoding import (
    CachedGeocode,
    ClaimDisposition,
    MissClaim,
)
from wef_backend.features.ingestion.application.location_revalidation import ValidationClaim
from wef_backend.features.ingestion.application.media_recovery import MEDIA_RECOVERY_POLICY
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeCacheKey,
    GeocodeProvider,
    normalize_geocode_query,
    review_geocode_result,
)
from wef_backend.features.ingestion.infrastructure import (
    location_validation_store as validation_module,
)
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.location_validation_store import (
    SQLAlchemyLocationValidationStore,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeMissClaimRow,
    MediaRecoveryChannelRow,
    MediaRecoveryWorkRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)


def _claim() -> ValidationClaim:
    return ValidationClaim(
        uuid4(), uuid4(), "a" * 64, "ul. Testowa 1, Warszawa", None, 1, 1, "observe", 0
    )


async def test_geocode_claim_requires_durable_insert_or_existing_owner() -> None:
    query = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    session = MagicMock(execute=AsyncMock(return_value=query), scalar=AsyncMock(return_value=None))
    key = GeocodeCacheKey(GeocodeProvider.FIXTURE, "synthetic query")
    with pytest.raises(RuntimeError, match="claim disappeared during acquisition"):
        await SQLAlchemyGeocodeStore(_factory(session)).claim_miss(
            key, owner_id="owner", now=NOW, lease_expires_at=NOW + timedelta(seconds=10)
        )


@pytest.mark.parametrize(
    "mode", ["fenced_with_cache", "insert_conflict", "missing_durable_id", "missing_cache_row"]
)
async def test_geocode_completion_reconciles_only_acknowledged_cache_rows(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = GeocodeCacheKey(GeocodeProvider.FIXTURE, "synthetic query")
    claim = MissClaim(ClaimDisposition.OWNER, "owner", 1, NOW + timedelta(seconds=10))
    current = GeocodeMissClaimRow(owner_id="owner", fencing_token=1)
    cached = CachedGeocode(uuid4(), _result(), None)
    values = (
        [None]
        if mode == "fenced_with_cache"
        else [current, None, None if mode == "missing_durable_id" else cached.result_id]
        if mode in {"insert_conflict", "missing_durable_id"}
        else [current, cached.result_id]
    )
    session = MagicMock(scalar=AsyncMock(side_effect=values), delete=AsyncMock())
    store = SQLAlchemyGeocodeStore(_factory(session))
    monkeypatch.setattr(
        store,
        "_get_cached_in_session",
        AsyncMock(return_value=None if mode == "missing_cache_row" else cached),
    )

    async def complete() -> CachedGeocode:
        return await store.complete_miss(
            key,
            claim=claim,
            query=normalize_geocode_query("Warszawa"),
            result=_result(),
            attempted_at=NOW,
            expires_at=None,
        )

    if mode in {"missing_durable_id", "missing_cache_row"}:
        with pytest.raises(
            RuntimeError,
            match="no durable result"
            if mode == "missing_durable_id"
            else "row missing after completion",
        ):
            await complete()
        session.delete.assert_not_awaited()
    else:
        assert await complete() is cached
        assert session.delete.await_count == int(mode == "insert_conflict")


async def test_geocode_selection_requires_location_and_selected_coordinates() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None))
    store = SQLAlchemyGeocodeStore(_factory(session))
    decision = review_geocode_result(
        _result(), query=normalize_geocode_query("ul. Marszałkowska 1, Warszawa")
    )
    assert decision.select_result
    with pytest.raises(ValueError, match="location does not exist"):
        await store.select_for_location(
            location_id=uuid4(),
            cached=CachedGeocode(uuid4(), _result(), None),
            decision=decision,
            actor_type="operator",
            actor_id="synthetic",
        )
    no_coordinates = CachedGeocode(uuid4(), _result(lon=None, lat=None), None)
    with pytest.raises(ValueError, match="selected result must have coordinates"):
        await store.select_in_session(
            session,
            location=LocationRow(id=uuid4()),
            cached=no_coordinates,
            decision=decision,
            actor_type="operator",
            actor_id="synthetic",
        )
    session.add.assert_not_called()


@pytest.mark.parametrize("action", ["claim", "control", "pause"])
async def test_media_store_missing_channel_is_a_noop(action: str) -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None))
    store = SQLAlchemyMediaRecoveryStore(_factory(session), "missing")
    if action == "claim":
        assert await store.claim() is None
    elif action == "control":
        await store.control("pause")
    else:
        await store.pause("synthetic")
    session.execute.assert_not_called()


async def test_media_claim_respects_paused_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    store = SQLAlchemyMediaRecoveryStore(_factory(session), "synthetic")
    monkeypatch.setattr(
        SQLAlchemyMediaRecoveryStore,
        "_channel",
        AsyncMock(return_value=MediaRecoveryChannelRow(phase="paused")),
    )
    assert await store.claim() is None
    session.get.assert_not_called()


@pytest.mark.parametrize(
    "mode", ["missing_revision", "missing_source", "missing_channel", "invalid_payload"]
)
async def test_media_claim_requires_complete_retained_source_relationships(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    revision_id, source_id, channel_id = uuid4(), uuid4(), uuid4()
    row = MediaRecoveryWorkRow(
        id=uuid4(), source_revision_id=revision_id, policy_version=MEDIA_RECOVERY_POLICY
    )
    revision = SourceMessageRevisionRow(
        id=revision_id, source_message_id=source_id, raw_payload_json=[]
    )
    source = SourceMessageRow(current_revision_id=revision_id, deleted_at=None)
    channel = SourceChannelRow(external_id="synthetic", display_name="Synthetic")
    session = MagicMock(
        scalar=AsyncMock(return_value=row),
        get=AsyncMock(
            side_effect=[
                None if mode == "missing_revision" else revision,
                None if mode == "missing_source" else source,
                None if mode == "missing_channel" else channel,
            ]
        ),
    )
    store = SQLAlchemyMediaRecoveryStore(_factory(session), "synthetic")
    monkeypatch.setattr(
        SQLAlchemyMediaRecoveryStore,
        "_channel",
        AsyncMock(return_value=MediaRecoveryChannelRow(source_channel_id=channel_id)),
    )
    monkeypatch.setattr(
        SQLAlchemyMediaRecoveryStore, "_claim_allowed", AsyncMock(return_value=True)
    )
    with pytest.raises(
        TypeError if mode == "invalid_payload" else RuntimeError,
        match="payload is invalid" if mode == "invalid_payload" else "relationship missing",
    ):
        await store.claim()


async def test_validation_claim_refuses_apply_without_discovery_readiness() -> None:
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = {
        "mode": "apply",
        "next_eligible_at": NOW,
        "discovery_ready": False,
    }
    session = MagicMock(execute=AsyncMock(return_value=result))
    assert (
        await SQLAlchemyLocationValidationStore(_factory(session)).claim(
            target="synthetic", now=NOW
        )
        is None
    )
    session.execute.assert_awaited_once()


async def test_validation_finish_refuses_a_deleted_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None))
    monkeypatch.setattr(SQLAlchemyLocationValidationStore, "_owned", AsyncMock(return_value={}))
    assert (
        await SQLAlchemyLocationValidationStore(_factory(session)).finish(
            _claim(), resolution(), now=NOW
        )
        == "missing_location"
    )
    session.execute.assert_not_called()


async def test_validation_defer_cannot_extend_a_lost_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr(SQLAlchemyLocationValidationStore, "_owned", AsyncMock(return_value=None))
    await SQLAlchemyLocationValidationStore(_factory(session)).defer(
        _claim(), reason="quota", next_attempt=NOW, failure=False, now=NOW
    )
    session.execute.assert_not_called()


async def test_validation_canary_advance_is_a_noop_while_observing() -> None:
    session = MagicMock()
    await SQLAlchemyLocationValidationStore(_factory(session))._advance_canary(  # noqa: SLF001 - rollout guard
        session, MagicMock(__getitem__=lambda _self, key: {"mode": "observe"}[key])
    )
    session.execute.assert_not_called()


async def test_validation_control_refuses_unknown_modes_before_database_access() -> None:
    session = MagicMock()
    with pytest.raises(ValueError, match="unknown validation mode"):
        await SQLAlchemyLocationValidationStore(_factory(session)).control(
            target="synthetic", mode="unknown"
        )
    session.execute.assert_not_called()


@pytest.mark.parametrize("mode", ["not_paused", "missing_location", "missing_predecessor"])
async def test_validation_rollback_preserves_quarantine_without_valid_predecessor(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = {
        "display_address": "ul. Testowa 1, Warszawa",
        "normalized_address_hash": "a" * 64,
        "district": None,
        "city": "Warszawa",
        "country_code": "PL",
        "actor_type": "automatic_policy",
        "actor_id": None,
        "review_status": "needs_review",
        "precision": "unknown",
        "confidence": Decimal(0),
        "selected_geocode_result_id": None,
        "longitude": None,
        "latitude": None,
        "out_of_scope": False,
        "selection_version": 1,
    }
    # These are retained receipt inputs; the test changes only predecessor availability.
    snapshot = validation_module._snapshot(MagicMock(__getitem__=lambda _self, key: row[key]))  # noqa: SLF001 - receipt fixture
    fingerprint = validation_module._fingerprint(  # noqa: SLF001 - receipt fixture
        {
            key: row[key]
            for key in (
                "display_address",
                "normalized_address_hash",
                "district",
                "city",
                "country_code",
            )
        }
    )
    receipt = {
        "work_id": uuid4(),
        "location_id": uuid4(),
        "source_fingerprint": fingerprint,
        "before_json": {"result_id": str(uuid4())},
        "after_json": snapshot,
    }
    receipts = MagicMock()
    receipts.mappings.return_value.all.return_value = [receipt]
    current = MagicMock()
    current.mappings.return_value.one.return_value = row
    session = MagicMock(
        scalar=AsyncMock(
            side_effect=[
                "apply" if mode == "not_paused" else "off",
                None if mode == "missing_location" else LocationRow(id=receipt["location_id"]),
            ]
        ),
        execute=AsyncMock(side_effect=[receipts, current]),
    )
    monkeypatch.setattr(SQLAlchemyLocationValidationStore, "control", AsyncMock())
    record = AsyncMock()
    monkeypatch.setattr(SQLAlchemyLocationValidationStore, "_receipt", record)
    geocodes = MagicMock(result_in_session=AsyncMock(return_value=None))
    monkeypatch.setattr(validation_module, "SQLAlchemyGeocodeStore", lambda _factory: geocodes)
    store = SQLAlchemyLocationValidationStore(_factory(session))
    if mode == "not_paused":
        with pytest.raises(ValueError, match="requires paused validation"):
            await store.rollback(target="synthetic")
    else:
        assert await store.rollback(target="synthetic") == (
            {"retained_quarantine": 1} if mode == "missing_predecessor" else {}
        )
        assert record.await_count == int(mode == "missing_predecessor")
