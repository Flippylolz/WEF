"""Tests for lazy runtime wiring and deterministic tooling."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from wef_backend import cli, geocoder_check, migration, seed_command
from wef_backend.app import create_app
from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import (
    ProductionSeedError,
    SeedLocation,
    SeedOffer,
    SeedResult,
)
from wef_backend.features.estates.infrastructure import RetiredEstateQueryAdapter
from wef_backend.openapi_export import export_openapi
from wef_backend.settings import Settings, load_settings


async def test_database_resources_are_lazy() -> None:
    """Create and dispose an engine without contacting its invalid host."""
    database = create_database_resources("postgresql+asyncpg://invalid.invalid/wef_proof")

    assert database.session_factory.kw["expire_on_commit"] is False

    await database.engine.dispose()


async def test_retired_estate_adapter_avoids_obsolete_persistence() -> None:
    """Keep the deprecated additive route inert during frontend migration."""
    assert await RetiredEstateQueryAdapter().list_estate_records() == ()


async def test_runtime_app_composes_without_connecting() -> None:
    """Build and close the runtime app without requiring a database."""
    app = create_app()

    async with app.router.lifespan_context(app):
        assert app.docs_url is None


def test_settings_loader_returns_typed_defaults() -> None:
    """Load the environment-backed settings only when requested."""
    settings = load_settings()

    assert settings.port == 8000
    assert settings.env == "development"
    assert settings.geoapify_requests_per_second == 4
    assert settings.geoapify_daily_quota == 2_700
    assert settings.ai_curation_enabled is False
    assert settings.groq_api_key is None
    assert settings.groq_zdr_verified is False
    assert settings.groq_model == "openai/gpt-oss-20b"


@dataclass
class FakeGeocoderTransport:
    """Return one public, sanitized Geoapify-shaped response."""

    payload: object

    async def get_json(
        self,
        _url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> object:
        """Prove the command supplies a key without exposing it in output."""
        assert params["apiKey"] == "fixture-secret-key-0123456789"
        assert headers["User-Agent"]
        assert timeout_seconds == 15
        return self.payload


async def test_geoapify_check_is_bounded_and_secret_safe() -> None:
    """The operator check validates one mapped Warsaw result without secret output."""
    settings = Settings(geoapify_api_key=SecretStr("fixture-secret-key-0123456789"))
    result = await geocoder_check.check_geoapify(
        settings,
        transport=FakeGeocoderTransport(
            {
                "features": [
                    {
                        "geometry": {"coordinates": [21.0058, 52.2318]},
                        "properties": {
                            "place_id": "public-check",
                            "formatted": "Warszawa",
                            "result_type": "building",
                            "rank": {"confidence": 1},
                        },
                    },
                ],
            },
        ),
    )

    assert result == {
        "attribution": "© OpenStreetMap contributors; Geoapify",
        "precision": "building",
        "provider": "geoapify",
        "status": "ok",
        "within_scope": True,
    }
    assert "fixture-secret-key" not in repr(settings)


async def test_geoapify_check_fails_closed_without_configuration() -> None:
    """A missing production secret fails before any network request."""
    with pytest.raises(geocoder_check.GeoapifyCheckError, match="not configured"):
        await geocoder_check.check_geoapify(Settings())


def test_openapi_export_is_deterministic(tmp_path: Path) -> None:
    """Write identical sorted JSON for repeated offline exports."""
    destination = tmp_path / "v1.json"

    export_openapi(destination)
    first_export = destination.read_text(encoding="utf-8")
    export_openapi(destination)

    assert destination.read_text(encoding="utf-8") == first_export
    assert json.loads(first_export)["info"]["title"] == "Warsaw Estate Finder API"


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
    assert invocation["proxy_headers"] is True
    assert invocation["forwarded_allow_ips"] == "127.0.0.1"


def test_serve_trusts_forwarded_headers_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production API peers are Docker networks, so trust all forwarded peers."""
    invocation: dict[str, Any] = {}

    def fake_run(application: str, **options: object) -> None:
        invocation["application"] = application
        invocation.update(options)

    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: Settings(port=8123, env="production"),
    )
    monkeypatch.setattr("wef_backend.cli.uvicorn.run", fake_run)

    cli.serve()

    assert invocation["forwarded_allow_ips"] == "*"


def test_alembic_config_uses_runtime_database_url() -> None:
    """Inject the database URL without writing it to Alembic configuration."""
    config_path = Path(__file__).parents[1] / "alembic.ini"
    config = migration.alembic_config(
        Settings(
            alembic_config=config_path,
            database_url="postgresql+asyncpg://wef:p%25@db/wef",
        ),
    )

    assert config.get_main_option("sqlalchemy.url") == ("postgresql+asyncpg://wef:p%25@db/wef")


def test_migrate_upgrades_to_head(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run only the forward Alembic upgrade command."""
    calls: list[tuple[object, str]] = []
    settings = Settings(alembic_config=Path(__file__).parents[1] / "alembic.ini")
    monkeypatch.setattr(migration, "load_settings", lambda: settings)
    monkeypatch.setattr(
        migration.alembic_command,
        "upgrade",
        lambda config, revision: calls.append((config, revision)),
    )

    migration.migrate()

    assert calls[0][1] == "head"


class FakeSeedAdapter:
    """Return fixture counts without persistence."""

    async def upsert_seed(
        self,
        locations: Sequence[SeedLocation],
        offers: Sequence[SeedOffer],
    ) -> SeedResult:
        """Return supplied reconciliation counts."""
        return SeedResult(locations=len(locations), offers=len(offers))


class FakeEngine:
    """Record deterministic resource disposal."""

    def __init__(self) -> None:
        """Initialize disposal state."""
        self.disposed = False

    async def dispose(self) -> None:
        """Record disposal."""
        self.disposed = True


@dataclass
class FakeDatabase:
    """Minimum database resource shape needed by the seed command."""

    engine: FakeEngine
    session_factory: object


async def test_seed_command_emits_counts_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command emits bounded JSON and always disposes its engine."""
    database = FakeDatabase(engine=FakeEngine(), session_factory=object())
    monkeypatch.setattr(seed_command, "load_settings", lambda: Settings(env="test"))
    monkeypatch.setattr(seed_command, "create_database_resources", lambda _url: database)
    monkeypatch.setattr(
        seed_command,
        "SQLAlchemyCatalogSeedAdapter",
        lambda _factory: FakeSeedAdapter(),
    )

    await seed_command.seed()

    assert json.loads(capsys.readouterr().out) == {"locations": 4, "offers": 5}
    assert database.engine.disposed is True


def test_seed_main_reports_guard_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A production guard exits non-zero with one safe message."""
    error = ProductionSeedError("synthetic seed disabled")

    async def reject_seed() -> None:
        raise error

    monkeypatch.setattr(seed_command, "seed", reject_seed)

    with pytest.raises(SystemExit) as raised:
        seed_command.main()

    assert raised.value.code == 2
    assert capsys.readouterr().err == "synthetic seed disabled\n"
