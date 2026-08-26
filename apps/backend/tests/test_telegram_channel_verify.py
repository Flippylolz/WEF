"""Tests for Telegram channel identity and redacted verification."""

from __future__ import annotations

import pytest

from wef_backend.features.ingestion.application.telegram_channel_verify import (
    verify_telegram_channel_access,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)

_HTTP_OK = 200


def test_default_identity_matches_d003_public_channel() -> None:
    identity = default_live_channel_identity()
    assert identity.username == "elestate_warszawa"
    assert identity.channel_id == "2180077318"
    assert identity.public_message_url(3) == "https://t.me/elestate_warszawa/3"


@pytest.mark.asyncio
async def test_verify_reports_credentials_missing_when_public_ok() -> None:
    identity = default_live_channel_identity()

    async def fake_get(_url: str) -> int:
        return _HTTP_OK

    result = await verify_telegram_channel_access(
        identity,
        credentials_ready=False,
        session_ready=False,
        get=fake_get,
    )
    assert result.public_message_reachable is True
    assert result.credentials_ready is False
    assert result.status == "public_ok_credentials_missing"


@pytest.mark.asyncio
async def test_verify_reports_session_pending_when_api_present() -> None:
    identity = default_live_channel_identity()

    async def fake_get(_url: str) -> int:
        return _HTTP_OK

    result = await verify_telegram_channel_access(
        identity,
        credentials_ready=True,
        session_ready=False,
        get=fake_get,
    )
    assert result.credentials_ready is True
    assert result.session_ready is False
    assert result.status == "public_ok_session_pending"


@pytest.mark.asyncio
async def test_verify_ready_when_session_present() -> None:
    identity = default_live_channel_identity()

    async def fake_get(_url: str) -> int:
        return _HTTP_OK

    result = await verify_telegram_channel_access(
        identity,
        credentials_ready=True,
        session_ready=True,
        get=fake_get,
    )
    assert result.status == "public_ok_credentials_present"
