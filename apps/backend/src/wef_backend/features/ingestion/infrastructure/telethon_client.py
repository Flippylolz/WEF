"""Telethon-backed live Telegram client (secrets never logged)."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession

from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramLoginCodeError,
    TelegramSecretError,
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

    def save_session(self) -> str:
        """Return the current Telethon string session (never log it)."""
        return str(self._client.session.save())

    def is_connected(self) -> bool:
        """Return True when the Telethon transport is connected."""
        return bool(self._client.is_connected())

    async def connect(self) -> None:
        """Connect to Telegram. Authorization is handled by ensure_authorized."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect the Telethon client."""
        await self._client.disconnect()

    async def ensure_authorized(
        self,
        *,
        phone: str | None = None,
        login_code: str | None = None,
        password: str | None = None,
    ) -> str:
        """Authorize the user, generating a string session when needed."""
        if not self._client.is_connected():
            await self._client.connect()
        if await self._client.is_user_authorized():
            return self.save_session()
        if not phone:
            message = (
                "Telegram session is not authorized; set WEF_TELEGRAM_PHONE "
                "for first login or WEF_TELEGRAM_SESSION after generation"
            )
            raise TelegramSecretError(message)
        if login_code:
            try:
                await self._client.sign_in(phone, code=login_code)
            except SessionPasswordNeededError as error:
                if not password:
                    message = "Telegram two-step password required (WEF_TELEGRAM_2FA_PASSWORD)"
                    raise TelegramSecretError(message) from error
                await self._client.sign_in(password=password)
            if not await self._client.is_user_authorized():
                message = "Telegram sign-in did not produce an authorized session"
                raise TelegramSecretError(message)
            return self.save_session()
        if sys.stdin.isatty():
            await self._client.start(phone=phone, password=password)
            return self.save_session()
        await self._client.send_code_request(phone)
        message = "Telegram login code sent; set WEF_TELEGRAM_LOGIN_CODE and restart"
        raise TelegramLoginCodeError(message)

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

    async def latest_message_id(self, username: str) -> int:
        """Observe the newest remote message id without retaining its payload."""
        async for message in self.iter_messages(
            username=username,
            min_id=0,
            reverse=False,
            limit=1,
        ):
            return message.external_message_id
        return 0

    def subscribe_channel(self, username: str, queue: LiveEventQueue) -> None:
        """Register new/edit/delete handlers for one channel onto the serial queue."""
        from wef_backend.features.ingestion.infrastructure.telethon_events import (  # noqa: PLC0415
            delete_event_from_telethon,
            new_or_edit_event_from_telethon,
        )

        async def _on_new(event: object) -> None:
            try:
                message = getattr(event, "message", event)
                await queue.put(
                    new_or_edit_event_from_telethon(message, kind=LiveTelegramEventKind.NEW),
                )
            except Exception as error:  # noqa: BLE001
                await queue.fail(error)

        async def _on_edit(event: object) -> None:
            try:
                message = getattr(event, "message", event)
                await queue.put(
                    new_or_edit_event_from_telethon(message, kind=LiveTelegramEventKind.EDIT),
                )
            except Exception as error:  # noqa: BLE001
                await queue.fail(error)

        async def _on_delete(event: object) -> None:
            try:
                deleted_ids = getattr(event, "deleted_ids", ())
                await queue.put(delete_event_from_telethon(deleted_ids))
            except Exception as error:  # noqa: BLE001
                await queue.fail(error)

        self._client.add_event_handler(_on_new, events.NewMessage(chats=username))
        self._client.add_event_handler(_on_edit, events.MessageEdited(chats=username))
        self._client.add_event_handler(_on_delete, events.MessageDeleted(chats=username))

    async def run_until_disconnected(self) -> None:
        """Block until the Telethon client disconnects."""
        await self._client.run_until_disconnected()

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
