"""Parser replay: re-derive canonical offers from the raw archive (E17-T2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.persistence import (
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunMode,
    RunStatus,
    normalized_location_key,
    redacted_error_summary,
)
from wef_backend.features.ingestion.application.raw_archive import record_to_live_event
from wef_backend.features.ingestion.application.telegram_events import (
    LiveTelegramEventKind,
    RawEventRecord,
)
from wef_backend.features.ingestion.application.telegram_live import (
    live_message_to_raw,
    source_identity_from_channel,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from wef_backend.features.ingestion.application.persistence import IngestionPersistencePort
    from wef_backend.features.ingestion.application.telegram_events import LiveTelegramEvent
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity

_BATCH_SIZE = 100
_MAX_ROUNDS = 5


@dataclass(frozen=True, slots=True)
class ReplayWorkItem:
    """One archived message event selected for canonical re-derivation."""

    channel_external_id: str
    external_message_id: int
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ReplaySummary:
    """Redacted result of one replay invocation."""

    reprocessed: int
    not_rederivable: int
    created: int
    unchanged: int
    revised: int
    skipped_non_candidate: int
    stale_after_replay: int


class RawReplayPort(Protocol):
    """Archive selection of messages whose canonical state is stale."""

    async def stale_message_events(
        self,
        *,
        parser_version: str,
        sentinel_hash: str,
        limit: int,
        exclude: frozenset[str] = frozenset(),
    ) -> Sequence[ReplayWorkItem]:
        """Return latest archived events for stale-parser or sentinel offers."""
        ...


def _work_key(item: ReplayWorkItem) -> str:
    return f"{item.channel_external_id}:{item.external_message_id}"


def _event_from_payload(item: ReplayWorkItem) -> LiveTelegramEvent:
    record = RawEventRecord(
        id=uuid4(),
        event_kind="new",
        channel_external_id=item.channel_external_id,
        external_message_id=item.external_message_id,
        payload=item.payload,
        received_at=datetime.now(UTC),
        attempts=0,
    )
    return record_to_live_event(record)


@dataclass(frozen=True, slots=True)
class RawParserReplayer:
    """Idempotently replay archived messages through the current parser.

    Selection targets offers whose stored parser version is older than the
    running parser or that still point at the unknown-location sentinel;
    re-persisting through the live upsert path rewrites both, so completed
    replays select nothing on the next run.
    """

    store: IngestionPersistencePort
    source: RawReplayPort
    identity: TelegramChannelIdentity

    async def __call__(self, *, release_sha: str | None = None) -> ReplaySummary:
        """Replay all stale archived messages and return redacted counts."""
        channel = source_identity_from_channel(self.identity)
        source_key = f"{channel.platform.value}:{channel.channel_id}"
        sentinel_hash = normalized_location_key(None)
        excluded: set[str] = set()
        reprocessed = 0
        not_rederivable = 0
        counts = RunCounts()
        async with self.store.run_lock(source_key):
            channel_id = await self.store.ensure_channel(
                platform=channel.platform.value,
                external_id=channel.channel_id,
                display_name=channel.channel_name,
            )
            run_id = await self.store.start_run(
                channel_id=channel_id,
                mode=RunMode.REPROCESS,
                parser_version=PARSER_VERSION,
                source_checksum=None,
                release_sha=release_sha,
            )
            checkpoint = RunCheckpoint()
            try:
                for _ in range(_MAX_ROUNDS):
                    items = await self.source.stale_message_events(
                        parser_version=PARSER_VERSION,
                        sentinel_hash=sentinel_hash,
                        limit=_BATCH_SIZE,
                        exclude=frozenset(excluded),
                    )
                    if not items:
                        break
                    progressed = False
                    for item in items:
                        try:
                            event = _event_from_payload(item)
                        except (TypeError, ValueError):
                            excluded.add(_work_key(item))
                            continue
                        if event.kind is LiveTelegramEventKind.DELETE or event.message is None:
                            excluded.add(_work_key(item))
                            continue
                        raw = live_message_to_raw(event.message, identity=channel)
                        extraction = extract_listing(raw)
                        if extraction.listing is None:
                            # The current parser no longer derives an offer from
                            # this source; keep the existing offer (canonical
                            # revised-offer semantics) and report it instead of
                            # rewriting history every run.
                            excluded.add(_work_key(item))
                            not_rederivable += 1
                            continue
                        advance = raw.external_message_id > checkpoint.last_source_index
                        _, checkpoint, counts, _ = await self.store.persist_live_upsert(
                            channel_id=channel_id,
                            run_id=run_id,
                            message=PersistableMessage(
                                raw=raw,
                                extraction=extraction,
                            ),
                            checkpoint=checkpoint,
                            counts=counts,
                            advance_checkpoint=advance,
                        )
                        reprocessed += 1
                        progressed = True
                    if not progressed:
                        for item in items:
                            excluded.add(_work_key(item))
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
        remaining = await self.source.stale_message_events(
            parser_version=PARSER_VERSION,
            sentinel_hash=sentinel_hash,
            limit=_BATCH_SIZE,
            exclude=frozenset(),
        )
        return ReplaySummary(
            reprocessed=reprocessed,
            not_rederivable=not_rederivable,
            created=counts.created,
            unchanged=counts.unchanged,
            revised=counts.revised,
            skipped_non_candidate=counts.skipped_non_candidate,
            stale_after_replay=len(remaining),
        )
