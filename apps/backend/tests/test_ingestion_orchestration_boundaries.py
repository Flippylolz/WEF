"""Bounded import, replay receipts and media ownership failure boundaries."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.test_complete_import import NOW, FakeBudget, FakeGeocoder, _result
from tests.test_dry_run import (
    _adapter,
    _messages,
    _write_export,
)
from tests.test_listing_extraction import _message
from wef_backend.features.ingestion.application.archive_processing import ArchiveResolution
from wef_backend.features.ingestion.application.complete_import import (
    DurableBudgetedGeocoder,
    ProviderReservation,
    prepare_import,
)
from wef_backend.features.ingestion.application.dry_run import _MutableRun, run_dry_run
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.media_recovery import (
    MediaRecoveryOutcome,
    MediaRecoveryRunner,
)
from wef_backend.features.ingestion.application.raw_archive import RawEventDrainer
from wef_backend.features.ingestion.application.telegram_events import RawEventRecord
from wef_backend.features.ingestion.domain import DryRunTerminalStatus
from wef_backend.features.ingestion.domain.geocoding import normalize_geocode_query
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity

if TYPE_CHECKING:
    from pathlib import Path

    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity


def test_prepare_import_reports_every_scanned_record_and_skips_malformed(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    _write_export(source, _messages())
    progress: list[int] = []

    prepared = prepare_import(_adapter(source), progress=progress.append)

    assert progress == [1, 2, 3, 4]
    assert prepared.summary.counts.total == 4
    assert [message.raw.external_message_id for message in prepared.messages] == [801, 802, 803]
    assert prepared.candidate_count == 1


async def test_durable_reservation_waits_before_calling_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = FakeBudget([ProviderReservation(uuid4(), NOW + timedelta(seconds=2))])
    hosted = FakeGeocoder(_result())

    async def sleep(delay: float) -> None:
        assert delay == 2
        assert hosted.calls == 0
        assert len(budget.queries) == 1
        assert budget.completions == []

    wait = AsyncMock(side_effect=sleep)
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.complete_import.asyncio.sleep", wait
    )
    geocoder = DurableBudgetedGeocoder(
        hosted,
        budget,
        uuid4(),
        "synthetic",
        10,
        timedelta(seconds=2),
        1,
        clock=lambda: NOW,
    )

    assert await geocoder.geocode(normalize_geocode_query("Warszawa")) == hosted.result
    wait.assert_awaited_once_with(2)
    assert hosted.calls == 1
    assert budget.completions == [("succeeded", None)]


def test_dry_run_publication_bounds_preserve_equal_timestamps(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    _write_export(
        source,
        [
            {
                "id": index + 1,
                "type": "message",
                "text": "ordinary message",
                "date_unixtime": str(int((NOW + timedelta(days=offset)).timestamp())),
            }
            for index, offset in enumerate((1, 1, 4))
        ],
    )
    report = run_dry_run(_adapter(source), monotonic=lambda: 0.0)
    assert report.terminal_status is DryRunTerminalStatus.SUCCEEDED
    assert report.source is not None
    assert report.source.published_from == NOW + timedelta(days=1)
    assert report.source.published_to == NOW + timedelta(days=4)
    assert report.counts.messages_evaluated == 3


@pytest.mark.parametrize(
    ("text", "boundary"),
    [
        ("For sale:", "candidate_at_threshold"),
        ("Location: Warszawa\nPrice: 700000 PLN", "non_candidate_one_below_threshold"),
    ],
)
def test_dry_run_retains_decisions_at_the_candidate_boundary(text: str, boundary: str) -> None:
    run = _MutableRun()
    run.add_extraction(extract_listing(_message(text)))
    assert run.candidate_boundaries == {boundary: 1}
    assert run.candidates + run.non_candidates == 1


def test_dry_run_does_not_invent_missing_content_type() -> None:
    extraction = extract_listing(_message("For sale:"))
    assert extraction.listing is not None
    run = _MutableRun()
    run.add_extraction(replace(extraction, listing=replace(extraction.listing, content_type=None)))
    assert run.candidates == 1
    assert run.content_types == {}


def test_dry_run_reports_unassociated_media(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    _write_export(
        source,
        [
            {
                "id": 1,
                "type": "message",
                "date_unixtime": "1924992000",
                "text": "ordinary message",
                "photo": "photos/synthetic.jpg",
            }
        ],
    )
    report = run_dry_run(_adapter(source), monotonic=lambda: 0.0)
    assert report.terminal_status is DryRunTerminalStatus.SUCCEEDED
    assert report.counts.media_total == 1
    assert report.counts.media_unassociated == 1
    assert report.counts.media_associated == 0
    assert sum(bucket.count for bucket in report.unassociated_media_reasons) == 1


def _archive_record() -> RawEventRecord:
    return RawEventRecord(
        id=uuid4(),
        event_kind="new",
        channel_external_id=default_live_channel_identity().channel_id,
        external_message_id=1,
        payload={"id": 1, "type": "message"},
        received_at=NOW,
        attempts=0,
    )


@pytest.mark.parametrize("batch_size", [0, 26])
def test_archive_drainer_rejects_unbounded_batch_sizes(batch_size: int) -> None:
    with pytest.raises(ValueError, match="archive batch size must be between 1 and 25"):
        RawEventDrainer(AsyncMock(), AsyncMock(), default_live_channel_identity(), batch_size)


async def test_archive_drainer_holds_the_processing_lock_until_receipt() -> None:
    record = _archive_record()
    archive = AsyncMock()
    archive.unprocessed_batch.return_value = [record]
    archive.mark_attempt.return_value = True
    lock = asyncio.Lock()

    async def process(
        *,
        record: RawEventRecord,
        identity: TelegramChannelIdentity,
        release_sha: str | None = None,
    ) -> ArchiveResolution:
        assert lock.locked()
        assert identity == default_live_channel_identity()
        assert release_sha == "synthetic-release"
        return ArchiveResolution(record.id, "applied", NOW)

    result = await RawEventDrainer(archive, process, default_live_channel_identity()).drain_once(
        release_sha="synthetic-release",
        processing_lock=lock,
    )
    assert not lock.locked()
    assert result.newly_terminal == 1
    assert result.last_committed_at == NOW
    archive.record_failure.assert_not_awaited()


async def test_archive_drainer_refuses_a_receipt_for_another_event() -> None:
    record = _archive_record()
    archive = AsyncMock()
    archive.unprocessed_batch.return_value = [record]
    process = AsyncMock(return_value=ArchiveResolution(uuid4(), "applied", NOW))
    result = await RawEventDrainer(archive, process, default_live_channel_identity()).drain_once()
    assert result.failed == 1
    assert result.newly_terminal == 0
    archive.mark_attempt.assert_not_awaited()
    assert archive.record_failure.await_args.args[0] == record.id
    assert archive.record_failure.await_args.args[1].category == "ValueError"


async def test_archive_drainer_does_not_count_a_repeated_terminal_receipt() -> None:
    record = _archive_record()
    archive = AsyncMock()
    archive.unprocessed_batch.return_value = [record]
    archive.mark_attempt.return_value = False
    process = AsyncMock(return_value=ArchiveResolution(record.id, "applied", NOW))
    result = await RawEventDrainer(archive, process, default_live_channel_identity()).drain_once()
    assert result.newly_terminal == 0
    assert result.unchanged_terminal == 1
    assert result.last_committed_at is None


async def test_archive_drainer_preserves_failure_when_failure_ledger_is_unavailable() -> None:
    record = _archive_record()
    archive = AsyncMock()
    archive.unprocessed_batch.return_value = [record]
    original, ledger_error = ValueError("synthetic malformed record"), OSError("synthetic ledger")
    archive.record_failure.side_effect = ledger_error
    drainer = RawEventDrainer(
        archive, AsyncMock(side_effect=original), default_live_channel_identity()
    )
    with pytest.raises(ValueError, match="synthetic malformed record") as caught:
        await drainer.drain_once()
    assert caught.value is original
    assert caught.value.__cause__ is ledger_error
    archive.mark_attempt.assert_not_awaited()


@pytest.mark.parametrize("mode", ["empty", "completed", "failed"])
async def test_archive_recovery_finishes_only_claimed_batches_with_their_outcome(mode: str) -> None:
    record = _archive_record()
    archive, recovery = AsyncMock(), AsyncMock()
    recovery.claim_batch.return_value = [] if mode == "empty" else [record]
    archive.mark_attempt.return_value = True
    process = AsyncMock(return_value=ArchiveResolution(record.id, "applied", NOW))
    if mode == "failed":
        process.side_effect = ValueError("synthetic malformed event")
    result = await RawEventDrainer(
        archive,
        process,
        default_live_channel_identity(),
        recovery=recovery,
    ).drain_once()
    recovery.claim_batch.assert_awaited_once_with(default_live_channel_identity().channel_id, 25)
    archive.unprocessed_batch.assert_not_awaited()
    if mode == "empty":
        recovery.finish_batch.assert_not_awaited()
        process.assert_not_awaited()
        assert result.selected == 0
    else:
        recovery.finish_batch.assert_awaited_once_with(
            default_live_channel_identity().channel_id,
            failed=mode == "failed",
        )
        assert result.newly_terminal == int(mode == "completed")
        assert result.failed == int(mode == "failed")


async def test_media_recovery_stops_after_ten_claims() -> None:
    store = AsyncMock()
    store.claim.side_effect = [uuid4() for _ in range(10)]
    store.finish.return_value = True
    recover = AsyncMock(return_value=MediaRecoveryOutcome("completed"))
    assert await MediaRecoveryRunner(store, recover).run_once() == 10
    assert store.claim.await_count == 10
    assert store.finish.await_count == 10
    assert recover.await_count == 10


async def test_media_recovery_renews_ownership_until_work_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AsyncMock()
    store.claim.side_effect = [uuid4(), None]
    store.finish.return_value = True
    renewed = asyncio.Event()

    async def renew(claim: object) -> bool:
        assert claim is not None
        renewed.set()
        return True

    async def recover(claim: object) -> MediaRecoveryOutcome:
        assert claim is not None
        await renewed.wait()
        return MediaRecoveryOutcome("completed")

    store.renew.side_effect = renew
    monkeypatch.setattr(
        "wef_backend.features.ingestion.application.media_recovery.LEASE_SECONDS", 0.003
    )
    assert await MediaRecoveryRunner(store, recover).run_once() == 1
    store.renew.assert_awaited_once()
    store.fail.assert_not_awaited()
