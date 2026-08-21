"""Telethon-backed live Telegram client (secrets never logged)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from wef_backend.features.ingestion.domain.telegram_secrets import TelegramWorkerSecrets


class TelethonLiveClient:
    """Async Telethon adapter with flood-wait sleep and redacted failures."""

    def __init__(
        self,
        secrets: TelegramWorkerSecrets,
        *,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """Build a client from worker secrets without echoing session material."""
        # flood_sleep_threshold=0: we own flood waits explicitly.
        self._client = TelegramClient(
            StringSession(secrets.session),
            secrets.api_id,
            secrets.api_hash,
            flood_sleep_threshold=0,
        )
        self._sleep = sleep

    async def connect(self) -> None:
        """Connect and require an already-authorized string session."""
        await self._client.connect()
        if not await self._client.is_user_authorized():
            message = "Telegram session is not authorized"
            raise RuntimeError(message)

    async def disconnect(self) -> None:
        """Disconnect the Telethon client."""
        await self._client.disconnect()

    async def resolve_channel(self, username: str) -> TelegramChannelEntity:
        """Resolve a public channel username to numeric id and title."""
        try:
            entity = await self._client.get_entity(username)
        except FloodWaitError as error:
            await self._wait_flood(error.seconds)
            entity = await self._client.get_entity(username)
        channel_id = str(getattr(entity, "id", "") or "")
        title = str(getattr(entity, "title", "") or "")
        resolved_username = str(getattr(entity, "username", "") or username)
        if not channel_id or not title:
            message = "Telegram entity is missing id or title"
            raise RuntimeError(message)
        return TelegramChannelEntity(
            username=resolved_username,
            channel_id=channel_id,
            title=title,
        )

    async def iter_messages(
        self,
        *,
        username: str,
        min_id: int,
        reverse: bool = True,
        limit: int | None = None,
    ) -> AsyncIterator[LiveTelegramMessage]:
        """Iterate channel messages oldest-first when reverse is true."""
        try:
            async for message in self._client.iter_messages(
                username,
                min_id=min_id,
                reverse=reverse,
                limit=limit,
            ):
                yield _to_live_message(message)
        except FloodWaitError as error:
            await self._wait_flood(error.seconds)
            async for message in self._client.iter_messages(
                username,
                min_id=min_id,
                reverse=reverse,
                limit=limit,
            ):
                yield _to_live_message(message)

    async def _wait_flood(self, seconds: int) -> None:
        sleeper = self._sleep or asyncio.sleep
        await sleeper(max(int(seconds), 0))


def _to_live_message(message: object) -> LiveTelegramMessage:
    payload = cast("Any", message)
    message_id = int(payload.id)
    text = str(getattr(payload, "message", None) or getattr(payload, "text", None) or "")
    date = getattr(payload, "date", None)
    if not isinstance(date, datetime):
        message_text = "Telegram message is missing a published timestamp"
        raise TypeError(message_text)
    published = date if date.tzinfo is not None else date.replace(tzinfo=UTC)
    edited = getattr(payload, "edit_date", None)
    edited_at = None
    if isinstance(edited, datetime):
        edited_at = edited if edited.tzinfo is not None else edited.replace(tzinfo=UTC)
    grouped = getattr(payload, "grouped_id", None)
    media_group_id = None if grouped is None else str(grouped)
    return LiveTelegramMessage(
        external_message_id=message_id,
        text=text,
        published_at=published.astimezone(UTC),
        edited_at=None if edited_at is None else edited_at.astimezone(UTC),
        media_group_id=media_group_id,
    )
