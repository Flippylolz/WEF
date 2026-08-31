"""Tests for the telegram-worker recurring geocode background loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest
from pydantic import SecretStr

from wef_backend.features.ingestion.application.complete_import import ProviderDailyBudgetError
from wef_backend.features.ingestion.application.recurring_geocode import RecurringDeferAction
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    LocationWorkItem,
)
from wef_backend.recurring_geocode_worker import (
    RecurringGeocodeWorker,
    maintain_recurring_geocode,
)
from wef_backend.settings import Settings


@dataclass
class _FakeRepository:
    """Minimal repository surface for recurring geocode worker tests."""

    channel_id: object
    pending: tuple[LocationWorkItem, ...]

    async def resolve_source_channel_id(self, _channel: object) -> object:
        return self.channel_id

    async def pending_locations(self) -> tuple[LocationWorkItem, ...]:
        return self.pending

    async def recurring_geocode_run_id(self, **_kwargs: object) -> object:
        return uuid4()


class _ResolverRaisesBudget:
    async def __call__(self, **_kwargs: object) -> None:
        raise ProviderDailyBudgetError


@pytest.mark.asyncio
async def test_process_once_skips_without_api_key() -> None:
    worker = RecurringGeocodeWorker(
        settings=Settings(),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )
    result = await worker.process_once()
    assert result.skipped
    assert result.processed == 0


@pytest.mark.asyncio
async def test_process_once_defers_until_next_utc_day_on_budget_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = LocationWorkItem(uuid4(), "ul. Testowa 1", "Mokotów")
    fake_repo = _FakeRepository(channel_id=uuid4(), pending=(item,))
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.SQLAlchemyCompleteImportRepository",
        lambda _factory: fake_repo,
    )
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.ResolveGeocode",
        lambda *_args, **_kwargs: _ResolverRaisesBudget(),
    )
    worker = RecurringGeocodeWorker(
        settings=Settings(geoapify_api_key=_secret("test-key")),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )

    result = await worker.process_once()
    assert result.defer_action is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY

    second = await worker.process_once()
    assert second.skipped
    assert second.processed == 0


@pytest.mark.asyncio
async def test_process_once_refreshes_catalog_after_geocoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = LocationWorkItem(uuid4(), "ul. Testowa 1", "Mokotów")
    fake_repo = _FakeRepository(channel_id=uuid4(), pending=(item,))
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.SQLAlchemyCompleteImportRepository",
        lambda _factory: fake_repo,
    )
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.ResolveGeocode",
        lambda *_args, **_kwargs: _SuccessfulResolver(),
    )

    refresh_calls: list[int] = []

    async def _refresh(_self: RecurringGeocodeWorker) -> tuple[int, int]:
        refresh_calls.append(1)
        return 2, 3

    monkeypatch.setattr(RecurringGeocodeWorker, "_refresh_live_catalog", _refresh)
    worker = RecurringGeocodeWorker(
        settings=Settings(geoapify_api_key=_secret("test-key")),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )

    result = await worker.process_once()
    assert result.processed == 1
    assert result.locations_accepted == 2
    assert result.offers_promoted == 3
    assert refresh_calls == [1]


class _SuccessfulResolver:
    async def __call__(self, **_kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_maintain_recurring_geocode_runs_until_stop() -> None:
    calls = 0

    class _Worker:
        async def process_once(self) -> object:
            nonlocal calls
            calls += 1
            return object()

    stop = asyncio.Event()
    task = asyncio.create_task(
        maintain_recurring_geocode(_Worker(), stop=stop, interval=0.01),  # type: ignore[arg-type]
    )
    for _ in range(50):
        if calls >= 2:
            break
        await asyncio.sleep(0.02)
    stop.set()
    await task
    assert calls >= 2


def _secret(value: str) -> SecretStr:
    return SecretStr(value)
