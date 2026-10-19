"""Live ingestion cleanup, replay and bounded provider failure tests."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_location_resolution import SOURCE, resolution
from tests.test_media_grouping import _input, _message
from tests.test_telegram_live_backfill import _FakeStore
from tests.test_telegram_reconciliation import _CheckpointStore, _client, _Processor
from tests.test_telegram_reconciliation import _message as _live_message
from wef_backend.features.ingestion.application.complete_import import (
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.application.live_media import LiveMediaPipeline
from wef_backend.features.ingestion.application.location_resolution import (
    ResolveLocation,
    _grounded_street,
    recovered_address,
)
from wef_backend.features.ingestion.application.media_grouping import (
    GROUPING_VERSION,
    StatefulMediaGrouper,
)
from wef_backend.features.ingestion.application.recurring_geocode import (
    RecurringDeferAction,
    classify_recurring_budget_error,
    classify_recurring_provider_outcome,
)
from wef_backend.features.ingestion.application.telegram_backfill import (
    LiveBackfillRequest,
    LiveTelegramBackfill,
)
from wef_backend.features.ingestion.application.telegram_channel_verify import (
    verify_telegram_channel_access,
)
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEvent,
    LiveTelegramEventKind,
    LiveTelegramEventProcessor,
)
from wef_backend.features.ingestion.application.telegram_live import (
    live_message_to_raw,
    source_identity_from_channel,
)
from wef_backend.features.ingestion.application.telegram_progress import (
    ChannelProgress,
    SourceObservation,
    SweepBatch,
)
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointReconciler,
    TelegramReconciliationRequest,
    maintain_checkpoint_reconciliation,
)
from wef_backend.features.ingestion.application.telegram_worker_liveness import WorkerRuntimeState
from wef_backend.features.ingestion.domain import MediaDescriptor, MediaKind, SourceAnchor
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.domain.media_storage import descriptor_identity
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity
from wef_backend.features.ingestion.domain.telegram_secrets import TelegramSecretError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from wef_backend.features.ingestion.application.telegram_live import LiveTelegramMessage


@pytest.mark.parametrize("mode", ["missing_anchor", "replay"])
async def test_live_media_skips_unprocessable_or_terminal_descriptors(mode: str) -> None:
    """Missing durable anchors and replay keys never call storage."""
    raw = _message(
        1,
        0,
        message_type="service" if mode == "service" else "message",
        media_kinds=(MediaKind.PHOTO,),
    )
    processor, anchors = AsyncMock(), MagicMock()
    source = SourceAnchor(uuid4(), uuid4(), None)
    anchors.source_anchors = AsyncMock(return_value={} if mode == "missing_anchor" else {1: source})
    anchors.existing_media_replays = AsyncMock(
        return_value={
            (
                source.source_message_id,
                0,
                source.revision_id,
                descriptor_identity(raw.media[0]),
                GROUPING_VERSION,
            )
        }
        if mode == "replay"
        else set()
    )
    assert (
        await LiveMediaPipeline(processor, anchors, StatefulMediaGrouper()).process_message(
            channel=raw.source, raw=raw
        )
        == 0
    )
    processor.assert_not_awaited()


def test_grouping_rejects_empty_version_before_mutating_state() -> None:
    """Every output must have a nonempty association version."""
    with pytest.raises(ValueError, match="version must not be empty"):
        StatefulMediaGrouper(grouping_version="").ingest(
            _input(_message(1, 0), expected_candidate=False)
        )


def test_explicit_album_owner_wins_over_reply_without_activating_adjacency() -> None:
    """A reply inside a known album retains its explicit owner only for that media."""
    grouper = StatefulMediaGrouper()
    grouper.ingest(
        _input(_message(1, 0, text="Kupno | Mieszkanie", group_id="album"), expected_candidate=True)
    )
    dispositions = grouper.ingest(
        _input(
            _message(2, 1, group_id="album", reply_to=999, media_kinds=(MediaKind.PHOTO,)),
            expected_candidate=False,
        )
    )
    assert len(dispositions) == 1
    assert dispositions[0].association is not None
    assert dispositions[0].association.listing_message_id == 1


@pytest.mark.parametrize("recovered", [None, SOURCE])
async def test_location_recovery_does_not_repeat_unchanged_lookup(recovered: str | None) -> None:
    """No recovery or the original query cannot trigger a redundant provider call."""
    municipal, hosted = AsyncMock(return_value=resolution()), AsyncMock(return_value=resolution())
    recovery = MagicMock(recover=AsyncMock(return_value=recovered))
    result = await ResolveLocation(municipal, hosted, MagicMock(), recovery)(source_query=SOURCE)
    assert not result.decision.select_result
    municipal.assert_awaited_once()
    hosted.assert_awaited_once()


def test_recovery_requires_an_address_and_explicit_street_marker() -> None:
    """Bare locality text and unlabeled street suffixes do not ground an address."""
    assert recovered_address("Warszawa", None, "Warszawa") is None
    assert _grounded_street("ul. Syntetyczna 12", None, "Syntetyczna")
    assert not _grounded_street("Syntetyczna 12", None, "Syntetyczna")


@pytest.mark.parametrize("code", list(GeocodeErrorCode))
def test_all_recurring_provider_outcomes_have_a_defined_action(code: GeocodeErrorCode) -> None:
    """The full provider vocabulary maps to an explicit worker action."""
    expected = {
        GeocodeErrorCode.NO_RESULT: RecurringDeferAction.CONTINUE,
        GeocodeErrorCode.QUOTA: RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY,
        GeocodeErrorCode.TRANSIENT: RecurringDeferAction.DEFER_TRANSIENT,
        GeocodeErrorCode.TIMEOUT: RecurringDeferAction.DEFER_TRANSIENT,
        GeocodeErrorCode.INVALID_RESPONSE: RecurringDeferAction.DEFER_TRANSIENT,
        GeocodeErrorCode.POLICY: RecurringDeferAction.LEAVE_UNGEOCODED,
    }
    assert classify_recurring_provider_outcome(code) is expected[code]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderBatchLimitError(), RecurringDeferAction.DEFER_TRANSIENT),
        (ProviderPauseError(), RecurringDeferAction.DEFER_TRANSIENT),
        (ProviderDailyBudgetError(), RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY),
    ],
)
def test_recurring_budget_errors_defer_without_dropping_work(
    error: Exception, expected: RecurringDeferAction
) -> None:
    """Both local allowance and durable quota failures remain resumable."""
    assert classify_recurring_budget_error(error) is expected


def test_unknown_recurring_budget_error_is_not_silently_classified() -> None:
    """Programming failures propagate instead of becoming an unbounded retry."""
    with pytest.raises(TypeError, match="unsupported recurring"):
        classify_recurring_budget_error(ValueError("synthetic"))


async def test_public_channel_refusal_precedes_credential_readiness() -> None:
    """Credential presence cannot make an unreachable public channel look healthy."""
    get = AsyncMock(return_value=404)
    result = await verify_telegram_channel_access(
        default_live_channel_identity(), credentials_ready=True, session_ready=True, get=get
    )
    assert result.status == "public_unreachable"
    assert not result.public_message_reachable
    get.assert_awaited_once_with(result.public_message_url)


@pytest.mark.parametrize("kind", [MediaKind.PHOTO, MediaKind.THUMBNAIL])
def test_live_payload_preserves_dimensions_and_thumbnail_kind(kind: MediaKind) -> None:
    """All image dimensions survive normalization without promoting thumbnails."""
    message = replace(
        _live_message(1), media=(MediaDescriptor(kind, "1/image.jpg", width=640, height=480),)
    )
    raw = live_message_to_raw(
        message, identity=source_identity_from_channel(default_live_channel_identity())
    )
    assert raw.raw_payload["width"] == 640
    assert raw.raw_payload["height"] == 480
    assert ("photo" in raw.raw_payload) == (kind is MediaKind.PHOTO)
    assert "file" not in raw.raw_payload


async def test_live_queue_ready_work_reflects_queued_events() -> None:
    """Bounded maintenance sees live work immediately after enqueue."""
    queue = LiveEventQueue()
    assert not queue.has_ready_work
    await queue.put(LiveTelegramEvent(LiveTelegramEventKind.NEW, message=_live_message(1)))
    assert queue.has_ready_work


@pytest.mark.parametrize("mode", ["success", "storage_failure", "old_ids"])
async def test_backfill_releases_media_leases_on_every_exit(mode: str) -> None:
    """Committed, failed and excluded windows all release bounded staging leases."""
    lease = MagicMock()
    message = replace(
        _live_message(10),
        media=(MediaDescriptor(MediaKind.PHOTO, "10/photo.jpg"),),
        media_lease=lease,
    )
    client = _client(())

    async def stream(**_kwargs: object) -> AsyncIterator[LiveTelegramMessage]:
        if mode == "old_ids":
            yield replace(message, external_message_id=4, media_lease=None)
            yield replace(message, external_message_id=5)
        else:
            yield message
            yield _live_message(11)

    client.iter_messages = stream  # type: ignore[method-assign]
    store = _FakeStore()
    pipeline = MagicMock(process_message=AsyncMock())
    if mode == "storage_failure":
        pipeline.process_message.side_effect = RuntimeError("synthetic storage outage")
    backfill = LiveTelegramBackfill(store, client, pipeline)
    request = LiveBackfillRequest(
        default_live_channel_identity(), resume_after_external_id=5, overlap=0, batch_size=20
    )
    if mode == "storage_failure":
        with pytest.raises(RuntimeError, match="synthetic storage outage"):
            await backfill(request)
    else:
        result = await backfill(request)
        assert result.messages_seen == (0 if mode == "old_ids" else 2)
    lease.release.assert_called_once()
    assert not client.connected
    assert pipeline.process_message.await_count == (0 if mode == "old_ids" else 1)


@pytest.mark.parametrize("mode", ["no_store", "no_ids", "mismatched", "deferred"])
async def test_reconciliation_sweep_boundaries_preserve_unknown_history(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing or mismatched source observations never count as confirmed deletion."""
    identity = default_live_channel_identity()
    stop = asyncio.Event()
    sweep = MagicMock()
    sweep.sweep_batch = AsyncMock(
        return_value=SweepBatch(() if mode == "no_ids" else (2,), uuid4())
    )
    sweep.finish_sweep_batch = AsyncMock()
    progress = ChannelProgress(applied_high_water_id=8, polled_through_id=10, history_limited=True)
    if mode == "deferred":
        progress = replace(progress, source_retry_at=datetime.now(UTC) + timedelta(minutes=1))
    sweep.channel_progress = AsyncMock(return_value=progress)
    client = _client(())
    monkeypatch.setattr(
        client,
        "observe_messages",
        AsyncMock(return_value=(SourceObservation(2, "present", _live_message(999)),)),
    )

    async def latest(_username: str) -> int:
        stop.set()
        return 10

    monkeypatch.setattr(client, "latest_message_id", latest)
    processor = _Processor()
    reconciler = TelegramCheckpointReconciler(
        _CheckpointStore(10, 10),
        client,
        processor,
        asyncio.Lock(),
        sweep_store=None if mode == "no_store" else sweep,
    )
    if mode == "deferred":
        # Deferred calls never inspect the remote head, so stop after reading progress.
        async def read_progress(**_kwargs: object) -> ChannelProgress:
            stop.set()
            return progress

        sweep.channel_progress.side_effect = read_progress
    state = WorkerRuntimeState()
    await maintain_checkpoint_reconciliation(
        reconciler, TelegramReconciliationRequest(identity), state=state, stop=stop, interval=0.01
    )
    assert not processor.calls
    if mode == "mismatched":
        assert sweep.finish_sweep_batch.await_args.kwargs["unknown"] == 1
    if mode != "no_store":
        assert state.applied_high_water_id == 8
        assert state.history_limited
    if mode == "deferred":
        assert state.last_reconciliation_at is None


