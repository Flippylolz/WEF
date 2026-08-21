"""Tests for Telegram channel identity and redacted verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from wef_backend.features.ingestion.application.telegram_channel_verify import (
    verify_telegram_channel_access,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramWorkerSecretPaths,
    default_live_channel_identity,
    inspect_secret_file,
)

if TYPE_CHECKING:
    from pathlib import Path

_OWNER_READABLE_MODE = 0o600
_HTTP_OK = 200


def test_default_identity_matches_d003_public_channel() -> None:
    identity = default_live_channel_identity()
    assert identity.username == "elestate_warszawa"
    assert identity.channel_id == "2180077318"
    assert identity.public_message_url(3) == "https://t.me/elestate_warszawa/3"


def test_inspect_secret_file_reports_mode_600(tmp_path: Path) -> None:
    secret = tmp_path / "session"
    secret.write_text("redacted", encoding="utf-8")
    secret.chmod(_OWNER_READABLE_MODE)
    status = inspect_secret_file(secret)
    assert status.present is True
    assert status.owner_readable_only is True
    assert status.mode == "0o600"


@pytest.mark.asyncio
async def test_verify_reports_secrets_missing_when_public_ok(tmp_path: Path) -> None:
    identity = default_live_channel_identity()
    paths = TelegramWorkerSecretPaths(
        api_id_file=tmp_path / "api_id",
        api_hash_file=tmp_path / "api_hash",
        session_file=tmp_path / "session",
    )

    async def fake_get(_url: str) -> int:
        return _HTTP_OK

    result = await verify_telegram_channel_access(identity, paths, get=fake_get)
    assert result.public_message_reachable is True
    assert result.secrets_ready is False
    assert result.status == "public_ok_secrets_missing"
    assert result.live_client_verification == "deferred_to_E8-T2"


@pytest.mark.asyncio
async def test_verify_awaits_client_when_secrets_present(tmp_path: Path) -> None:
    identity = default_live_channel_identity()
    paths = TelegramWorkerSecretPaths(
        api_id_file=tmp_path / "api_id",
        api_hash_file=tmp_path / "api_hash",
        session_file=tmp_path / "session",
    )
    for path in paths.required_files():
        path.write_text("x", encoding="utf-8")
        path.chmod(_OWNER_READABLE_MODE)

    async def fake_get(_url: str) -> int:
        return _HTTP_OK

    result = await verify_telegram_channel_access(identity, paths, get=fake_get)
    assert result.secrets_ready is True
    assert result.status == "public_ok_secrets_present_awaiting_client"
