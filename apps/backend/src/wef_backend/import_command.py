"""Resumable staged historical import operator with incremental dry-run planning."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from wef_backend.database import create_database_resources
from wef_backend.features.contacts.infrastructure import (
    AesGcmContactCipher,
    decode_secret_key,
)
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    CompleteImportStage,
    CompleteImportStatus,
    DurableBudgetedGeocoder,
    PreparedImport,
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
    build_incremental_plan,
    messages_to_process,
    prepare_import,
)
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.application.media_grouping import GROUPING_VERSION
from wef_backend.features.ingestion.application.media_storage import MediaWorkItem, ProcessMedia
from wef_backend.features.ingestion.application.persistence import (
    PersistHistoricalIngestion,
    RunMetadata,
    confidence_score,
)
from wef_backend.features.ingestion.application.source import ChannelExpectation
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.domain.media_storage import MediaLimits, descriptor_identity
from wef_backend.features.ingestion.infrastructure import (
    CompleteImportLeaseHeldError,
    HostedGeocoder,
    HTTPXJSONTransport,
    LocalMediaStorage,
    ProviderPolicy,
    SQLAlchemyCompleteImportRepository,
    SQLAlchemyGeocodeStore,
    SQLAlchemyMediaRepository,
    TelegramDesktopExportAdapter,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.operator import UnsafeSourceMountError, inspect_source
from wef_backend.settings import Settings, load_settings

if TYPE_CHECKING:
    from collections.abc import Mapping
    from io import TextIOBase

    from wef_backend.database import DatabaseResources
    from wef_backend.features.ingestion.application.complete_import import RunLease
    from wef_backend.features.ingestion.application.persistence import RunCounts

_DEFAULT_BATCH_SIZE = 200
_DEFAULT_GEOCODE_BATCH_SIZE = 25
_DEFAULT_MAX_PROVIDER_REQUESTS = 500
_LEASE_DURATION = timedelta(minutes=5)
_MEDIA_CONCURRENCY = 4
_NONINTERACTIVE_PROGRESS_STEP = 500


class TerminalProgress:
    """Small dependency-free progress bar that never logs source values."""

    def __init__(
        self,
        label: str,
        total: int | None,
        *,
        output: TextIOBase | None = None,
    ) -> None:
        """Initialize one bounded terminal renderer."""
        self.label = label
        self.total = total
        self.output = output or sys.stderr
        self.current = 0
        self._last_rendered = -1
        self._interactive = bool(getattr(self.output, "isatty", lambda: False)())

    def update(self, current: int) -> None:
        """Render monotonic progress without emitting one line per record."""
        self.current = max(self.current, current)
        if (
            self._interactive
            or self.current == 1
            or self.current - self._last_rendered >= _NONINTERACTIVE_PROGRESS_STEP
        ):
            self._render(final=False)

    def finish(self, *, complete: bool = True) -> None:
        """Render one final line, optionally without claiming completion."""
        if complete and self.total is not None:
            self.current = max(self.current, self.total)
        self._render(final=True)

    def _render(self, *, final: bool) -> None:
        width = 28
        if self.total is None or self.total <= 0:
            bar = "=" * min(width, (self.current // 100) % (width + 1))
            rendered = f"{self.label:12} [{bar:<{width}}] {self.current:,}"
        else:
            ratio = min(1.0, self.current / self.total)
            filled = round(width * ratio)
            bar = "#" * filled + "-" * (width - filled)
            rendered = f"{self.label:12} [{bar}] {ratio:6.1%} {self.current:,}/{self.total:,}"
        end = "\n" if final or not self._interactive else "\r"
        self.output.write(rendered + end)
        self.output.flush()
        self._last_rendered = self.current


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wef-import",
        description="Resumable, incremental Telegram JSON import into PostgreSQL/PostGIS.",
    )
    parser.add_argument("--batch-size", type=_positive_int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--geocode-batch-size",
        type=_positive_int,
        default=_DEFAULT_GEOCODE_BATCH_SIZE,
    )
    parser.add_argument(
        "--max-provider-requests",
        type=_positive_int,
        default=_DEFAULT_MAX_PROVIDER_REQUESTS,
    )
    parser.add_argument(
        "command",
        choices=("dry-run", "persist", "geocode", "media", "verify", "run"),
    )
    return parser


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        message = "value must be a positive integer"
        raise argparse.ArgumentTypeError(message)
    return parsed


def _adapter(settings: Settings) -> TelegramDesktopExportAdapter:
    return TelegramDesktopExportAdapter(
        settings.source_path / settings.historical_export_filename,
        ChannelExpectation(
            channel_id=settings.historical_channel_id,
            channel_type=settings.historical_channel_type,
            channel_name=settings.historical_channel_name,
        ),
    )


def _prepare(settings: Settings) -> PreparedImport:
    inspect_source(settings.source_path)
    progress = TerminalProgress("scan", None)
    prepared = prepare_import(_adapter(settings), progress=progress.update)
    progress.total = prepared.summary.counts.total
    progress.finish()
    return prepared


async def _dry_run(
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
) -> dict[str, object]:
    existing = await repository.existing_source_checksums(prepared.channel)
    plan = build_incremental_plan(prepared, existing)
    anchors = await repository.source_anchors(prepared.channel)
    replayed = await repository.existing_media_replays(prepared.channel)
    media_to_process = 0
    for disposition in prepared.media_dispositions:
        anchor = anchors.get(disposition.reference.source_message_id)
        if anchor is None:
            media_to_process += 1
            continue
        replay_key = (
            anchor.source_message_id,
            disposition.reference.media_index,
            anchor.revision_id,
            descriptor_identity(disposition.reference.descriptor),
            GROUPING_VERSION,
        )
        media_to_process += int(replay_key not in replayed)
    pending_locations = await repository.pending_locations()
    result = asdict(plan)
    result.update(
        {
            "candidate_messages_to_persist": sum(
                1
                for item in messages_to_process(prepared, existing)
                if item.extraction is not None and item.extraction.listing is not None
            ),
            "messages_to_process": plan.messages_to_process,
            "media_to_process": media_to_process,
            "locations_currently_pending": len(pending_locations),
            "parser_version": PARSER_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "source_checksum": prepared.summary.source_checksum,
            "status": "dry_run",
        },
    )
    return result


async def _claim(
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
    persistence: SQLAlchemyIngestionPersistence,
    stage: CompleteImportStage,
) -> RunLease:
    channel_id = await persistence.ensure_channel(
        platform=prepared.channel.platform.value,
        external_id=prepared.channel.channel_id,
        display_name=prepared.channel.channel_name,
    )
    now = datetime.now(UTC)
    return await repository.claim_run(
        source_channel_id=channel_id,
        source_checksum=prepared.summary.source_checksum,
        source_size=prepared.summary.source.file_size,
        pipeline_version=PIPELINE_VERSION,
        owner_id=str(uuid4()),
        stage=stage,
        now=now,
        lease_duration=_LEASE_DURATION,
    )


async def _persist(
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
    persistence: SQLAlchemyIngestionPersistence,
    *,
    batch_size: int,
    lease: RunLease | None = None,
) -> RunLease:
    existing = await repository.existing_source_checksums(prepared.channel)
    selected = messages_to_process(prepared, existing)
    active = lease or await _claim(
        prepared,
        repository,
        persistence,
        CompleteImportStage.PERSISTENCE,
    )
    progress = TerminalProgress("persist", len(selected))

    async def checkpoint(counts: RunCounts) -> None:
        nonlocal active
        progress.update(counts.seen)
        active = await repository.checkpoint_run(
            active,
            stage=CompleteImportStage.PERSISTENCE,
            status=CompleteImportStatus.RUNNING,
            checkpoint={"messages": counts.seen},
            counts=asdict(counts),
            now=datetime.now(UTC),
            lease_duration=_LEASE_DURATION,
        )

    if selected:
        service = PersistHistoricalIngestion(
            store=persistence,
            batch_size=batch_size,
            progress=checkpoint,
        )
        await service(
            channel=prepared.channel,
            messages=selected,
            metadata=RunMetadata(
                parser_version=PARSER_VERSION,
                source_checksum=prepared.summary.source_checksum,
            ),
        )
    progress.finish()
    return await repository.checkpoint_run(
        active,
        stage=CompleteImportStage.PERSISTENCE,
        status=CompleteImportStatus.RUNNING,
        checkpoint={"messages": len(selected)},
        counts={"processed": len(selected)},
        now=datetime.now(UTC),
        lease_duration=_LEASE_DURATION,
    )


async def _geocode(  # noqa: PLR0913
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
    persistence: SQLAlchemyIngestionPersistence,
    database: DatabaseResources,
    settings: Settings,
    *,
    batch_size: int,
    max_provider_requests: int,
    lease: RunLease | None = None,
) -> RunLease:
    active = lease or await _claim(
        prepared,
        repository,
        persistence,
        CompleteImportStage.GEOCODE,
    )
    pending = await repository.pending_locations()
    progress = TerminalProgress("geocode", len(pending))
    if not pending:
        progress.finish()
        return await repository.checkpoint_run(
            active,
            stage=CompleteImportStage.GEOCODE,
            status=CompleteImportStatus.RUNNING,
            checkpoint={"locations": 0},
            counts={"remaining": 0},
            now=datetime.now(UTC),
            lease_duration=_LEASE_DURATION,
        )
    if settings.geoapify_api_key is None or not settings.geoapify_api_key.get_secret_value():
        message = "WEF_GEOAPIFY_API_KEY is required for the geocode stage"
        raise RuntimeError(message)
    underlying = HostedGeocoder(
        provider=GeocodeProvider.GEOAPIFY,
        transport=HTTPXJSONTransport(),
        policy=ProviderPolicy(
            requests_per_second=settings.geoapify_requests_per_second,
            quota=max_provider_requests,
            retries=0,
            timeout_seconds=15,
            identifying_user_agent="WEF historical importer/1.0",
        ),
        api_key=settings.geoapify_api_key.get_secret_value(),
    )
    budgeted = DurableBudgetedGeocoder(
        geocoder=underlying,
        budget=repository,
        run_id=active.run_id,
        account_identity=settings.geoapify_account_identity,
        daily_limit=settings.geoapify_daily_quota,
        minimum_interval=timedelta(
            seconds=float(Decimal(1) / settings.geoapify_requests_per_second),
        ),
        max_provider_requests=max_provider_requests,
        clock=lambda: datetime.now(UTC),
    )
    resolver = ResolveGeocode(SQLAlchemyGeocodeStore(database.session_factory), budgeted)
    processed = 0
    try:
        for item in pending:
            await resolver(
                source_query=item.address,
                district=item.district,
                location_id=item.location_id,
            )
            processed += 1
            progress.update(processed)
            if processed % batch_size == 0:
                active = await repository.checkpoint_run(
                    active,
                    stage=CompleteImportStage.GEOCODE,
                    status=CompleteImportStatus.RUNNING,
                    checkpoint={"locations": processed},
                    counts={"remaining": len(pending) - processed},
                    now=datetime.now(UTC),
                    lease_duration=_LEASE_DURATION,
                )
    except ProviderBatchLimitError:
        active = await _pause(
            repository,
            active,
            CompleteImportStage.GEOCODE,
            "operator_batch_limit",
            processed,
            datetime.now(UTC),
        )
    except ProviderDailyBudgetError:
        active = await _pause(
            repository,
            active,
            CompleteImportStage.GEOCODE,
            "daily_provider_budget",
            processed,
            _next_utc_day(),
        )
    except ProviderPauseError:
        active = await _pause(
            repository,
            active,
            CompleteImportStage.GEOCODE,
            "provider_transient",
            processed,
            datetime.now(UTC) + timedelta(minutes=15),
        )
    progress.finish(complete=active.status is not CompleteImportStatus.PAUSED)
    if active.status is CompleteImportStatus.PAUSED:
        return active
    return await repository.checkpoint_run(
        active,
        stage=CompleteImportStage.GEOCODE,
        status=CompleteImportStatus.RUNNING,
        checkpoint={"locations": processed},
        counts={"remaining": len(pending) - processed},
        now=datetime.now(UTC),
        lease_duration=_LEASE_DURATION,
    )


async def _pause(  # noqa: PLR0913, PLR0917
    repository: SQLAlchemyCompleteImportRepository,
    lease: RunLease,
    stage: CompleteImportStage,
    reason: str,
    processed: int,
    next_eligible_at: datetime,
) -> RunLease:
    return await repository.checkpoint_run(
        lease,
        stage=stage,
        status=CompleteImportStatus.PAUSED,
        checkpoint={stage.value: processed},
        counts={"processed": processed},
        now=datetime.now(UTC),
        lease_duration=_LEASE_DURATION,
        pause_reason=reason,
        next_eligible_at=next_eligible_at,
    )


async def _media(  # noqa: PLR0913
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
    persistence: SQLAlchemyIngestionPersistence,
    database: DatabaseResources,
    settings: Settings,
    *,
    batch_size: int,
    lease: RunLease | None = None,
) -> RunLease:
    active = lease or await _claim(
        prepared,
        repository,
        persistence,
        CompleteImportStage.MEDIA,
    )
    anchors = await repository.source_anchors(prepared.channel)
    replayed = await repository.existing_media_replays(prepared.channel)
    work: list[MediaWorkItem] = []
    for disposition in prepared.media_dispositions:
        reference = disposition.reference
        source = anchors.get(reference.source_message_id)
        if source is None:
            continue
        replay_key = (
            source.source_message_id,
            reference.media_index,
            source.revision_id,
            descriptor_identity(reference.descriptor),
            GROUPING_VERSION,
        )
        if replay_key in replayed:
            continue
        association = disposition.association
        listing_anchor = (
            anchors.get(association.listing_message_id) if association is not None else None
        )
        offer_id = listing_anchor.offer_id if listing_anchor is not None else None
        work.append(
            MediaWorkItem(
                source_message_id=source.source_message_id,
                source_message_revision_id=source.revision_id,
                source_ordinal=reference.media_index,
                descriptor=reference.descriptor,
                association_version=GROUPING_VERSION,
                offer_id=offer_id,
                association_rule=association.rule if offer_id is not None and association else None,
                association_confidence=(
                    confidence_score(association.confidence)
                    if offer_id is not None and association is not None
                    else None
                ),
            ),
        )
    progress = TerminalProgress("media", len(work))
    processor = ProcessMedia(
        filesystem=LocalMediaStorage(
            source_root=settings.source_path,
            originals_root=settings.restricted_originals_path,
            derivatives_root=settings.public_derivatives_path,
            limits=MediaLimits(
                max_bytes=settings.media_max_bytes,
                max_pixels=settings.media_max_pixels,
            ),
        ),
        repository=SQLAlchemyMediaRepository(database.session_factory),
        persistence_lock=asyncio.Lock(),
    )
    concurrency = min(_MEDIA_CONCURRENCY, batch_size)
    processed = 0
    while processed < len(work):
        batch = work[processed : processed + concurrency]
        await asyncio.gather(*(processor(item) for item in batch))
        processed += len(batch)
        progress.update(processed)
        if processed % batch_size == 0:
            active = await repository.checkpoint_run(
                active,
                stage=CompleteImportStage.MEDIA,
                status=CompleteImportStatus.RUNNING,
                checkpoint={"media": processed},
                counts={"remaining": len(work) - processed},
                now=datetime.now(UTC),
                lease_duration=_LEASE_DURATION,
            )
    progress.finish()
    return await repository.checkpoint_run(
        active,
        stage=CompleteImportStage.MEDIA,
        status=CompleteImportStatus.RUNNING,
        checkpoint={"media": len(work)},
        counts={"remaining": 0},
        now=datetime.now(UTC),
        lease_duration=_LEASE_DURATION,
    )


async def _verify(
    prepared: PreparedImport,
    repository: SQLAlchemyCompleteImportRepository,
    persistence: SQLAlchemyIngestionPersistence,
    *,
    lease: RunLease | None = None,
) -> tuple[RunLease, Mapping[str, object]]:
    active = lease or await _claim(
        prepared,
        repository,
        persistence,
        CompleteImportStage.VERIFY,
    )
    existing = await repository.existing_source_checksums(prepared.channel)
    plan = build_incremental_plan(prepared, existing)
    verification = await repository.verify(prepared.channel, active.run_id)
    if plan.messages_to_process:
        message = "verification found unpersisted source messages"
        raise RuntimeError(message)
    counts = asdict(verification)
    active = await repository.checkpoint_run(
        active,
        stage=CompleteImportStage.VERIFY,
        status=CompleteImportStatus.SUCCEEDED,
        checkpoint={"verified": True},
        counts=counts,
        now=datetime.now(UTC),
        lease_duration=_LEASE_DURATION,
    )
    return active, counts


async def run_import(args: argparse.Namespace, settings: Settings) -> dict[str, object]:
    """Execute one explicit stage or the full resumable sequence."""
    prepared = await asyncio.to_thread(_prepare, settings)
    database = create_database_resources(settings.database_url)
    repository = SQLAlchemyCompleteImportRepository(database.session_factory)
    contact_cipher = AesGcmContactCipher(
        encryption_key=decode_secret_key(
            settings.contact_encryption_key.get_secret_value()
            if settings.contact_encryption_key is not None
            else None,
        ),
        hmac_key=decode_secret_key(
            settings.contact_hmac_key.get_secret_value()
            if settings.contact_hmac_key is not None
            else None,
        ),
    )
    persistence = SQLAlchemyIngestionPersistence(
        database.session_factory,
        contact_cipher=contact_cipher,
    )
    try:
        if args.command == "dry-run":
            return await _dry_run(prepared, repository)
        lease: RunLease | None = None
        if args.command in {"persist", "run"}:
            lease = await _persist(
                prepared,
                repository,
                persistence,
                batch_size=args.batch_size,
                lease=lease,
            )
            if args.command == "persist":
                lease = await repository.release_run(lease, now=datetime.now(UTC))
                return {"run_id": str(lease.run_id), "stage": "persistence", "status": "ok"}
        if args.command in {"geocode", "run"}:
            lease = await _geocode(
                prepared,
                repository,
                persistence,
                database,
                settings,
                batch_size=args.geocode_batch_size,
                max_provider_requests=args.max_provider_requests,
                lease=lease,
            )
            if args.command == "geocode":
                paused = lease.status is CompleteImportStatus.PAUSED
                if not paused:
                    lease = await repository.release_run(lease, now=datetime.now(UTC))
                return {
                    "run_id": str(lease.run_id),
                    "stage": "geocode",
                    "status": "paused" if paused else "ok",
                }
            if lease.status is CompleteImportStatus.PAUSED:
                return {
                    "run_id": str(lease.run_id),
                    "stage": "geocode",
                    "status": lease.status.value,
                }
        if args.command in {"media", "run"}:
            lease = await _media(
                prepared,
                repository,
                persistence,
                database,
                settings,
                batch_size=args.batch_size,
                lease=lease,
            )
            if args.command == "media":
                lease = await repository.release_run(lease, now=datetime.now(UTC))
                return {"run_id": str(lease.run_id), "stage": "media", "status": "ok"}
        lease, counts = await _verify(
            prepared,
            repository,
            persistence,
            lease=lease,
        )
        return {
            "counts": counts,
            "run_id": str(lease.run_id),
            "stage": "verify",
            "status": lease.status.value,
        }
    finally:
        await database.engine.dispose()


def _next_utc_day() -> datetime:
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=UTC)


def main() -> None:
    """Parse explicit operator arguments and emit one safe JSON summary."""
    args = _parser().parse_args()
    try:
        result = asyncio.run(run_import(args, load_settings()))
    except (CompleteImportLeaseHeldError, UnsafeSourceMountError, RuntimeError) as error:
        sys.stderr.write(f"import failed: {type(error).__name__}\n")
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        sys.stderr.write("import interrupted; resume after the five-minute lease expires\n")
        raise SystemExit(130) from None
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