def test_location_recovery_refuses_normalizer_without_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A degraded normalizer result cannot be used to invent address context."""
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.location_resolution.normalize_geocode_query",
        lambda _source, _district: replace(normalize_geocode_query(SOURCE), address=None),
    )
    assert recovered_address(SOURCE, None, "Syntetyczna") is None


def test_live_payload_refuses_nonobject_freezing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The archive payload boundary rejects a collaborator returning the wrong JSON shape."""
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.telegram_live.freeze_json", lambda _payload: ()
    )
    with pytest.raises(TypeError, match="must freeze as an object"):
        live_message_to_raw(
            _live_message(1), identity=source_identity_from_channel(default_live_channel_identity())
        )


@pytest.mark.parametrize("mode", ["old_id", "unordered"])
async def test_reconciliation_checks_forward_source_order_and_releases_leases(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source that ignores cursor/order cannot move the durable checkpoint backward."""
    client = _client((_live_message(12),))
    lease = MagicMock()

    async def stream(**_kwargs: object) -> AsyncIterator[LiveTelegramMessage]:
        if mode == "old_id":
            yield replace(_live_message(9), media_lease=lease)
            yield _live_message(12)
        else:
            yield _live_message(12)
            yield replace(_live_message(11), media_lease=lease)

    monkeypatch.setattr(client, "iter_messages", stream)
    store, processor = _CheckpointStore(10, 10), _Processor()
    reconciler = TelegramCheckpointReconciler(store, client, processor, asyncio.Lock())
    request = TelegramReconciliationRequest(default_live_channel_identity(), overlap=0)
    if mode == "unordered":
        with pytest.raises(ValueError, match="not ordered"):
            await reconciler(request)
    else:
        result = await reconciler(request)
        assert result.messages_fetched == 1
    assert store.checkpoint == 12
    lease.release.assert_called_once()
    assert len(processor.calls) == 1


async def test_reconciliation_does_not_swallow_systemic_processing_failures() -> None:
    """Landing is retained with a safe failure before a systemic exception propagates."""
    client = _client((_live_message(1),))
    archive = MagicMock(
        land=AsyncMock(return_value=uuid4()),
        can_attempt=AsyncMock(return_value=True),
        record_failure=AsyncMock(),
    )
    processor = AsyncMock(side_effect=TelegramSecretError("synthetic systemic failure"))
    reconciler = TelegramCheckpointReconciler(
        _CheckpointStore(0, 0), client, processor, asyncio.Lock(), archive=archive
    )
    with pytest.raises(TelegramSecretError, match="synthetic systemic failure"):
        await reconciler(TelegramReconciliationRequest(default_live_channel_identity()))
    assert archive.record_failure.await_count == 1
    assert archive.record_failure.await_args.args[1].kind == "systemic"


async def test_reconciliation_zero_sweep_budget_does_not_request_observations() -> None:
    """A forward page that consumes the cadence allowance leaves the sweep untouched."""
    client = _client(tuple(_live_message(i) for i in range(1, 11)))
    sweep = MagicMock(
        channel_progress=AsyncMock(return_value=ChannelProgress()), sweep_batch=AsyncMock()
    )
    reconciler = TelegramCheckpointReconciler(
        _CheckpointStore(0, 0), client, _Processor(), asyncio.Lock(), sweep_store=sweep
    )
    await reconciler(
        TelegramReconciliationRequest(default_live_channel_identity(), max_messages=10)
    )
    sweep.sweep_batch.assert_not_awaited()


async def test_deletion_receipt_helper_without_archive_is_a_noop() -> None:
    """Optional archive integration never makes canonical deletion require a ledger."""
    processor = LiveTelegramEventProcessor(MagicMock(), _client(()))
    await processor._mark_delete_outcomes(((uuid4(), 1),), ())  # noqa: SLF001 - optional ledger boundary
