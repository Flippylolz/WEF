"""Fenced E26 repair against disposable PostGIS; coordinates are synthetic only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_geocode_address_accuracy import _feature
from tests.test_geocoding import FakeTransport, _policy
from tests.test_geocoding_integration import TEST_DATABASE_URL, _prepare
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.application.location_revalidation import (
    VALIDATION_TARGET,
    RevalidateLocations,
)
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import HostedGeocoder
from wef_backend.features.ingestion.infrastructure.location_validation_store import (
    SQLAlchemyLocationValidationStore,
)

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.database import DatabaseResources

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]
NOW = datetime(2030, 1, 1, tzinfo=UTC)
SOURCE = "ul. Jugosłowiańska | Gocław"


async def _fixture() -> tuple[
    DatabaseResources, UUID, SQLAlchemyLocationValidationStore, ResolveGeocode, FakeTransport
]:
    database, location = await _prepare()
    async with database.session_factory() as session:
        await session.execute(
            text("DELETE FROM offers WHERE location_id != :id"), {"id": location.id}
        )
        await session.execute(text("DELETE FROM locations WHERE id != :id"), {"id": location.id})
        await session.execute(text("DELETE FROM location_validation_control"))
        await session.execute(
            text(
                "UPDATE locations SET display_address=:source, district='Praga-Południe', "
                "display_name='Old Gocław' WHERE id=:id"
            ),
            {"source": SOURCE, "id": location.id},
        )
        await session.commit()
    transport = FakeTransport([{"features": [_feature()]}] * 2)
    resolver = ResolveGeocode(
        SQLAlchemyGeocodeStore(database.session_factory),
        HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="synthetic"),
    )
    return (
        database,
        location.id,
        SQLAlchemyLocationValidationStore(database.session_factory),
        resolver,
        transport,
    )


async def _point(database: DatabaseResources, location: UUID) -> tuple[object, ...]:
    async with database.session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT ST_X(point),ST_Y(point),review_status,display_name "
                    "FROM locations WHERE id=:id"
                ),
                {"id": location},
            )
        ).one()
        return tuple(row)


async def test_observation_apply_receipts_and_second_run_noop() -> None:
    database, location, store, resolver, transport = await _fixture()
    before = await _point(database, location)
    result = await RevalidateLocations(store, resolver).run()
    assert result["validated"] == 1
    assert await _point(database, location) == before
    assert len(transport.calls) == 1
    await store.control(
        target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
    )
    applied = await RevalidateLocations(store, resolver).run()
    assert applied["corrected"] == 1
    after = await _point(database, location)
    assert after[:2] == pytest.approx((21.01, 52.23))
    assert str(after[3]).endswith("Warszawa")
    assert len(transport.calls) == 1  # Application reuses sufficient current cache evidence.
    assert (await RevalidateLocations(store, resolver).run())["processed"] == 0
    async with database.session_factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM location_validation_receipts")) == 2
        assert await session.scalar(text("SELECT count(*) FROM location_validation_work")) == 1
    status = await store.status(target=VALIDATION_TARGET)
    assert not status["control"]["canary_verified"]
    await store.verify_canary(target=VALIDATION_TARGET)
    assert (await store.status(target=VALIDATION_TARGET))["control"]["canary_verified"]
    await database.engine.dispose()


async def test_expired_lease_is_taken_over_and_old_worker_cannot_publish() -> None:
    database, location, store, resolver, _ = await _fixture()
    await store.discover(target=VALIDATION_TARGET, now=NOW)
    first = await store.claim(target=VALIDATION_TARGET, now=NOW)
    assert first is not None
    assert await store.claim(target=VALIDATION_TARGET, now=NOW + timedelta(seconds=1)) is None
    second = await store.claim(target=VALIDATION_TARGET, now=NOW + timedelta(seconds=121))
    assert second is not None
    assert second.fence > first.fence
    result = await resolver(source_query=SOURCE, district="Praga-Południe")
    assert await store.finish(first, result, now=NOW + timedelta(seconds=122)) == "stale_lease"
    assert not await store.renew(first, now=NOW + timedelta(seconds=122))
    assert await store.renew(second, now=NOW + timedelta(seconds=122))
    assert await store.finish(second, result, now=NOW + timedelta(seconds=123)) == "validated"
    assert (await _point(database, location))[3] == "Old Gocław"
    await database.engine.dispose()


@pytest.mark.parametrize("change", ["source", "owner", "selection"])
async def test_concurrent_changes_guard_the_completion(change: str) -> None:
    database, location, store, resolver, _ = await _fixture()
    await store.discover(target=VALIDATION_TARGET, now=NOW)
    claim = await store.claim(target=VALIDATION_TARGET, now=NOW)
    assert claim is not None
    before = await _point(database, location)
    async with database.session_factory() as session:
        if change == "source":
            await session.execute(
                text("UPDATE locations SET display_address='ul. Inna 1' WHERE id=:id"),
                {"id": location},
            )
        else:
            await session.execute(
                text("""
                INSERT INTO location_geocode_selections(id,location_id,from_state,to_state,
                    reason_code,actor_type,actor_id,review_policy_version,selection_version,decided_at)
                VALUES (:id,:location,'accepted','accepted','manual_accept',:actor,'owner',
                    'warsaw-review-v1',1,now())
            """),
                {
                    "id": uuid4(),
                    "location": location,
                    "actor": "operator" if change == "owner" else "automatic_policy",
                },
            )
        await session.commit()
    result = await resolver(source_query=SOURCE, district="Praga-Południe")
    outcome = await store.finish(claim, result, now=NOW + timedelta(seconds=1))
    assert (
        outcome
        == {"source": "source_changed", "owner": "protected", "selection": "selection_changed"}[
            change
        ]
    )
    assert await _point(database, location) == before
    if change == "source":
        assert await store.discover(target=VALIDATION_TARGET, now=NOW) == 1
    await database.engine.dispose()


async def test_quota_is_durable_and_transient_failures_are_bounded() -> None:
    database, _, store, _, _ = await _fixture()
    await store.discover(target=VALIDATION_TARGET, now=NOW)
    claim = await store.claim(target=VALIDATION_TARGET, now=NOW)
    assert claim is not None
    tomorrow = NOW + timedelta(days=1)
    await store.defer(claim, reason="quota", next_attempt=tomorrow, failure=False, now=NOW)
    assert await store.claim(target=VALIDATION_TARGET, now=NOW + timedelta(hours=1)) is None
    for failure in range(5):
        claim = await store.claim(
            target=VALIDATION_TARGET, now=tomorrow + timedelta(minutes=failure)
        )
        assert claim is not None
        assert claim.failures == failure
        await store.defer(
            claim,
            reason="transient",
            next_attempt=tomorrow + timedelta(minutes=failure + 1),
            failure=True,
            now=tomorrow + timedelta(minutes=failure),
        )
    assert await store.claim(target=VALIDATION_TARGET, now=tomorrow + timedelta(hours=1)) is None
    assert (await store.status(target=VALIDATION_TARGET))["states"][0]["state"] == "exception"
    await database.engine.dispose()


async def test_apply_requires_observed_canaries_and_discovery_readiness() -> None:
    database, location, store, _, _ = await _fixture()
    with pytest.raises(ValueError, match="application requires"):
        await store.control(target=VALIDATION_TARGET, mode="apply", canary_ids=(location,))
    with pytest.raises(ValueError, match="completed observation"):
        await store.control(
            target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
        )
    await store.control(target=VALIDATION_TARGET, mode="off")
    assert await store.discover(target=VALIDATION_TARGET, now=NOW) == 0
    assert await store.claim(target=VALIDATION_TARGET, now=NOW) is None
    await database.engine.dispose()


async def test_new_policy_generation_discovers_old_accepted_points_and_fences_old_work() -> None:
    database, _, store, _, _ = await _fixture()
    assert await store.discover(target="old-policy", now=NOW) == 1
    old = await store.claim(target="old-policy", now=NOW)
    assert old is not None
    assert await store.discover(target=VALIDATION_TARGET, now=NOW) == 1
    assert not await store.renew(old, now=NOW + timedelta(seconds=1))
    assert await store.claim(target="old-policy", now=NOW + timedelta(seconds=121)) is None
    assert await store.claim(target=VALIDATION_TARGET, now=NOW) is not None
    await database.engine.dispose()


async def test_application_receipt_failure_rolls_back_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, location, store, resolver, _ = await _fixture()
    await RevalidateLocations(store, resolver).run()
    await store.control(
        target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
    )
    claim = await store.claim(target=VALIDATION_TARGET, now=NOW)
    assert claim is not None
    result = await resolver(source_query=SOURCE, district="Praga-Południe")
    before = await _point(database, location)

    async def fail_receipt(*_args: object, **_kwargs: object) -> None:
        message = "injected receipt failure"
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(SQLAlchemyLocationValidationStore, "_receipt", fail_receipt)
        with pytest.raises(RuntimeError, match="receipt failure"):
            await store.finish(claim, result, now=NOW + timedelta(seconds=1))
    assert await _point(database, location) == before
    assert await store.finish(claim, result, now=NOW + timedelta(seconds=2)) == "corrected"
    async with database.session_factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM location_geocode_selections")) == 1
    await database.engine.dispose()


async def test_wrong_street_quarantine_preserves_offers_and_favorites() -> None:
    database, location, store, _, transport = await _fixture()
    user = uuid4()
    async with database.session_factory() as session:
        await session.execute(
            text("""
            INSERT INTO users(id,username_normalized,username_display,hashed_password,
                role,is_active,must_change_password)
            VALUES (:id,:username,:username,'synthetic-unused-hash','user',true,false)
        """),
            {"id": user, "username": str(user)},
        )
        await session.execute(
            text("INSERT INTO favorite_locations(user_id,location_id) VALUES (:user,:location)"),
            {"user": user, "location": location},
        )
        offers = (
            await session.execute(
                text("SELECT id,visibility FROM offers WHERE location_id=:id ORDER BY id"),
                {"id": location},
            )
        ).all()
        await session.commit()
    transport.payloads = [{"features": [_feature("Grochowska", result_type="amenity")]}] * 2
    resolver = ResolveGeocode(
        SQLAlchemyGeocodeStore(database.session_factory),
        HostedGeocoder(GeocodeProvider.GEOAPIFY, transport, _policy(), api_key="synthetic"),
    )
    assert (await RevalidateLocations(store, resolver).run())["unresolved"] == 1
    await store.control(
        target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
    )
    assert (await RevalidateLocations(store, resolver).run())["unresolved"] == 1
    assert (await _point(database, location))[:3] == (None, None, "needs_review")
    async with database.session_factory() as session:
        assert (
            await session.execute(
                text("SELECT id,visibility FROM offers WHERE location_id=:id ORDER BY id"),
                {"id": location},
            )
        ).all() == offers
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM favorite_locations WHERE user_id=:user "
                    "AND location_id=:location"
                ),
                {"user": user, "location": location},
            )
            == 1
        )
        await session.execute(text("DELETE FROM users WHERE id=:id"), {"id": user})
        await session.commit()
    await database.engine.dispose()


async def test_discovery_skips_protected_owner_without_spending_provider_quota() -> None:
    database, location, store, resolver, transport = await _fixture()
    async with database.session_factory() as session:
        await session.execute(
            text("""
            INSERT INTO location_geocode_selections(id,location_id,from_state,to_state,
                reason_code,actor_type,actor_id,review_policy_version,selection_version,decided_at)
            VALUES (:id,:location,'accepted','accepted','manual_accept','operator','owner',
                'warsaw-review-v1',1,now())
        """),
            {"id": uuid4(), "location": location},
        )
        await session.commit()
    assert (await RevalidateLocations(store, resolver).run())["processed"] == 0
    assert not transport.calls
    status = await store.status(target=VALIDATION_TARGET)
    assert status["states"][0]["outcome"] == "protected"
    await database.engine.dispose()


async def test_pause_resume_fences_inflight_work_and_canary_requires_completed_apply() -> None:
    database, location, store, resolver, _ = await _fixture()
    await store.discover(target=VALIDATION_TARGET, now=NOW)
    claim = await store.claim(target=VALIDATION_TARGET, now=NOW)
    assert claim is not None
    await store.control(target=VALIDATION_TARGET, mode="off")
    await store.control(target=VALIDATION_TARGET, mode="observe")
    assert not await store.renew(claim, now=NOW + timedelta(seconds=1))
    with pytest.raises(ValueError, match="active application"):
        await store.verify_canary(target=VALIDATION_TARGET)
    await RevalidateLocations(store, resolver).run()
    await store.control(
        target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
    )
    with pytest.raises(ValueError, match="completed application"):
        await store.verify_canary(target=VALIDATION_TARGET)
    await database.engine.dispose()


@pytest.mark.parametrize("case", ["valid", "invalid", "edited", "missing"])
async def test_rollback_only_restores_unchanged_valid_predecessor(case: str) -> None:
    database, location, store, resolver, _ = await _fixture()
    if case != "missing":
        await resolver(source_query=SOURCE, district="Praga-Południe", location_id=location)
    await RevalidateLocations(store, resolver).run()
    await store.control(
        target=VALIDATION_TARGET, mode="apply", canary_ids=(location,), discovery_ready=True
    )
    await RevalidateLocations(store, resolver).run()
    async with database.session_factory() as session:
        if case == "invalid":
            await session.execute(text("UPDATE geocode_results SET response_json='{}'"))
        elif case == "edited":
            await session.execute(
                text("UPDATE locations SET display_address='ul. Edited 1' WHERE id=:id"),
                {"id": location},
            )
        await session.commit()
    expected = {
        "valid": "restored_valid_predecessor",
        "invalid": "retained_quarantine",
        "edited": "edited_or_protected",
        "missing": "retained_quarantine",
    }[case]
    assert await store.rollback(target=VALIDATION_TARGET) == {expected: 1}
    assert await store.rollback(target=VALIDATION_TARGET) == {}
    assert (await store.status(target=VALIDATION_TARGET))["control"]["mode"] == "off"
    await database.engine.dispose()
