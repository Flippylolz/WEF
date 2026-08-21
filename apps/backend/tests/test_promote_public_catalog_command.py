"""Unit coverage for the promote-public-catalog CLI entrypoint."""

from __future__ import annotations

import pytest

import wef_backend.promote_public_catalog_command as command
from wef_backend.features.catalog.application.promote_public_catalog import (
    PromotePublicCatalogResult,
)
from wef_backend.settings import Settings


class _FakeEngine:
    async def dispose(self) -> None:
        return None


class _FakeDatabase:
    def __init__(self) -> None:
        self.engine = _FakeEngine()
        self.session_factory = object()


class _FakePromote:
    def __init__(self, _store: object) -> None:
        return None

    async def __call__(self) -> PromotePublicCatalogResult:
        return PromotePublicCatalogResult(
            offers_promoted=1,
            synthetic_offers_hidden=5,
            synthetic_locations_rejected=4,
            visible_offers=10,
            map_eligible_locations=8,
        )


def _settings() -> Settings:
    return Settings(database_url="postgresql+asyncpg://unused/unused")


def _database(_url: str) -> _FakeDatabase:
    return _FakeDatabase()


@pytest.mark.asyncio
async def test_run_returns_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command, "load_settings", _settings)
    monkeypatch.setattr(command, "create_database_resources", _database)
    monkeypatch.setattr(command, "PromotePublicCatalog", _FakePromote)
    payload = await command.run()
    assert payload["offers_promoted"] == 1
    assert payload["synthetic_offers_hidden"] == 5


def test_main_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run() -> dict[str, int]:
        return {
            "offers_promoted": 2,
            "synthetic_offers_hidden": 5,
            "synthetic_locations_rejected": 4,
            "visible_offers": 20,
            "map_eligible_locations": 10,
        }

    monkeypatch.setattr(command, "run", fake_run)
    command.main()
    out = capsys.readouterr().out
    assert '"offers_promoted": 2' in out


def test_main_exits_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom() -> dict[str, int]:
        message = "db down"
        raise RuntimeError(message)

    monkeypatch.setattr(command, "run", boom)
    with pytest.raises(SystemExit) as raised:
        command.main()
    assert raised.value.code == 2
