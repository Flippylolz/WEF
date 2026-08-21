"""Orchestrate bounded live Telegram backfill through shared persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
    redacted_error_summary,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveBackfillResult,
    live_message_to_raw,
    source_identity_from_channel,
    verify_channel_entity,
)

if TYPE_CHECKING:
    from wef_backend.features.ingestion.application.persistence import IngestionPersistencePort
    from wef_backend.features.ingestion.application.telegram_live import TelegramLiveClientPort
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity

_DEFAULT_BATCH = 50
_DEFAULT_OVERLAP = 25


@dataclass(frozen=True, slots=True)
class LiveBackfillRequest:
    """Bounded live backfill inputs (no secret material)."""

    identity: TelegramChannelIdentity
    resume_after_external_id: int = 0
    overlap: int = _DEFAULT_OVERLAP
    limit: int | None = None
    batch_size: int = _DEFAULT_BATCH
    release_sha: str | None = None


@dataclass(frozen=True, slots=True)
class LiveTelegramBackfill:
    """One-shot backfill: verify entity, lock, persist, advance checkpoint by message id."""

    store: IngestionPersistencePort
    client: TelegramLiveClientPort

    async def __call__(self, request: LiveBackfillRequest) -> LiveBackfillResult:
        """Run a restartable live backfill window under the channel advisory lock."""
        await self.client.connect()
        try:
            entity = await self.client.resolve_channel(request.identity.username)
            verify_channel_entity(request.identity, entity)
            channel = source_identity_from_channel(request.identity)
            source_key = f"{channel.platform.value}:{channel.channel_id}"
            min_id = max(0, request.resume_after_external_id - request.overlap)
            async with self.store.run_lock(source_key):
                channel_id = await self.store.ensure_channel(
                    platform=channel.platform.value,
                    external_id=channel.channel_id,
                    display_name=channel.channel_name,
                )
                run_id = await self.store.start_run(
                    channel_id=channel_id,
                    mode=RunMode.LIVE,
                    parser_version=PARSER_VERSION,
                    source_checksum=None,
                    release_sha=request.release_sha,
                )
                # Overlap may re-persist ids below the durable resume point;
                # start the in-run cursor at min_id so advances() stays forward-only.
                checkpoint = RunCheckpoint(
                    last_source_index=min_id if min_id > 0 else -1,
                )
                counts = RunCounts()
                batch: list[tuple[PersistableMessage, int]] = []
                try:
                    async for live in self.client.iter_messages(
                        username=request.identity.username,
                        min_id=min_id,
                        reverse=True,
                        limit=request.limit,
                    ):
                        if live.external_message_id <= min_id:
                            continue
                        raw = live_message_to_raw(live, identity=channel)
                        batch.append(
                            (
                                PersistableMessage(raw=raw, extraction=extract_listing(raw)),
                                live.external_message_id,
                            )
                        )
                        if len(batch) >= request.batch_size:
                            _, checkpoint, counts, _ = await self.store.persist_batch(
                                channel_id=channel_id,
                                run_id=run_id,
                                batch=tuple(batch),
                                checkpoint=checkpoint,
                                counts=counts,
                            )
                            batch.clear()
                    if batch:
                        _, checkpoint, counts, _ = await self.store.persist_batch(
                            channel_id=channel_id,
                            run_id=run_id,
                            batch=tuple(batch),
                            checkpoint=checkpoint,
                            counts=counts,
                        )
                except PersistenceBatchError as error:
                    await self.store.finish_run(
                        run_id=run_id,
                        status=RunStatus.FAILED,
                        counts=counts,
                        checkpoint=checkpoint,
                        error_summary=redacted_error_summary(error),
                    )
                    raise
                await self.store.finish_run(
                    run_id=run_id,
                    status=RunStatus.SUCCEEDED,
                    counts=counts,
                    checkpoint=checkpoint,
                    error_summary=None,
                )
                durable = max(
                    checkpoint.last_source_index,
                    request.resume_after_external_id,
                    0,
                )
                return LiveBackfillResult(
                    verified_channel_id=entity.channel_id,
                    messages_seen=counts.seen,
                    checkpoint_external_message_id=durable,
                    created=counts.created,
                    unchanged=counts.unchanged,
                    revised=counts.revised,
                    skipped_non_candidate=counts.skipped_non_candidate,
                )
        finally:
            await self.client.disconnect()
