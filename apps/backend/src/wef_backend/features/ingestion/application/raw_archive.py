"""Background draining of landed raw events (E17-T1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEvent,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.application.telegram_live import LiveTelegramMessage
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointStore,
    read_durable_telegram_checkpoint,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Mapping

    from wef_backend.features.ingestion.application.telegram_events import (
        LiveTelegramEventProcessor,
        RawEventArchivePort,
        RawEventRecord,
    )
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


def record_to_live_event(record: RawEventRecord) -> LiveTelegramEvent:
    """Rebuild one archived record into the shared live event boundary."""
    kind = LiveTelegramEventKind(record.event_kind)
    if kind is LiveTelegramEventKind.DELETE:
        return LiveTelegramEvent(kind=kind, deleted_ids=(record.external_message_id,))
    published_at = _payload_timestamp(record.payload, "date_unixtime")
    if published_at is None:
        message = "archived message payload must carry date_unixtime"
        raise ValueError(message)
    payload_id = record.payload["id"]
    if not isinstance(payload_id, str | int):
        message = "archived message payload id must be numeric"
        raise TypeError(message)
    media_group = record.payload.get("media_group_id")
    return LiveTelegramEvent(
        kind=kind,
        message=LiveTelegramMessage(
            external_message_id=int(payload_id),
            text=str(record.payload.get("text", "")),
            published_at=published_at,
            edited_at=_payload_timestamp(record.payload, "edited_unixtime"),
            media_group_id=(
                str(media_group) if isinstance(media_group, str | int) else None
            ),
        ),
    )


def _payload_timestamp(payload: Mapping[str, object], key: str) -> datetime | None:
    raw = payload.get(key)
    if raw is None:
        return None
    return datetime.fromtimestamp(int(str(raw)), tz=UTC)


@dataclass(frozen=True, slots=True)
class RawEventDrainer:
    """Background recovery: reprocess events landed without a terminal outcome.

    The processor re-lands each record (a no-op against the unique archive key)
    and records the real outcome; failures are marked here with a safe category
    so bounded retries can exhaust without blocking the rest of the batch.
    """

    archive: RawEventArchivePort
    processor: LiveTelegramEventProcessor
    identity: TelegramChannelIdentity
    checkpoint_store: TelegramCheckpointStore | None = None
    batch_size: int = 25

    async def drain_once(
        self,
        *,
        release_sha: str | None = None,
        processing_lock: asyncio.Lock | None = None,
    ) -> int:
        """Process pending archived events one by one through the canonical path."""
        records = await self.archive.unprocessed_batch(self.batch_size)
        for record in records:
            event = record_to_live_event(record)
            resume_after = 0
            if self.checkpoint_store is not None:
                resume_after = await read_durable_telegram_checkpoint(
                    self.checkpoint_store,
                    channel_external_id=self.identity.channel_id,
                )
            try:
                if processing_lock is None:
                    await self.processor(
                        identity=self.identity,
                        events=(event,),
                        resume_after_external_id=resume_after,
                        release_sha=release_sha,
                        manage_connection=False,
                    )
                else:
                    async with processing_lock:
                        await self.processor(
                            identity=self.identity,
                            events=(event,),
                            resume_after_external_id=resume_after,
                            release_sha=release_sha,
                            manage_connection=False,
                        )
            except Exception as error:  # noqa: BLE001 - one poisoned event must not block others
                await self.archive.mark_attempt(
                    record.id,
                    outcome="failed",
                    error_category=safe_error_category(error),
                )
        return len(records)
