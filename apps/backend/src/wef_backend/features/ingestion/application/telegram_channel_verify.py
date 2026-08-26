"""Public channel checks and redacted credential presence (never secret bytes)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity

_HTTP_CLIENT_ERROR = 400

PublicUrlGetter = Callable[[str], Awaitable[int]]


@dataclass(frozen=True, slots=True)
class TelegramChannelVerification:
    """Redacted verification result suitable for operator stdout."""

    channel_username: str
    expected_channel_id: str
    expected_channel_title: str
    public_channel_url: str
    public_message_url: str
    public_message_reachable: bool
    credentials_ready: bool
    session_ready: bool
    live_client_verification: str
    status: str


async def verify_public_message_reachable(
    url: str,
    *,
    get: PublicUrlGetter,
) -> bool:
    """Return True when the public message URL answers successfully."""
    return await get(url) < _HTTP_CLIENT_ERROR


async def verify_telegram_channel_access(
    identity: TelegramChannelIdentity,
    *,
    credentials_ready: bool,
    session_ready: bool,
    get: PublicUrlGetter,
    probe_message_id: int = 3,
) -> TelegramChannelVerification:
    """Verify public identity and whether env credentials are present."""
    message_url = identity.public_message_url(probe_message_id)
    reachable = await verify_public_message_reachable(message_url, get=get)
    if not reachable:
        status = "public_unreachable"
    elif not credentials_ready:
        status = "public_ok_credentials_missing"
    elif not session_ready:
        status = "public_ok_session_pending"
    else:
        status = "public_ok_credentials_present"
    live = "ready" if credentials_ready else "awaiting_api_credentials"
    return TelegramChannelVerification(
        channel_username=identity.username,
        expected_channel_id=identity.channel_id,
        expected_channel_title=identity.channel_title,
        public_channel_url=identity.public_channel_url(),
        public_message_url=message_url,
        public_message_reachable=reachable,
        credentials_ready=credentials_ready,
        session_ready=session_ready,
        live_client_verification=live,
        status=status,
    )
