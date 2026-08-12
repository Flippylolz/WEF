"""Tests for lazy runtime wiring and deterministic tooling."""

import json
from pathlib import Path
from typing import Any

import pytest

from wef_backend import cli
from wef_backend.app import create_app
from wef_backend.database import create_database_resources
from wef_backend.openapi_export import export_openapi
from wef_backend.settings import Settings, load_settings


async def test_database_resources_are_lazy() -> None:
    """Create and dispose an engine without contacting its invalid host."""
    database = create_database_resources("postgresql+asyncpg://invalid.invalid/wef_proof")

    assert database.session_factory.kw["expire_on_commit"] is False

    await database.engine.dispose()


async def test_runtime_app_composes_without_connecting() -> None:
    """Build and close the runtime app without requiring a database."""
    app = create_app()

    async with app.router.lifespan_context(app):
        assert app.docs_url is None


def test_settings_loader_returns_typed_defaults() -> None:
    """Load the environment-backed settings only when requested."""
    settings = load_settings()

    assert settings.port == 8000


def test_openapi_export_is_deterministic(tmp_path: Path) -> None:
    """Write identical sorted JSON for repeated offline exports."""
    destination = tmp_path / "v1.json"

    export_openapi(destination)
    first_export = destination.read_text(encoding="utf-8")
    export_openapi(destination)

    assert destination.read_text(encoding="utf-8") == first_export
    assert json.loads(first_export)["info"]["title"] == "WEF synthetic backend proof"


def test_serve_uses_uvicorn_application_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass typed settings to Uvicorn without constructing the app in the CLI."""
    invocation: dict[str, Any] = {}

    def fake_run(application: str, **options: object) -> None:
        invocation["application"] = application
        invocation.update(options)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings(port=8123))
    monkeypatch.setattr("wef_backend.cli.uvicorn.run", fake_run)

    cli.serve()

    assert invocation["application"] == "wef_backend.app:create_app"
    assert invocation["factory"] is True
    assert invocation["port"] == 8123
