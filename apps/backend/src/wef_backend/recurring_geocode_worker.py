"""Background recurring geocoding for live-ingested ungeocoded locations."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: TC002

from wef_backend.features.catalog.infrastructure.promote_public_catalog_adapter import (
    SQLAlchemyPromotePublicCatalogAdapter,
)
from wef_backend.features.ingestion.application.accept_pending_geocode_pins import (
    AcceptPendingGeocodePins,
)
from wef_backend.features.ingestion.application.complete_import import (
    PIPELINE_VERSION,
    DurableBudgetedGeocoder,
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.application.recurring_geocode import (
    RecurringDeferAction,
    build_recurring_monitor_event,
    classify_recurring_budget_error,
)
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category
from wef_backend.features.ingestion.infrastructure import HostedGeocoder, HTTPXJSONTransport
from wef_backend.features.ingestion.infrastructure.accept_pending_geocode_pins_adapter import (
    SQLAlchemyAcceptPendingGeocodePinsAdapter,
)
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    SQLAlchemyCompleteImportRepository,
)
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.geocoder_adapters import ProviderPolicy
from wef_backend.settings import Settings  # noqa: TC001

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity

logger = structlog.get_logger("wef.recurring_geocode")

_TRANSIENT_DEFER = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class RecurringGeocodeCycleResult:
    """Redacted outcome for one background geocode cycle."""

    processed: int
    pending: int
    skipped: bool
    defer_action: RecurringDeferAction | None
    locations_accepted: int = 0
    offers_promoted: int = 0


@dataclass(slots=True)
class RecurringGeocodeWorker:
    """Resolve pending live locations under the recurring Geoapify budget."""

    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    channel: TelegramChannelIdentity
    _defer_until: datetime | None = None

    async def process_once(self) -> RecurringGeocodeCycleResult:
        """Geocode up to one batch of pending locations, deferring on budget errors."""
        now = datetime.now(UTC)
        if self._defer_until is not None and now < self._defer_until:
            return RecurringGeocodeCycleResult(
                processed=0,
                pending=0,
                skipped=True,
                defer_action=None,
            )

        api_key = self.settings.geoapify_api_key
        if api_key is None or not api_key.get_secret_value():
            return RecurringGeocodeCycleResult(
                processed=0,
                pending=0,
                skipped=True,
                defer_action=None,
            )

        repository = SQLAlchemyCompleteImportRepository(self.session_factory)
        channel_id = await repository.resolve_source_channel_id(
            source_identity_from_channel(self.channel),
        )
        if channel_id is None:
            return RecurringGeocodeCycleResult(
                processed=0,
                pending=0,
                skipped=True,
                defer_action=None,
            )

        pending = await repository.pending_locations()
        batch = pending[: self.settings.telegram_recurring_geocode_batch_size]
        if not batch:
            return RecurringGeocodeCycleResult(
                processed=0,
                pending=0,
                skipped=False,
                defer_action=None,
            )

        run_id = await repository.recurring_geocode_run_id(
            source_channel_id=channel_id,
            pipeline_version=PIPELINE_VERSION,
            now=now,
        )
        underlying = HostedGeocoder(
            provider=GeocodeProvider.GEOAPIFY,
            transport=HTTPXJSONTransport(),
            policy=ProviderPolicy(
                requests_per_second=self.settings.geoapify_requests_per_second,
                quota=self.settings.telegram_recurring_geocode_batch_size,
                retries=0,
                timeout_seconds=15,
                identifying_user_agent="WEF recurring geocoder/1.0",
            ),
            api_key=api_key.get_secret_value(),
        )
        budgeted = DurableBudgetedGeocoder(
            geocoder=underlying,
            budget=repository,
            run_id=run_id,
            account_identity=self.settings.geoapify_account_identity,
            daily_limit=self.settings.geoapify_daily_quota,
            minimum_interval=timedelta(
                seconds=float(Decimal(1) / self.settings.geoapify_requests_per_second),
            ),
            max_provider_requests=self.settings.telegram_recurring_geocode_batch_size,
            clock=lambda: datetime.now(UTC),
        )
        resolver = ResolveGeocode(
            SQLAlchemyGeocodeStore(self.session_factory),
            budgeted,
        )

        processed = 0
        defer_action: RecurringDeferAction | None = None
        try:
            for item in batch:
                await resolver(
                    source_query=item.address,
                    district=item.district,
                    location_id=item.location_id,
                )
                processed += 1
        except (ProviderDailyBudgetError, ProviderBatchLimitError, ProviderPauseError) as error:
            defer_action = classify_recurring_budget_error(error)
            self._apply_defer(defer_action, now=datetime.now(UTC))
            monitor = build_recurring_monitor_event(
                provider=GeocodeProvider.GEOAPIFY,
                disposition=defer_action,
                error_code=None,
                account_identity=self.settings.geoapify_account_identity,
            )
            fields = monitor.as_log_fields()
            logger.info(fields.pop("event"), **fields)

        if processed:
            logger.info(
                "recurring_geocode_cycle",
                processed=processed,
                pending=max(len(pending) - processed, 0),
            )
            locations_accepted, offers_promoted = await self._refresh_live_catalog()
        else:
            locations_accepted = 0
            offers_promoted = 0

        return RecurringGeocodeCycleResult(
            processed=processed,
            pending=len(pending) - processed,
            skipped=False,
            defer_action=defer_action,
            locations_accepted=locations_accepted,
            offers_promoted=offers_promoted,
        )

    async def _refresh_live_catalog(self) -> tuple[int, int]:
        """Accept in-scope pending pins and publish offers tied to map-ready locations."""
        pins = await AcceptPendingGeocodePins(
            SQLAlchemyAcceptPendingGeocodePinsAdapter(self.session_factory),
        )()
        promoted = await SQLAlchemyPromotePublicCatalogAdapter(
            self.session_factory,
        ).promote_map_ready_offers()
        if pins.locations_accepted or promoted:
            logger.info(
                "recurring_catalog_refresh",
                locations_accepted=pins.locations_accepted,
                offers_promoted=promoted,
            )
        return pins.locations_accepted, promoted

    def _apply_defer(self, action: RecurringDeferAction, *, now: datetime) -> None:
        if action is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY:
            day = now.astimezone(UTC).date()
            self._defer_until = datetime.combine(
                day + timedelta(days=1),
                datetime.min.time(),
                tzinfo=UTC,
            )
        elif action is RecurringDeferAction.DEFER_TRANSIENT:
            self._defer_until = now + _TRANSIENT_DEFER


async def maintain_recurring_geocode(
    worker: RecurringGeocodeWorker,
    *,
    stop: asyncio.Event,
    interval: float,
) -> None:
    """Repeat bounded geocode cycles until the worker stops."""
    while not stop.is_set():
        with suppress(asyncio.CancelledError):
            try:
                await worker.process_once()
            except Exception as error:  # noqa: BLE001
                logger.error(  # noqa: TRY400
                    "recurring_geocode_cycle_failed",
                    category=safe_error_category(error),
                )
        await asyncio.sleep(interval)


__all__ = [
    "RecurringGeocodeCycleResult",
    "RecurringGeocodeWorker",
    "maintain_recurring_geocode",
]
