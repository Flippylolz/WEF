"""In-memory Telegram client for deterministic E8-T2 tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.telegram_progress import SourceObservation

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from wef_backend.features.ingestion.application.telegram_live import (
        LiveTelegramMessage,
        TelegramChannelEntity,
    )


@dataclass
class FakeTelegramLiveClient:
    """Deterministic live client with an in-memory message stream."""

    entity: TelegramChannelEntity
    messages: Sequence[LiveTelegramMessage] = ()
    connected: bool = False
    resolve_calls: list[str] = field(default_factory=list)

    async def observe_messages(
        self, *, username: str, ids: Sequence[int]
    ) -> Sequence[SourceObservation]:
        """Confirm only retained fake messages; absent IDs remain unknown."""
        await self.resolve_channel(username)
        by_id = {message.external_message_id: message for message in self.messages}
        return tuple(
            SourceObservation(external_id, "present", by_id[external_id])
            if external_id in by_id
            else SourceObservation(external_id, "unknown")
            for external_id in ids
        )

    async def connect(self) -> None:
        """Mark the fake client connected."""
        self.connected = True

    async def disconnect(self) -> None:
        """Mark the fake client disconnected."""
        self.connected = False

    async def resolve_channel(self, username: str) -> TelegramChannelEntity:
        """Return the configured entity when the username matches."""
        self.resolve_calls.append(username)
        if username.casefold() != self.entity.username.casefold():
            message = "fake channel username not found"
            raise LookupError(message)
        return self.entity

    async def latest_message_id(self, username: str) -> int:
        """Return the largest fake message id for the verified channel."""
        await self.resolve_channel(username)
        return max((message.external_message_id for message in self.messages), default=0)

    async def iter_messages(
        self,
        *,
        username: str,
        min_id: int,
        reverse: bool = True,
        limit: int | None = None,
    ) -> AsyncIterator[LiveTelegramMessage]:
        """Yield in-memory messages for the configured channel."""
        if not self.connected:
            message = "fake client is not connected"
            raise RuntimeError(message)
        if username.casefold() != self.entity.username.casefold():
            message = "fake channel username not found"
            raise LookupError(message)
        ordered = sorted(
            (item for item in self.messages if item.external_message_id > min_id),
            key=lambda item: item.external_message_id,
            reverse=not reverse,
        )
        if limit is not None:
            ordered = ordered[:limit]
        for item in ordered:
            yield item
