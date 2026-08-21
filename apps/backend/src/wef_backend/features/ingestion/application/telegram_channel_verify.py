"""Credential-free public channel checks and redacted secret-path inspection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from wef_backend.features.ingestion.domain.telegram_channel import (
    SecretFileStatus,
    TelegramChannelIdentity,
    TelegramWorkerSecretPaths,
    inspect_secret_file,
)

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
    secret_files: tuple[SecretFileStatus, ...]
    secrets_ready: bool
    live_client_verification: str
    status: str


async def verify_public_message_reachable(
    url: str,
    *,
    get: PublicUrlGetter,
) -> bool:
    """Return True when the public message URL answers successfully."""
    return await get(url) < _HTTP_CLIENT_ERROR


def summarize_secret_paths(paths: TelegramWorkerSecretPaths) -> tuple[SecretFileStatus, ...]:
    """Inspect each configured secret path without reading file contents."""
    return tuple(inspect_secret_file(path) for path in paths.required_files())


async def verify_telegram_channel_access(
    identity: TelegramChannelIdentity,
    secret_paths: TelegramWorkerSecretPaths,
    *,
    get: PublicUrlGetter,
    probe_message_id: int = 3,
) -> TelegramChannelVerification:
    """Verify public identity and secret-path contract without loading Telethon."""
    message_url = identity.public_message_url(probe_message_id)
    reachable = await verify_public_message_reachable(message_url, get=get)
    secrets = summarize_secret_paths(secret_paths)
    secrets_ready = all(item.present and item.owner_readable_only is True for item in secrets)
    if not reachable:
        status = "public_unreachable"
    elif not secrets_ready:
        status = "public_ok_secrets_missing"
    else:
        # Live numeric ID/title resolve requires Telethon (E8-T2) plus real secrets.
        status = "public_ok_secrets_present_awaiting_client"
    return TelegramChannelVerification(
        channel_username=identity.username,
        expected_channel_id=identity.channel_id,
        expected_channel_title=identity.channel_title,
        public_channel_url=identity.public_channel_url(),
        public_message_url=message_url,
        public_message_reachable=reachable,
        secret_files=secrets,
        secrets_ready=secrets_ready,
        live_client_verification="deferred_to_E8-T2",
        status=status,
    )
