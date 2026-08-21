"""Tests for accepting in-scope pending geocode pins."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

import wef_backend.accept_pending_geocode_pins_command as command
from wef_backend.features.ingestion.application.accept_pending_geocode_pins import (
    AcceptPendingGeocodePins,
    AcceptPendingGeocodePinsResult,
)
from wef_backend.settings import Settings


@dataclass
class _FakeStore:
    accepted: int = 10
    map_locations: int = 100
    remaining_review: int = 3
    ungeocoded: int = 9
    calls: list[str] = field(default_factory=list)

    async def accept_in_scope_pending_pins(self) -> int:
        self.calls.append("accept")
        return self.accepted

    async def count_map_eligible_locations(self) -> int:
        self.calls.append("map")
        return self.map_locations

    async def count_needs_review_without_point(self) -> int:
        self.calls.append("review")
        return self.remaining_review

    async def count_ungeocoded(self) -> int:
        self.calls.append("ungeocoded")
        return self.ungeocoded


@pytest.mark.asyncio
async def test_accept_pending_geocode_pins_orders_calls() -> None:
    store = _FakeStore()
    result = await AcceptPendingGeocodePins(store)()
    assert result == AcceptPendingGeocodePinsResult(
        locations_accepted=10,
        map_eligible_locations=100,
        remaining_needs_review_without_point=3,
        remaining_ungeocoded=9,
    )
    assert store.calls == ["accept", "map", "review", "ungeocoded"]


class _FakeEngine:
    async def dispose(self) -> None:
        return None


class _FakeDatabase:
    def __init__(self) -> None:
        self.engine = _FakeEngine()
        self.session_factory = object()


class _FakeAccept:
    def __init__(self, _store: object) -> None:
        return None

    async def __call__(self) -> AcceptPendingGeocodePinsResult:
        return AcceptPendingGeocodePinsResult(
            locations_accepted=1,
            map_eligible_locations=50,
            remaining_needs_review_without_point=0,
            remaining_ungeocoded=9,
        )


def test_command_main_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run() -> dict[str, int]:
        return {
            "locations_accepted": 2,
            "map_eligible_locations": 60,
            "remaining_needs_review_without_point": 1,
            "remaining_ungeocoded": 9,
        }

    monkeypatch.setattr(command, "run", fake_run)
    command.main()
    assert '"locations_accepted": 2' in capsys.readouterr().out


@pytest.mark.asyncio
async def test_command_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        command,
        "load_settings",
        lambda: Settings(database_url="postgresql+asyncpg://unused/unused"),
    )
    monkeypatch.setattr(command, "create_database_resources", lambda _url: _FakeDatabase())
    monkeypatch.setattr(command, "AcceptPendingGeocodePins", _FakeAccept)
    payload = await command.run()
    assert payload["locations_accepted"] == 1
