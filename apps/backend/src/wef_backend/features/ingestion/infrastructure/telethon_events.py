"""Convert Telethon update objects into inward LiveTelegramEvent values."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import _to_live_message

if TYPE_CHECKING:
    from collections.abc import Sequence


def new_or_edit_event_from_telethon(
    message: object,
    *,
    kind: LiveTelegramEventKind,
    received_at: datetime | None = None,
) -> LiveTelegramEvent:
    """Map a Telethon new/edit message into a live event."""
    if kind not in {LiveTelegramEventKind.NEW, LiveTelegramEventKind.EDIT}:
        message_text = "kind must be new or edit"
        raise ValueError(message_text)
    return LiveTelegramEvent(
        kind=kind,
        message=_to_live_message(message),
        received_at=received_at or datetime.now(UTC),
    )


def delete_event_from_telethon(
    deleted_ids: Sequence[int] | object,
    *,
    received_at: datetime | None = None,
) -> LiveTelegramEvent:
    """Map Telethon deleted message ids into a live delete event."""
    raw_ids = cast("Any", deleted_ids)
    if hasattr(raw_ids, "__iter__") and not isinstance(raw_ids, (str, bytes)):
        ids = tuple(int(item) for item in raw_ids)
    else:
        message = "deleted_ids must be an iterable of integers"
        raise TypeError(message)
    return LiveTelegramEvent(
        kind=LiveTelegramEventKind.DELETE,
        deleted_ids=ids,
        received_at=received_at or datetime.now(UTC),
    )
