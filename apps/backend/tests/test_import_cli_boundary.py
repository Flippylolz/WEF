"""Historical import CLI keeps stable exits and source-free output."""

from __future__ import annotations

import argparse
import json
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from wef_backend import import_command
from wef_backend.features.ingestion.application.complete_import import CompleteImportStatus
from wef_backend.features.ingestion.infrastructure import CompleteImportLeaseHeldError
from wef_backend.operator import UnsafeSourceMountError
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.parametrize(
    ("error_factory", "exit_code", "expected"),
    [
        (RuntimeError, 2, "import failed: RuntimeError\n"),
        (UnsafeSourceMountError, 2, "import failed: UnsafeSourceMountError\n"),
        (CompleteImportLeaseHeldError, 2, "import failed: CompleteImportLeaseHeldError\n"),
        (
            KeyboardInterrupt,
            130,
            "import interrupted; resume after the five-minute lease expires\n",
        ),
    ],
)
def test_import_failure_is_redacted_with_stable_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error_factory: Callable[[str], BaseException],
    exit_code: int,
    expected: str,
) -> None:
    """An exception's private message never reaches stderr or stdout."""

    async def fail(_args: argparse.Namespace, _settings: Settings) -> dict[str, object]:
        msg = "private-source-contact-path-and-provider-secret"
        raise error_factory(msg)

    monkeypatch.setattr(sys, "argv", ["wef-import", "run"])
    monkeypatch.setattr(import_command, "load_settings", lambda: Settings(env="test"))
    monkeypatch.setattr(import_command, "run_import", fail)
    with pytest.raises(SystemExit) as error:
        import_command.main()
    assert error.value.code == exit_code
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == expected


def test_import_success_preserves_argument_defaults_and_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI emits exactly one sorted summary and uses unchanged batch defaults."""

    async def succeed(args: argparse.Namespace, _settings: Settings) -> dict[str, object]:
        assert args.command == "persist"
        assert (args.batch_size, args.geocode_batch_size, args.max_provider_requests) == (
            200,
            25,
            500,
        )
        return {"stage": "persistence", "status": "ok", "run_id": "synthetic"}

    monkeypatch.setattr(sys, "argv", ["wef-import", "persist"])
    monkeypatch.setattr(import_command, "load_settings", lambda: Settings(env="test"))
    monkeypatch.setattr(import_command, "run_import", succeed)
    import_command.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert (
        captured.out
        == json.dumps(
            {"stage": "persistence", "status": "ok", "run_id": "synthetic"}, sort_keys=True
        )
        + "\n"
    )


@pytest.mark.parametrize(
    ("command", "paused", "expected_stages"),
    [
        ("dry-run", False, ["dry-run"]),
        ("persist", False, ["persist", "release"]),
        ("geocode", False, ["geocode", "release"]),
        ("geocode", True, ["geocode"]),
        ("media", False, ["media", "release"]),
        ("verify", False, ["verify"]),
        ("run", False, ["persist", "geocode", "media", "verify"]),
        ("run", True, ["persist", "geocode"]),
    ],
)
async def test_stage_context_preserves_sequence_pause_and_disposal(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    *,
    paused: bool,
    expected_stages: list[str],
) -> None:
    """Shared composition retains explicit stages, paused short-circuit and engine cleanup."""
    settings = Settings(env="test")
    prepared = object()
    database = SimpleNamespace(
        session_factory=object(), engine=SimpleNamespace(dispose=AsyncMock())
    )
    repository = MagicMock()
    persistence = object()
    lease = SimpleNamespace(
        run_id="synthetic",
        status=CompleteImportStatus.PAUSED if paused else CompleteImportStatus.RUNNING,
    )
    stages: list[str] = []

    async def stage(context: import_command.ImportStageContext, **_kwargs: object) -> object:
        assert context.prepared is prepared
        assert context.repository is repository
        assert context.persistence is persistence
        assert id(context.database) == id(database)
        assert context.settings is settings
        return lease

    async def geocode(context: import_command.ImportStageContext, **kwargs: object) -> object:
        stages.append("geocode")
        return await stage(context, **kwargs)

    async def media(context: import_command.ImportStageContext, **kwargs: object) -> object:
        stages.append("media")
        return await stage(context, **kwargs)

    async def persist(*_args: object, **_kwargs: object) -> object:
        stages.append("persist")
        return lease

    async def verify(*_args: object, **_kwargs: object) -> tuple[object, dict[str, int]]:
        stages.append("verify")
        return lease, {"offers": 0}

    async def release(*_args: object, **_kwargs: object) -> object:
        stages.append("release")
        return lease

    async def dry_run(*_args: object) -> dict[str, object]:
        stages.append("dry-run")
        return {"status": "ok"}

    repository.release_run = release
    monkeypatch.setattr(import_command, "_prepare", lambda _settings: prepared)
    monkeypatch.setattr(import_command, "create_database_resources", lambda _url: database)
    monkeypatch.setattr(
        import_command, "SQLAlchemyCompleteImportRepository", lambda _factory: repository
    )
    monkeypatch.setattr(
        import_command, "SQLAlchemyIngestionPersistence", lambda *_args, **_kwargs: persistence
    )
    monkeypatch.setattr(import_command, "build_offer_origin_sync", lambda _factory: None)
    monkeypatch.setattr(import_command, "_dry_run", dry_run)
    monkeypatch.setattr(import_command, "_persist", persist)
    monkeypatch.setattr(import_command, "_geocode", geocode)
    monkeypatch.setattr(import_command, "_media", media)
    monkeypatch.setattr(import_command, "_verify", verify)
    result = await import_command.run_import(
        argparse.Namespace(
            command=command, batch_size=200, geocode_batch_size=25, max_provider_requests=500
        ),
        settings,
    )
    assert stages == expected_stages
    assert result["status"] == (
        "paused" if paused else "running" if command in {"run", "verify"} else "ok"
    )
    database.engine.dispose.assert_awaited_once()
