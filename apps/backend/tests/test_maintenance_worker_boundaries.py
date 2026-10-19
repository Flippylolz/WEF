"""Maintenance loops retain live priority and survive bounded failures."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_recurring_geocode_worker import _FakeRepository
from wef_backend import automatic_recovery_worker as automatic
from wef_backend import recurring_geocode_worker as recurring
from wef_backend.features.ingestion.application.complete_import import ProviderBatchLimitError
from wef_backend.features.ingestion.application.recurring_geocode import RecurringDeferAction
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    LocationWorkItem,
)
from wef_backend.settings import Settings


def _worker() -> recurring.RecurringGeocodeWorker:
    return recurring.RecurringGeocodeWorker(
        Settings(geoapify_api_key=SecretStr("fixture"), geocode_revalidation_enabled=False),
        MagicMock(),
        default_live_channel_identity(),
    )


async def test_recurring_unknown_channel_does_not_consume_provider_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _FakeRepository(None, ())
    monkeypatch.setattr(recurring, "SQLAlchemyCompleteImportRepository", lambda _: repository)
    result = await _worker().process_once()
    assert result == recurring.RecurringGeocodeCycleResult(
        processed=0, pending=0, skipped=True, defer_action=None
    )


async def test_recurring_batch_limit_still_attempts_later_municipal_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = tuple(LocationWorkItem(uuid4(), f"Testowa {number}", "Mokotów") for number in (1, 2))
    monkeypatch.setattr(
        recurring, "SQLAlchemyCompleteImportRepository", lambda _: _FakeRepository(uuid4(), items)
    )
    resolve = AsyncMock(side_effect=[ProviderBatchLimitError(), None])
    monkeypatch.setattr(recurring, "build_location_resolver", lambda *_: resolve)
    monkeypatch.setattr(
        recurring.RecurringGeocodeWorker, "_refresh_live_catalog", AsyncMock(return_value=(0, 0))
    )
    result = await _worker().process_once()
    assert result.processed == result.pending == 1
    assert result.defer_action is None
    assert resolve.await_count == 2
    assert resolve.await_args_list[1].kwargs["location_id"] == items[1].location_id


@pytest.mark.parametrize("count", [0, 2])
async def test_recurring_revalidation_receives_shared_budget_and_logs_changes(
    count: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget, resolver = MagicMock(), MagicMock()
    monkeypatch.setattr(recurring, "build_location_resolver", lambda *_: resolver)
    run = AsyncMock(return_value={"checked": count})
    construct = MagicMock(return_value=SimpleNamespace(run=run))
    monkeypatch.setattr(recurring, "RevalidateLocations", construct)
    log = MagicMock()
    monkeypatch.setattr(recurring, "logger", log)
    await _worker()._run_revalidation(budget, 3)  # noqa: SLF001
    assert construct.call_args.args[1] is resolver
    assert construct.call_args.kwargs == {"independent_lookups": True}
    run.assert_awaited_once_with()
    assert log.info.call_count == int(count > 0)
    if count:
        log.info.assert_called_once_with("location_revalidation_cycle", checked=2)


async def test_recurring_no_promotions_returns_zero_without_change_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    promote = AsyncMock(return_value=0)
    monkeypatch.setattr(
        recurring,
        "SQLAlchemyPromotePublicCatalogAdapter",
        lambda _: SimpleNamespace(promote_map_ready_offers=promote),
    )
    log = MagicMock()
    monkeypatch.setattr(recurring, "logger", log)
    assert await _worker()._refresh_live_catalog() == (0, 0)  # noqa: SLF001
    log.info.assert_not_called()


@pytest.mark.parametrize("action", list(RecurringDeferAction))
def test_recurring_defer_deadline_uses_utc_and_leaves_other_actions_unchanged(
    action: RecurringDeferAction,
) -> None:
    worker = _worker()
    now = datetime(2026, 10, 19, 23, 55, tzinfo=UTC)
    worker._apply_defer(action, now=now)  # noqa: SLF001
    expected = {
        RecurringDeferAction.CONTINUE: None,
        RecurringDeferAction.LEAVE_UNGEOCODED: None,
        RecurringDeferAction.DEFER_TRANSIENT: now + timedelta(minutes=15),
        RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY: datetime(2026, 10, 20, tzinfo=UTC),
    }
    assert worker._defer_until == expected[action]  # noqa: SLF001


async def test_recurring_unexpected_failure_is_redacted_and_loop_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = asyncio.Event()
    process = AsyncMock(side_effect=[RuntimeError("private provider body"), None])

    async def cadence(interval: float) -> None:
        assert interval == 2
        if process.await_count == 2:
            stop.set()

    log = MagicMock()
    monkeypatch.setattr(recurring, "logger", log)
    monkeypatch.setattr(asyncio, "sleep", cadence)
    await recurring.maintain_recurring_geocode(
        MagicMock(process_once=process),
        stop=stop,
        interval=2,
    )
    assert process.await_count == 2
    assert log.error.call_args.args == ("recurring_geocode_cycle_failed",)
    assert "private" not in str(log.error.call_args)


@pytest.mark.parametrize(
    "mode", ["unauthorized", "database_failure", "owner_batch", "tick_failure"]
)
async def test_automatic_recovery_authorization_cohorts_and_failure_isolation(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, batch = uuid4(), uuid4()
    stop = asyncio.Event()
    session = MagicMock(scalar=AsyncMock())
    if mode == "database_failure":
        session.scalar.side_effect = SQLAlchemyError("private database detail")
    else:
        session.scalar.side_effect = [None] if mode == "unauthorized" else [owner, batch]
    admin = SimpleNamespace(
        generate_ingestion_ai_parse=AsyncMock(),
        apply_ingestion_ai_parse=AsyncMock(),
        start_offer_enrichment=AsyncMock(),
        process_offer_enrichment=AsyncMock(),
    )
    services = SimpleNamespace(admin=admin, close=AsyncMock())
    monkeypatch.setattr(automatic, "build_services", lambda _: services)
    backfill = AsyncMock()
    monkeypatch.setattr(automatic, "backfill_parse_issues", backfill)
    tick = AsyncMock(
        side_effect=RuntimeError("private failure") if mode == "tick_failure" else None
    )
    monkeypatch.setattr(automatic, "AutomaticRecovery", lambda *_: SimpleNamespace(tick=tick))
    log = MagicMock()
    monkeypatch.setattr(automatic, "logger", log)
    waits = 0

    async def cadence(awaitable: object, *, timeout: int) -> None:  # noqa: ASYNC109
        nonlocal waits
        assert timeout == 60
        waits += 1
        if waits == 1:
            awaitable.close()  # type: ignore[attr-defined]
            raise TimeoutError
        stop.set()
        await awaitable  # type: ignore[misc]

    # The second tick proves service reuse and suppresses identical status noise.
    if mode == "owner_batch":
        session.scalar.side_effect = [owner, batch, owner, batch]
    elif mode == "tick_failure":
        session.scalar.side_effect = [owner, owner]
    elif mode == "unauthorized":
        session.scalar.side_effect = [None, None]
    monkeypatch.setattr(asyncio, "wait_for", cadence)
    settings = Settings(
        ai_recovery_enabled=True,
        ai_recovery_activation_verified=True,
        ai_curation_enabled=True,
        groq_zdr_verified=True,
        groq_api_key=SecretStr("fixture"),
        ai_recovery_owner_id=owner,
    )
    await automatic.maintain_automatic_recovery(settings, _factory(session), stop, lambda: True)
    services.close.assert_awaited_once_with()
    assert log.info.call_count == 1
    expected = (
        "running"
        if mode == "owner_batch"
        else ("recovery_failed" if mode == "tick_failure" else "activation_unavailable")
    )
    log.info.assert_called_once_with("parser_recovery_status", status=expected)
    assert admin.process_offer_enrichment.await_count == (2 if mode == "owner_batch" else 0)
    if mode == "owner_batch":
        admin.process_offer_enrichment.assert_awaited_with(
            owner_id=owner,
            batch_id=batch,
            request_id=batch,
        )
