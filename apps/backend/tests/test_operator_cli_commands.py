"""CLI smoke tests for Telegram and recurring-geocoder operator commands."""

from __future__ import annotations

import json

import pytest

from wef_backend import (
    batch_ingestion_ai_parse_command,
    recurring_geocoder_command,
    telegram_backfill_command,
    telegram_channel_command,
)
from wef_backend.batch_ingestion_ai_parse_command import BatchIngestionAiParseSummary
from wef_backend.features.ingestion.application.telegram_channel_verify import (
    TelegramChannelVerification,
)
from wef_backend.features.ingestion.application.telegram_live import LiveBackfillResult
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramWorkerSecrets
from wef_backend.settings import Settings


def test_telegram_channel_command_prints_redacted_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_verify(*_args: object, **_kwargs: object) -> TelegramChannelVerification:
        return TelegramChannelVerification(
            channel_username="elestate_warszawa",
            expected_channel_id="2180077318",
            expected_channel_title="El Estate | Покупка Варшава",
            public_channel_url="https://t.me/elestate_warszawa",
            public_message_url="https://t.me/elestate_warszawa/1",
            public_message_reachable=True,
            credentials_ready=False,
            session_ready=False,
            live_client_verification="awaiting_api_credentials",
            status="public_ok_credentials_missing",
        )

    monkeypatch.setattr(
        telegram_channel_command,
        "verify_telegram_channel_access",
        _fake_verify,
    )
    telegram_channel_command.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["channel_username"] == "elestate_warszawa"
    assert payload["operating_owner"] == "dedicated_telegram_user_not_bot"


def test_telegram_channel_command_exits_when_public_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_verify(*_args: object, **_kwargs: object) -> TelegramChannelVerification:
        return TelegramChannelVerification(
            channel_username="elestate_warszawa",
            expected_channel_id="2180077318",
            expected_channel_title="title",
            public_channel_url="https://t.me/elestate_warszawa",
            public_message_url="https://t.me/elestate_warszawa/1",
            public_message_reachable=False,
            credentials_ready=False,
            session_ready=False,
            live_client_verification="awaiting_api_credentials",
            status="public_unreachable",
        )

    monkeypatch.setattr(
        telegram_channel_command,
        "verify_telegram_channel_access",
        _fake_verify,
    )
    with pytest.raises(SystemExit) as exited:
        telegram_channel_command.main()
    assert exited.value.code == 2


def test_recurring_geocoder_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_run(*, live_check: bool) -> dict[str, object]:
        assert live_check is False
        return {"retained_provider": "geoapify", "status": "retain"}

    monkeypatch.setattr(recurring_geocoder_command, "_run", _fake_run)
    recurring_geocoder_command.main([])
    payload = json.loads(capsys.readouterr().out)
    assert payload["retained_provider"] == "geoapify"
    assert "generated_at" in payload


def test_telegram_backfill_command_success_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_run_backfill(
        *,
        resume_after: int,
        overlap: int,
        limit: int | None,
    ) -> LiveBackfillResult:
        assert resume_after == 10
        assert overlap == 2
        assert limit == 5
        return LiveBackfillResult(
            verified_channel_id="2180077318",
            messages_seen=1,
            checkpoint_external_message_id=11,
            created=1,
            unchanged=0,
            revised=0,
            skipped_non_candidate=0,
        )

    monkeypatch.setattr(telegram_backfill_command, "run_backfill", _fake_run_backfill)
    telegram_backfill_command.main(["--resume-after", "10", "--overlap", "2", "--limit", "5"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verified_channel_id"] == "2180077318"
    assert payload["checkpoint_external_message_id"] == 11


def test_telegram_backfill_command_generic_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(**_kwargs: object) -> LiveBackfillResult:
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(telegram_backfill_command, "run_backfill", _boom)
    with pytest.raises(SystemExit) as exited:
        telegram_backfill_command.main([])
    assert exited.value.code == 2


def test_telegram_backfill_command_fails_closed_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        telegram_backfill_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=None,
            telegram_api_hash=None,
        ),
    )
    with pytest.raises(SystemExit) as exited:
        telegram_backfill_command.main([])
    assert exited.value.code == 2


@pytest.mark.asyncio
async def test_telegram_backfill_run_loads_secrets_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        telegram_backfill_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=1,
            telegram_api_hash=None,
            database_url="postgresql+asyncpg://example/unused",
        ),
    )

    class _Engine:
        async def dispose(self) -> None:
            return None

    class _Client:
        pass

    calls: list[str] = []

    def _engine(_url: str) -> _Engine:
        calls.append("engine")
        return _Engine()

    def _session_factory(*_args: object, **_kwargs: object) -> object:
        calls.append("session")
        return object()

    class _Store:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            calls.append("store")

    class _Backfill:
        def __init__(self, **_kwargs: object) -> None:
            calls.append("backfill")

        async def __call__(self, request: object) -> LiveBackfillResult:
            _ = request
            return LiveBackfillResult(
                verified_channel_id="2180077318",
                messages_seen=0,
                checkpoint_external_message_id=0,
                created=0,
                unchanged=0,
                revised=0,
                skipped_non_candidate=0,
            )

    def _client(_secrets: TelegramWorkerSecrets, **_kwargs: object) -> _Client:
        _ = _secrets
        return _Client()

    class _MediaPipeline:
        pass

    def _media_pipeline(*_args: object, **_kwargs: object) -> _MediaPipeline:
        calls.append("media_pipeline")
        return _MediaPipeline()

    monkeypatch.setattr(telegram_backfill_command, "create_async_engine", _engine)
    monkeypatch.setattr(telegram_backfill_command, "async_sessionmaker", _session_factory)
    monkeypatch.setattr(telegram_backfill_command, "SQLAlchemyIngestionPersistence", _Store)
    monkeypatch.setattr(telegram_backfill_command, "TelethonLiveClient", _client)
    monkeypatch.setattr(telegram_backfill_command, "build_live_media_pipeline", _media_pipeline)
    monkeypatch.setattr(telegram_backfill_command, "LiveTelegramBackfill", _Backfill)
    monkeypatch.setattr(
        telegram_backfill_command,
        "secrets_from_settings",
        lambda _settings: TelegramWorkerSecrets(api_id=1, api_hash="hash", session="sess"),
    )

    result = await telegram_backfill_command.run_backfill(
        resume_after=0,
        overlap=0,
        limit=1,
    )
    assert result.verified_channel_id == "2180077318"
    assert "engine" in calls
    assert "backfill" in calls


def test_batch_ingestion_ai_parse_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_run_batch(
        _options: batch_ingestion_ai_parse_command.BatchIngestionAiParseOptions,
    ) -> BatchIngestionAiParseSummary:
        return BatchIngestionAiParseSummary(
            linked_existing_offers=2,
            candidates_considered=3,
            generated=2,
            applied=1,
            skipped={"offer_exists": 1},
        )

    monkeypatch.setattr(batch_ingestion_ai_parse_command, "run_batch", _fake_run_batch)
    batch_ingestion_ai_parse_command.main([])
    payload = json.loads(capsys.readouterr().out)
    assert payload["linked_existing_offers"] == 2
    assert payload["applied"] == 1
    assert payload["skipped"] == {"offer_exists": 1}
