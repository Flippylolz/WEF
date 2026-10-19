"""Operator CLI refusal, argument forwarding and bounded batch completion paths."""

from __future__ import annotations

import importlib
import json
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_ingestion_ai_parse import _context, _payload, _pending_run
from tests.test_ingestion_persistence_boundaries import _factory
from wef_backend import (
    archive_recovery_command,
    batch_ingestion_ai_parse_command,
    location_validation_command,
    recurring_geocoder_command,
)
from wef_backend.batch_ingestion_ai_parse_command import (
    BatchCandidate,
    BatchIngestionAiParseOptions,
    resolve_owner_id,
    run_batch,
)
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyOutcome,
    IngestionAiApplyStatus,
    IngestionAiParseOutcome,
    IngestionAiParseStatus,
    parse_ingestion_ai_parse_payload,
)
from wef_backend.geocoder_check import GeoapifyCheckError
from wef_backend.settings import Settings


@pytest.mark.parametrize(
    ("module_name", "operation"),
    [
        ("accept_pending_geocode_pins_command", "run"),
        ("archive_recovery_command", "run"),
        ("batch_ingestion_ai_parse_command", "run_batch"),
        ("recurring_geocoder_command", "_run"),
    ],
)
def test_operator_failures_exit_with_redacted_diagnostics(
    module_name: str,
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected SQL/provider bodies never enter operator stdout or stderr."""
    module = importlib.import_module("wef_backend." + module_name)
    monkeypatch.setattr(
        module, operation, AsyncMock(side_effect=RuntimeError("private source and credential body"))
    )
    monkeypatch.setattr(sys, "argv", [module_name])
    with pytest.raises(SystemExit) as caught:
        module.main()
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "failed" in captured.err.casefold()
    assert "private" not in captured.err
    assert "credential" not in captured.err


def test_recurring_geocoder_check_failure_preserves_its_bounded_explanation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        recurring_geocoder_command,
        "_run",
        AsyncMock(side_effect=GeoapifyCheckError("safe provider check refusal")),
    )
    with pytest.raises(SystemExit) as caught:
        recurring_geocoder_command.main([])
    assert caught.value.code == 2
    assert capsys.readouterr().err == "safe provider check refusal\n"


def test_archive_cli_defaults_to_readonly_preflight(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = AsyncMock(return_value={"selected": 0, "phase": "preflight"})
    monkeypatch.setattr(archive_recovery_command, "run", run)
    monkeypatch.setattr(sys, "argv", ["archive-recovery"])
    archive_recovery_command.main()
    run.assert_awaited_once_with("preflight")
    assert json.loads(capsys.readouterr().out) == {"selected": 0, "phase": "preflight"}


def test_location_validation_cli_forwards_explicit_canaries_and_readiness(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    first, second = uuid4(), uuid4()
    run = AsyncMock(return_value={"mode": "apply"})
    monkeypatch.setattr(location_validation_command, "run", run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "location-validation",
            "apply",
            "--canary-id",
            str(first),
            "--canary-id",
            str(second),
            "--discovery-ready",
        ],
    )
    location_validation_command.main()
    run.assert_awaited_once_with("apply", canary_ids=(first, second), discovery_ready=True)
    assert json.loads(capsys.readouterr().out) == {"mode": "apply"}


@pytest.mark.parametrize(
    "module_name",
    [
        "archive_recovery_command",
        "batch_ingestion_ai_parse_command",
        "ingestion_progress_command",
        "location_validation_command",
    ],
)
def test_operator_module_entrypoints_expose_help_without_running_services(
    module_name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = importlib.import_module("wef_backend." + module_name)
    assert module.__file__ is not None
    monkeypatch.setattr(sys, "argv", [module_name, "--help"])
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(module.__file__, run_name="__main__")
    assert caught.value.code == 0
    assert "usage:" in capsys.readouterr().out


@pytest.mark.parametrize("live", [False, True])
async def test_recurring_cli_live_probe_is_explicit_and_keeps_policy_report(
    *, live: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = AsyncMock(return_value={"status": "synthetic proof"})
    settings = Settings()
    monkeypatch.setattr(recurring_geocoder_command, "check_geoapify", probe)
    monkeypatch.setattr(recurring_geocoder_command, "load_settings", lambda: settings)
    result = await recurring_geocoder_command._run(live_check=live)  # noqa: SLF001 - CLI composition boundary
    assert result["status"] == "revalidated_retain_geoapify"
    assert result["live_check"] == ({"status": "synthetic proof"} if live else None)
    assert probe.await_count == int(live)


async def test_batch_owner_lookup_refuses_no_matching_owner() -> None:
    result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    session = MagicMock(execute=AsyncMock(return_value=result))
    with pytest.raises(RuntimeError, match="owner account was not found"):
        await resolve_owner_id(_factory(session), Settings(), owner_id=None)


@pytest.mark.parametrize("mode", ["no_candidates", "no_outcomes", "apply_stale"])
async def test_batch_operator_handles_empty_work_and_nonapplied_results(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, owner = _context(), uuid4()
    _verdict, fields, _warnings = parse_ingestion_ai_parse_payload(_payload())
    run = _pending_run(context=context, owner_id=owner, run_id=uuid4(), fields=fields)
    engine = MagicMock(dispose=AsyncMock())
    admin = SimpleNamespace(
        generate_ingestion_ai_parse=SimpleNamespace(
            generate_batch=AsyncMock(
                return_value=()
                if mode == "no_outcomes"
                else (IngestionAiParseOutcome(IngestionAiParseStatus.GENERATED, "ok", run),)
            )
        ),
        apply_ingestion_ai_parse=AsyncMock(
            return_value=IngestionAiApplyOutcome(IngestionAiApplyStatus.STALE, run, None)
        ),
    )
    build = MagicMock(return_value=SimpleNamespace(admin=admin))
    monkeypatch.setattr(
        batch_ingestion_ai_parse_command, "resolve_owner_id", AsyncMock(return_value=owner)
    )
    monkeypatch.setattr(
        batch_ingestion_ai_parse_command,
        "load_candidates",
        AsyncMock(
            return_value=()
            if mode == "no_candidates"
            else (BatchCandidate(7, context.revision_id),)
        ),
    )
    monkeypatch.setattr(
        batch_ingestion_ai_parse_command,
        "create_database_resources",
        lambda _url: SimpleNamespace(engine=engine, session_factory=MagicMock()),
    )
    monkeypatch.setattr(batch_ingestion_ai_parse_command, "build_services", build)
    result = await run_batch(
        BatchIngestionAiParseOptions(
            owner_id=owner,
            limit=1,
            generate_only=False,
            link_existing=False,
            min_text_length=1,
            settings=Settings(),
        )
    )
    assert result.applied == 0
    if mode == "no_candidates":
        build.assert_not_called()
        assert result.candidates_considered == 0
    elif mode == "no_outcomes":
        assert result.groq_batch_jobs == 0
        admin.apply_ingestion_ai_parse.assert_not_awaited()
    else:
        assert result.skipped == {"stale": 1}
        assert result.generated == 1
    engine.dispose.assert_awaited_once()
