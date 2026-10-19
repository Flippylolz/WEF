"""Tests for the telegram-worker recurring geocode background loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from wef_backend.features.ingestion.application.location_revalidation import LimitedGeocoder


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
        "wef_backend.recurring_geocode_worker.build_location_resolver",
        lambda *_args, **_kwargs: _ResolverRaisesBudget(),
    )

    async def _noop_refresh(_self: RecurringGeocodeWorker) -> tuple[int, int]:
        return 0, 0

    monkeypatch.setattr(RecurringGeocodeWorker, "_refresh_live_catalog", _noop_refresh)
    worker = RecurringGeocodeWorker(
        settings=Settings(geoapify_api_key=_secret("test-key"), geocode_revalidation_enabled=False),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )

    result = await worker.process_once()
    assert result.defer_action is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY

    second = await worker.process_once()
    assert not second.skipped
    assert second.defer_action is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY
    assert second.processed == 0


@pytest.mark.asyncio
async def test_process_once_refreshes_catalog_when_queue_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_repo = _FakeRepository(channel_id=uuid4(), pending=())
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.SQLAlchemyCompleteImportRepository",
        lambda _factory: fake_repo,
    )
    refresh_calls: list[int] = []

    async def _refresh(_self: RecurringGeocodeWorker) -> tuple[int, int]:
        refresh_calls.append(1)
        return 0, 1

    monkeypatch.setattr(RecurringGeocodeWorker, "_refresh_live_catalog", _refresh)
    worker = RecurringGeocodeWorker(
        settings=Settings(geoapify_api_key=_secret("test-key"), geocode_revalidation_enabled=False),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )

    result = await worker.process_once()
    assert result.processed == 0
    assert result.offers_promoted == 1
    assert refresh_calls == [1]


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
        "wef_backend.recurring_geocode_worker.build_location_resolver",
        lambda *_args, **_kwargs: _SuccessfulResolver(),
    )

    refresh_calls: list[int] = []

    async def _refresh(_self: RecurringGeocodeWorker) -> tuple[int, int]:
        refresh_calls.append(1)
        return 2, 3

    monkeypatch.setattr(RecurringGeocodeWorker, "_refresh_live_catalog", _refresh)
    worker = RecurringGeocodeWorker(
        settings=Settings(geoapify_api_key=_secret("test-key"), geocode_revalidation_enabled=False),
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


@pytest.mark.asyncio
async def test_catalog_refresh_only_promotes_already_validated_locations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refreshing discovery cannot bypass the address policy with AD-034 acceptance."""

    class PromotionOnly:
        async def promote_map_ready_offers(self) -> int:
            return 3

    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.SQLAlchemyPromotePublicCatalogAdapter",
        lambda _factory: PromotionOnly(),
    )
    worker = RecurringGeocodeWorker(
        settings=Settings(),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )
    assert await worker._refresh_live_catalog() == (0, 3)  # noqa: SLF001


@pytest.mark.parametrize(
    ("foreground", "cap", "share"), [(True, 10, 5), (False, 10, 10), (True, 1, 0)]
)
async def test_revalidation_reserves_foreground_share_of_one_budget(
    monkeypatch: pytest.MonkeyPatch, *, foreground: bool, cap: int, share: int
) -> None:
    item = LocationWorkItem(uuid4(), "ul. Testowa 1", "Mokotów")
    repository = _FakeRepository(uuid4(), (item,) if foreground else ())
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.SQLAlchemyCompleteImportRepository",
        lambda _factory: repository,
    )
    budget = object()
    seen: list[object] = []

    async def make_budget(*_args: object) -> object:
        return budget

    async def run_revalidation(_self: object, shared: object, allowance: int) -> None:
        assert shared is budget
        assert allowance == share
        seen.append(shared)

    async def resolve(**_kwargs: object) -> None:
        return None

    def make_resolver(_store: object, limited: LimitedGeocoder, _settings: Settings) -> object:
        assert limited.geocoder is budget
        assert limited.limit == min(cap, 25) - share
        return resolve

    async def refresh(_self: object) -> tuple[int, int]:
        return 0, 0

    monkeypatch.setattr(RecurringGeocodeWorker, "_budgeted_geocoder", make_budget)
    monkeypatch.setattr(RecurringGeocodeWorker, "_run_revalidation", run_revalidation)
    monkeypatch.setattr(RecurringGeocodeWorker, "_refresh_live_catalog", refresh)
    monkeypatch.setattr(
        "wef_backend.recurring_geocode_worker.build_location_resolver", make_resolver
    )
    worker = RecurringGeocodeWorker(
        settings=Settings(
            geoapify_api_key=_secret("synthetic"), telegram_recurring_geocode_batch_size=cap
        ),
        session_factory=object(),  # type: ignore[arg-type]
        channel=default_live_channel_identity(),
    )
    result = await worker.process_once()
    assert result.processed == int(foreground)
    assert len(seen) == 1
