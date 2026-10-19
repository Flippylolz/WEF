"""Private recovery operators retain ownership, safe receipts and failure cleanup."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from wef_backend import media_recovery_command, offer_backfill_command, raw_replay_command
from wef_backend.features.ingestion.application.persistence import (
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
)
from wef_backend.features.ingestion.application.raw_replay import ReplaySummary
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from types import ModuleType


def _settings() -> Settings:
    return Settings(
        env="test",
        database_url="postgresql+asyncpg://synthetic:synthetic@unused.invalid/wef",
        release_sha="a" * 40,
        contact_encryption_key=None,
        contact_hmac_key=None,
    )


def _database(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> MagicMock:
    database = MagicMock()
    database.engine.dispose = AsyncMock()
    monkeypatch.setattr(module, "load_settings", _settings)
    monkeypatch.setattr(module, "create_database_resources", MagicMock(return_value=database))
    return database


@pytest.mark.parametrize("seed", [False, True])
async def test_raw_replay_composes_current_identity_and_optional_seed(
    monkeypatch: pytest.MonkeyPatch,
    *,
    seed: bool,
) -> None:
    database = _database(monkeypatch, raw_replay_command)
    archive = AsyncMock()
    archive.seed_from_history.return_value = (2, 1)
    store, cipher, origin_sync = object(), object(), object()
    monkeypatch.setattr(
        raw_replay_command, "SQLAlchemyRawEventArchive", MagicMock(return_value=archive)
    )
    persistence = MagicMock(return_value=store)
    monkeypatch.setattr(raw_replay_command, "SQLAlchemyIngestionPersistence", persistence)
    monkeypatch.setattr(raw_replay_command, "build_contact_cipher", MagicMock(return_value=cipher))
    monkeypatch.setattr(
        raw_replay_command, "build_offer_origin_sync", MagicMock(return_value=origin_sync)
    )
    summary = ReplaySummary(3, 1, 1, 1, 0, 0, 0)
    replay = AsyncMock(return_value=summary)
    factory = MagicMock(return_value=replay)
    monkeypatch.setattr(raw_replay_command, "RawParserReplayer", factory)

    result = await raw_replay_command.run(seed_archive=seed)

    assert result == ({"seeded": 2, "seed_skipped": 1} if seed else {}) | asdict(summary)
    assert archive.seed_from_history.await_count == int(seed)
    persistence.assert_called_once_with(
        database.session_factory, contact_cipher=cipher, field_origin_sync=origin_sync
    )
    assert factory.call_args.kwargs["source"] is archive
    assert factory.call_args.kwargs["store"] is store
    assert factory.call_args.kwargs["identity"] == default_live_channel_identity()
    replay.assert_awaited_once_with(release_sha="a" * 40)
    database.engine.dispose.assert_awaited_once()


async def test_raw_replay_disposes_resources_after_replayer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _database(monkeypatch, raw_replay_command)
    monkeypatch.setattr(
        raw_replay_command, "SQLAlchemyRawEventArchive", MagicMock(return_value=AsyncMock())
    )
    monkeypatch.setattr(raw_replay_command, "SQLAlchemyIngestionPersistence", MagicMock())
    monkeypatch.setattr(raw_replay_command, "build_contact_cipher", MagicMock())
    monkeypatch.setattr(raw_replay_command, "build_offer_origin_sync", MagicMock())
    failure = RuntimeError("synthetic private source")
    monkeypatch.setattr(
        raw_replay_command,
        "RawParserReplayer",
        MagicMock(return_value=AsyncMock(side_effect=failure)),
    )
    with pytest.raises(RuntimeError, match="synthetic private source") as caught:
        await raw_replay_command.run()
    assert caught.value is failure
    database.engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("seed", [False, True])
def test_replay_cli_preserves_seed_opt_in_and_sorted_receipt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    seed: bool,
) -> None:
    run = AsyncMock(return_value={"reprocessed": 2, "created": 1})
    monkeypatch.setattr(raw_replay_command, "run", run)
    monkeypatch.setattr(sys, "argv", ["wef-replay-parser", *(["--seed-archive"] if seed else [])])
    raw_replay_command.main()
    run.assert_awaited_once_with(seed_archive=seed)
    captured = capsys.readouterr()
    assert captured.out == '{"created": 1, "reprocessed": 2}\n'
    assert captured.err == ""


def test_replay_cli_failure_is_redacted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        raw_replay_command, "run", AsyncMock(side_effect=RuntimeError("synthetic secret source"))
    )
    monkeypatch.setattr(sys, "argv", ["wef-replay-parser"])
    with pytest.raises(SystemExit) as exited:
        raw_replay_command.main()
    assert exited.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Raw archive parser replay failed: RuntimeError\n"


@pytest.mark.parametrize("action", ["status", "pause", "resume"])
async def test_media_recovery_status_is_read_only_and_control_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    action: str,
) -> None:
    engine, store = MagicMock(), AsyncMock()
    engine.dispose = AsyncMock()
    store.status.return_value = {"state": "paused", "pending": 3}
    monkeypatch.setattr(media_recovery_command, "load_settings", _settings)
    monkeypatch.setattr(
        media_recovery_command, "create_async_engine", MagicMock(return_value=engine)
    )
    session_factory = MagicMock()
    sessions = MagicMock(return_value=session_factory)
    monkeypatch.setattr(media_recovery_command, "async_sessionmaker", sessions)
    factory = MagicMock(return_value=store)
    monkeypatch.setattr(media_recovery_command, "SQLAlchemyMediaRecoveryStore", factory)

    assert await media_recovery_command.run(action) == {"state": "paused", "pending": 3}
    sessions.assert_called_once_with(engine, expire_on_commit=False)
    factory.assert_called_once_with(session_factory, default_live_channel_identity().channel_id)
    if action == "status":
        store.control.assert_not_awaited()
    else:
        store.control.assert_awaited_once_with(action)
    store.status.assert_awaited_once()
    engine.dispose.assert_awaited_once()


async def test_media_recovery_disposes_engine_after_control_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, store = MagicMock(), AsyncMock()
    engine.dispose = AsyncMock()
    failure = OSError("synthetic control failure")
    store.control.side_effect = failure
    monkeypatch.setattr(media_recovery_command, "load_settings", _settings)
    monkeypatch.setattr(
        media_recovery_command, "create_async_engine", MagicMock(return_value=engine)
    )
    monkeypatch.setattr(media_recovery_command, "async_sessionmaker", MagicMock())
    monkeypatch.setattr(
        media_recovery_command, "SQLAlchemyMediaRecoveryStore", MagicMock(return_value=store)
    )
    with pytest.raises(OSError, match="synthetic control failure") as caught:
        await media_recovery_command.run("resume")
    assert caught.value is failure
    store.status.assert_not_awaited()
    engine.dispose.assert_awaited_once()


@pytest.mark.parametrize(
    ("arguments", "action"), [([], "status"), (["pause"], "pause"), (["resume"], "resume")]
)
def test_media_recovery_cli_defaults_to_status_and_prints_aggregates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    action: str,
) -> None:
    run = AsyncMock(return_value={"pending": 2})
    monkeypatch.setattr(media_recovery_command, "run", run)
    monkeypatch.setattr(sys, "argv", ["wef-media-recovery", *arguments])
    media_recovery_command.main()
    run.assert_awaited_once_with(action)
    output = capsys.readouterr()
    assert output.out == '{"pending": 2}\n'
    assert output.err == ""


def _backfill_context(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock, AsyncMock]:
    database = _database(monkeypatch, offer_backfill_command)
    session = MagicMock()
    session.scalar = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    session.execute = AsyncMock(return_value=MagicMock())
    session.execute.return_value.all.return_value = [
        SimpleNamespace(external_message_id=4, current_revision_id=uuid4()),
        SimpleNamespace(external_message_id=6, current_revision_id=uuid4()),
    ]
    manager = database.session_factory.return_value
    manager.__aenter__ = AsyncMock(return_value=session)
    manager.__aexit__ = AsyncMock(return_value=False)
    store = AsyncMock()
    store.start_run.return_value = uuid4()
    monkeypatch.setattr(
        offer_backfill_command, "SQLAlchemyIngestionPersistence", MagicMock(return_value=store)
    )
    monkeypatch.setattr(
        offer_backfill_command, "build_contact_cipher", MagicMock(return_value=object())
    )
    monkeypatch.setattr(
        offer_backfill_command, "build_offer_origin_sync", MagicMock(return_value=object())
    )
    return database, session, store


async def test_backfill_refuses_unknown_channel_without_starting_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, session, store = _backfill_context(monkeypatch)
    session.scalar.return_value = None
    with pytest.raises(ValueError, match="unknown source channel"):
        await offer_backfill_command.run(
            channel="synthetic", after_id=3, through_id=9, limit=2, apply=True
        )
    store.start_run.assert_not_awaited()
    session.execute.assert_not_awaited()
    database.engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("apply", [False, True])
async def test_backfill_failure_records_only_acknowledged_progress_and_safe_cursor(
    monkeypatch: pytest.MonkeyPatch,
    *,
    apply: bool,
) -> None:
    database, session, store = _backfill_context(monkeypatch)
    failure = ValueError("synthetic private source contact")
    store.replay_current_revision.side_effect = ["create_candidate", failure]
    with pytest.raises(ValueError, match="synthetic private source contact"):
        await offer_backfill_command.run(
            channel="synthetic", after_id=3, through_id=9, limit=2, apply=apply
        )
    if apply:
        store.finish_run.assert_awaited_once()
        finished = store.finish_run.await_args.kwargs
        assert finished["status"] is RunStatus.FAILED
        assert finished["counts"] == RunCounts(seen=1, unchanged=1, offers=1)
        assert finished["checkpoint"] == RunCheckpoint()
        assert finished["error_summary"] == "bounded_backfill_failed_after_id=4"
        assert store.start_run.await_args.kwargs["mode"] is RunMode.REPROCESS
    else:
        store.start_run.assert_not_awaited()
        store.finish_run.assert_not_awaited()
        assert all(
            call.kwargs["run_id"] is None for call in store.replay_current_revision.await_args_list
        )
    statement = session.execute.await_args.args[0]
    sql = str(statement)
    assert "source_messages.external_message_id >" in sql
    assert "source_messages.external_message_id <=" in sql
    assert "ORDER BY" in sql
    assert "LIMIT" in sql
    assert {3, 9, 2} <= set(statement.compile().params.values())
    database.engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("apply", [False, True])
async def test_backfill_success_returns_exact_bounded_counts(
    monkeypatch: pytest.MonkeyPatch, *, apply: bool
) -> None:
    database, _session, store = _backfill_context(monkeypatch)
    store.replay_current_revision.side_effect = ["create_candidate", "current"]
    result = await offer_backfill_command.run(
        channel="synthetic", after_id=3, through_id=9, limit=2, apply=apply
    )
    assert result["counts"] == {"create_candidate": 1, "current": 1}
    assert result["next_after_id"] == 6
    assert result["scanned"] == 2
    assert result["exhausted"] is False
    assert bool(result["run_id"]) is apply
    if apply:
        assert store.finish_run.await_args.kwargs["status"] is RunStatus.SUCCEEDED
        assert store.finish_run.await_args.kwargs["counts"] == RunCounts(
            seen=2, unchanged=2, offers=1
        )
        assert store.finish_run.await_args.kwargs["error_summary"] is None
    else:
        store.finish_run.assert_not_awaited()
    database.engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("failed", [False, True])
def test_backfill_cli_keeps_dry_run_default_and_redacts_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    failed: bool,
) -> None:
    run = AsyncMock(return_value={"scanned": 2, "apply": False})
    if failed:
        run.side_effect = ValueError("synthetic private source")
    monkeypatch.setattr(offer_backfill_command, "run", run)
    monkeypatch.setattr(
        sys, "argv", ["wef-backfill", "--channel", "synthetic", "--through-id", "9"]
    )
    if failed:
        with pytest.raises(SystemExit) as exited:
            offer_backfill_command.main()
        assert exited.value.code == 2
    else:
        offer_backfill_command.main()
    run.assert_awaited_once_with(
        channel="synthetic", after_id=0, through_id=9, limit=100, apply=False
    )
    output = capsys.readouterr()
    assert output.out == ("" if failed else '{"apply": false, "scanned": 2}\n')
    assert output.err == ("Offer backfill failed: ValueError\n" if failed else "")


@pytest.mark.parametrize(
    ("module", "option"),
    [(media_recovery_command, "pause"), (offer_backfill_command, "--through-id")],
)
def test_recovery_python_module_help_precedes_any_work(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    module: ModuleType,
    option: str,
) -> None:
    monkeypatch.setattr(sys, "argv", ["synthetic-operator", "--help"])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(str(module.__file__), run_name="__main__")
    assert exited.value.code == 0
    output = capsys.readouterr()
    assert option in output.out
    assert output.err == ""
