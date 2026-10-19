"""Historical operator stages preserve leases, bounded work and resumable pauses."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from tests.test_complete_import import EXPECTATION, FIXTURE, NOW, _prepared
from tests.test_persistence_application import FakeStore
from wef_backend import import_command
from wef_backend.database import DatabaseResources
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    CompleteImportStage,
    CompleteImportStatus,
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
    RunLease,
)
from wef_backend.features.ingestion.application.media_grouping import GROUPING_VERSION
from wef_backend.features.ingestion.domain import SourceAnchor
from wef_backend.features.ingestion.domain.media_storage import descriptor_identity
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    ImportVerification,
    LocationWorkItem,
    SQLAlchemyCompleteImportRepository,
)
from wef_backend.import_command import ImportStageContext
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
        SQLAlchemyIngestionPersistence,
    )


@dataclass
class StageHarness:
    """Real source preparation and inward persistence fake with scripted outer read models."""

    context: ImportStageContext
    repository: MagicMock
    persistence: FakeStore
    lease: RunLease


@pytest.fixture
def stage_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StageHarness:
    prepared = _prepared()
    repository = MagicMock()
    persistence = FakeStore()
    lease = RunLease(
        uuid4(),
        "synthetic-owner",
        1,
        CompleteImportStage.PERSISTENCE,
        CompleteImportStatus.RUNNING,
        NOW + timedelta(minutes=5),
    )

    async def claim(**kwargs: object) -> RunLease:
        assert kwargs["source_checksum"] == prepared.summary.source_checksum
        assert kwargs["source_size"] == prepared.summary.source.file_size
        assert kwargs["pipeline_version"] == PIPELINE_VERSION
        assert UUID(str(kwargs["owner_id"])).version == 4
        stage = kwargs["stage"]
        assert isinstance(stage, CompleteImportStage)
        return replace(lease, stage=stage)

    async def checkpoint(owned: RunLease, **kwargs: object) -> RunLease:
        assert owned.run_id == lease.run_id
        stage, status = kwargs["stage"], kwargs["status"]
        assert isinstance(stage, CompleteImportStage)
        assert isinstance(status, CompleteImportStatus)
        return replace(owned, stage=stage, status=status)

    repository.claim_run = AsyncMock(side_effect=claim)
    repository.checkpoint_run = AsyncMock(side_effect=checkpoint)
    repository.existing_source_checksums = AsyncMock(return_value={})
    repository.source_anchors = AsyncMock(return_value={})
    repository.existing_media_replays = AsyncMock(return_value=set())
    repository.pending_locations = AsyncMock(return_value=[])
    database = DatabaseResources(
        engine=cast("AsyncEngine", MagicMock()),
        session_factory=cast("async_sessionmaker[AsyncSession]", MagicMock()),
    )
    settings = Settings(
        env="test",
        source_path=tmp_path,
        restricted_originals_path=tmp_path / "originals",
        public_derivatives_path=tmp_path / "public",
        geoapify_api_key=SecretStr("synthetic-provider-key"),
        geoapify_requests_per_second=Decimal(4),
    )
    clock = MagicMock(wraps=datetime)
    clock.now.return_value = NOW
    monkeypatch.setattr(import_command, "datetime", clock)
    return StageHarness(
        ImportStageContext(
            prepared,
            cast("SQLAlchemyCompleteImportRepository", repository),
            cast("SQLAlchemyIngestionPersistence", persistence),
            database,
            settings,
        ),
        repository,
        persistence,
        lease,
    )


def test_prepare_inspects_source_and_finishes_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "synthetic.json"
    source.write_bytes(FIXTURE.read_bytes())
    inspected: list[Path] = []
    monkeypatch.setattr(import_command, "inspect_source", inspected.append)
    settings = Settings(
        env="test",
        source_path=tmp_path,
        historical_export_filename=source.name,
        historical_channel_id=EXPECTATION.channel_id,
        historical_channel_type=EXPECTATION.channel_type,
        historical_channel_name=EXPECTATION.channel_name,
    )
    prepared = import_command._prepare(settings)  # noqa: SLF001
    assert inspected == [tmp_path]
    assert prepared.summary.counts.total == 8
    assert prepared.summary.source.file_size == source.stat().st_size
    output = capsys.readouterr()
    assert "scan" in output.err
    assert output.out == ""
    assert str(source) not in output.err
    assert all(not item.raw.text or item.raw.text not in output.err for item in prepared.messages)


def _anchors(context: ImportStageContext, *, offers: bool = True) -> dict[int, SourceAnchor]:
    dispositions = context.prepared.media_dispositions
    owners = {item.association.listing_message_id for item in dispositions if item.association}
    ids = owners | {item.reference.source_message_id for item in dispositions}
    return {
        external_id: SourceAnchor(
            uuid4(), uuid4(), uuid4() if offers and external_id in owners else None
        )
        for external_id in ids
    }


async def test_dry_run_accounts_for_anchored_media_and_completed_replays(
    stage_harness: StageHarness,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    anchors = _anchors(context)
    first = context.prepared.media_dispositions[0].reference
    anchor = anchors[first.source_message_id]
    repository.source_anchors.return_value = anchors
    repository.existing_media_replays.return_value = {
        (
            anchor.source_message_id,
            first.media_index,
            anchor.revision_id,
            descriptor_identity(first.descriptor),
            GROUPING_VERSION,
        )
    }
    result = await import_command._dry_run(context.prepared, context.repository)  # noqa: SLF001
    assert result["media_to_process"] == len(context.prepared.media_dispositions) - 1
    repository.claim_run.assert_not_awaited()
    repository.checkpoint_run.assert_not_awaited()


@pytest.mark.parametrize("reuse_lease", [False, True])
async def test_persist_checkpoints_each_acknowledged_batch_and_retains_lease(
    stage_harness: StageHarness,
    *,
    reuse_lease: bool,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    result = await import_command._persist(  # noqa: SLF001
        context.prepared,
        context.repository,
        context.persistence,
        batch_size=1,
        lease=stage_harness.lease if reuse_lease else None,
    )
    count = len(context.prepared.messages)
    assert stage_harness.persistence.batches == [1] * count
    calls = repository.checkpoint_run.await_args_list
    assert [call.kwargs["checkpoint"]["messages"] for call in calls] == [
        *range(1, count + 1),
        count,
    ]
    assert calls[-1].kwargs["counts"] == {"processed": count}
    assert result.run_id == stage_harness.lease.run_id
    assert result.stage is CompleteImportStage.PERSISTENCE
    assert repository.claim_run.await_count == int(not reuse_lease)


async def test_persist_does_no_batch_work_for_unchanged_source(stage_harness: StageHarness) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    repository.existing_source_checksums.return_value = {
        item.raw.external_message_id: item.raw.checksum for item in context.prepared.messages
    }
    result = await import_command._persist(  # noqa: SLF001
        context.prepared,
        context.repository,
        context.persistence,
        batch_size=2,
    )
    assert stage_harness.persistence.batches == []
    repository.checkpoint_run.assert_awaited_once()
    assert repository.checkpoint_run.await_args.kwargs["counts"] == {"processed": 0}
    assert result.status is CompleteImportStatus.RUNNING


def _pending_locations() -> list[LocationWorkItem]:
    return [
        LocationWorkItem(uuid4(), f"ul. Syntetyczna {index}, Warszawa", "Wola")
        for index in range(3)
    ]


async def test_empty_geocode_stage_needs_no_provider_key(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    context = replace(
        context, settings=context.settings.model_copy(update={"geoapify_api_key": None})
    )
    build = MagicMock()
    monkeypatch.setattr(import_command, "build_location_resolver", build)
    result = await import_command._geocode(context, batch_size=2, max_provider_requests=3)  # noqa: SLF001
    build.assert_not_called()
    assert result.stage is CompleteImportStage.GEOCODE
    assert repository.checkpoint_run.await_args.kwargs["checkpoint"] == {"locations": 0}


@pytest.mark.parametrize("key", [None, SecretStr("")])
async def test_nonempty_geocode_stage_refuses_missing_or_blank_key(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
    key: SecretStr | None,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    repository.pending_locations.return_value = _pending_locations()
    context = replace(
        context, settings=context.settings.model_copy(update={"geoapify_api_key": key})
    )
    build = MagicMock()
    monkeypatch.setattr(import_command, "build_location_resolver", build)
    with pytest.raises(RuntimeError, match="WEF_GEOAPIFY_API_KEY is required"):
        await import_command._geocode(context, batch_size=2, max_provider_requests=3)  # noqa: SLF001
    build.assert_not_called()
    repository.checkpoint_run.assert_not_awaited()


async def test_geocode_bounds_checkpoints_and_preserves_pending_identity(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    pending = _pending_locations()
    repository.pending_locations.return_value = pending
    resolve = AsyncMock()
    build = MagicMock(return_value=resolve)
    monkeypatch.setattr(import_command, "build_location_resolver", build)
    result = await import_command._geocode(  # noqa: SLF001
        context,
        batch_size=2,
        max_provider_requests=3,
        lease=stage_harness.lease,
    )
    assert [call.kwargs for call in resolve.await_args_list] == [
        {"source_query": item.address, "district": item.district, "location_id": item.location_id}
        for item in pending
    ]
    assert [call.kwargs["checkpoint"] for call in repository.checkpoint_run.await_args_list] == [
        {"locations": 2},
        {"locations": 3},
    ]
    assert repository.checkpoint_run.await_args.kwargs["counts"] == {"remaining": 0}
    budgeted = build.call_args.args[1]
    assert budgeted.max_provider_requests == 3
    assert budgeted.minimum_interval == timedelta(milliseconds=250)
    assert budgeted.daily_limit == context.settings.geoapify_daily_quota
    assert budgeted.clock() == NOW
    assert result.status is CompleteImportStatus.RUNNING
    repository.claim_run.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "reason", "delay"),
    [
        (ProviderBatchLimitError(), "operator_batch_limit", timedelta(0)),
        (ProviderDailyBudgetError(), "daily_provider_budget", None),
        (ProviderPauseError(), "provider_transient", timedelta(minutes=15)),
    ],
)
async def test_geocode_pauses_resumably_after_committed_progress(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
    error: RuntimeError,
    reason: str,
    delay: timedelta | None,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    repository.pending_locations.return_value = _pending_locations()
    resolve = AsyncMock(side_effect=[None, error])
    monkeypatch.setattr(import_command, "build_location_resolver", MagicMock(return_value=resolve))
    result = await import_command._geocode(context, batch_size=2, max_provider_requests=3)  # noqa: SLF001
    checkpoint = repository.checkpoint_run.await_args.kwargs
    assert result.status is CompleteImportStatus.PAUSED
    assert checkpoint["pause_reason"] == reason
    assert checkpoint["checkpoint"] == {"geocode": 1}
    assert checkpoint["counts"] == {"processed": 1}
    expected = (
        datetime.combine(NOW.date() + timedelta(days=1), time.min, tzinfo=UTC)
        if delay is None
        else NOW + delay
    )
    assert checkpoint["next_eligible_at"] == expected
    assert resolve.await_count == 2
    repository.checkpoint_run.assert_awaited_once()


@pytest.mark.parametrize("offers", [False, True])
async def test_media_processes_bounded_work_with_optional_listing_ownership(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
    *,
    offers: bool,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    anchors = _anchors(context, offers=offers)
    repository.source_anchors.return_value = anchors
    processor = AsyncMock()
    monkeypatch.setattr(import_command, "ProcessMedia", MagicMock(return_value=processor))
    result = await import_command._media(  # noqa: SLF001
        context,
        batch_size=2,
        lease=stage_harness.lease,
    )
    count = len(context.prepared.media_dispositions)
    assert processor.await_count == count == 3
    assert [call.kwargs["checkpoint"] for call in repository.checkpoint_run.await_args_list] == [
        {"media": 2},
        {"media": 3},
    ]
    for call, disposition in zip(
        processor.await_args_list, context.prepared.media_dispositions, strict=True
    ):
        item = call.args[0]
        source = anchors[disposition.reference.source_message_id]
        assert item.source_message_id == source.source_message_id
        assert item.source_message_revision_id == source.revision_id
        assert item.source_ordinal == disposition.reference.media_index
        assert (item.offer_id is not None) is bool(offers and disposition.association)
        assert (item.association_confidence is not None) is (item.offer_id is not None)
    assert result.stage is CompleteImportStage.MEDIA
    repository.claim_run.assert_not_awaited()


@pytest.mark.parametrize("replayed", [False, True])
async def test_media_skips_missing_anchors_and_completed_replays(
    stage_harness: StageHarness,
    monkeypatch: pytest.MonkeyPatch,
    *,
    replayed: bool,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    anchors = _anchors(context) if replayed else {}
    repository.source_anchors.return_value = anchors
    repository.existing_media_replays.return_value = (
        {
            (
                anchors[item.reference.source_message_id].source_message_id,
                item.reference.media_index,
                anchors[item.reference.source_message_id].revision_id,
                descriptor_identity(item.reference.descriptor),
                GROUPING_VERSION,
            )
            for item in context.prepared.media_dispositions
        }
        if replayed
        else set()
    )
    processor = AsyncMock()
    monkeypatch.setattr(import_command, "ProcessMedia", MagicMock(return_value=processor))
    await import_command._media(context, batch_size=2)  # noqa: SLF001
    processor.assert_not_awaited()
    assert repository.checkpoint_run.await_args.kwargs["counts"] == {"remaining": 0}
    assert repository.checkpoint_run.await_args.kwargs["checkpoint"] == {"media": 0}


@pytest.mark.parametrize("complete", [False, True])
async def test_verify_requires_persisted_source_before_marking_success(
    stage_harness: StageHarness,
    *,
    complete: bool,
) -> None:
    context, repository = stage_harness.context, stage_harness.repository
    if complete:
        repository.existing_source_checksums.return_value = {
            item.raw.external_message_id: item.raw.checksum for item in context.prepared.messages
        }
    verification = ImportVerification(
        len(context.prepared.messages),
        len(context.prepared.messages),
        context.prepared.candidate_count,
        1,
        0,
        0,
        0,
        0,
        0,
    )
    repository.verify = AsyncMock(return_value=verification)
    if complete:
        lease, counts = await import_command._verify(  # noqa: SLF001
            context.prepared,
            context.repository,
            context.persistence,
        )
        assert lease.status is CompleteImportStatus.SUCCEEDED
        assert counts == asdict(verification)
        assert repository.checkpoint_run.await_args.kwargs["checkpoint"] == {"verified": True}
    else:
        with pytest.raises(RuntimeError, match="verification found unpersisted source messages"):
            await import_command._verify(  # noqa: SLF001
                context.prepared,
                context.repository,
                context.persistence,
                lease=stage_harness.lease,
            )
        repository.checkpoint_run.assert_not_awaited()


def test_python_module_entrypoint_exposes_the_operator_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["wef-import", "--help"])
    with pytest.raises(SystemExit) as captured:
        runpy.run_path(str(import_command.__file__), run_name="__main__")
    assert captured.value.code == 0
    output = capsys.readouterr()
    assert "Resumable, incremental Telegram JSON import" in output.out
    assert "--max-provider-requests" in output.out
    assert output.err == ""
