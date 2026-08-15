"""Unit tests for incremental preparation, provider budgets, and progress."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

from wef_backend.features.ingestion.application import ChannelExpectation
from wef_backend.features.ingestion.application.complete_import import (
    DurableBudgetedGeocoder,
    PreparedImport,
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderReservation,
    build_incremental_plan,
    messages_to_process,
    prepare_import,
)
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.infrastructure import TelegramDesktopExportAdapter
from wef_backend.import_command import TerminalProgress, _dry_run, _positive_int

if TYPE_CHECKING:
    from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
        SQLAlchemyCompleteImportRepository,
    )

FIXTURE = Path(__file__).parent / "fixtures/telegram_export/sanitized-complete.json"
EXPECTATION = ChannelExpectation("9001", "public_channel", "Sanitized Fixture Channel")
NOW = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)


def _prepared() -> PreparedImport:
    return prepare_import(TelegramDesktopExportAdapter(FIXTURE, EXPECTATION))


def test_incremental_plan_counts_only_unseen_or_changed_messages() -> None:
    """A later dump skips unchanged identities while retaining changed revisions."""
    prepared = _prepared()
    first, second = prepared.messages[:2]
    existing = {
        first.raw.external_message_id: first.raw.checksum,
        second.raw.external_message_id: "f" * 64,
    }

    plan = build_incremental_plan(prepared, existing)
    selected = messages_to_process(prepared, existing)

    assert plan.records_total == 8
    assert plan.unchanged_messages == 1
    assert plan.changed_messages == 1
    assert plan.new_messages == len(prepared.messages) - 2
    assert plan.messages_to_process == len(selected)
    assert first not in selected
    assert second in selected
    assert plan.media_total == len(prepared.media_dispositions)


def test_progress_bar_reports_counts_and_completion() -> None:
    """Interactive and redirected operators receive a bounded visible bar."""
    output = StringIO()
    progress = TerminalProgress("persist", 10, output=output)

    progress.update(1)
    progress.update(5)
    progress.finish()

    rendered = output.getvalue()
    assert "persist" in rendered
    assert "1/10" in rendered
    assert "100.0%" in rendered


@dataclass
class FakeDryRunRepository:
    """Provide only the read models used by the exact incremental preview."""

    existing: dict[int, str]

    async def existing_source_checksums(self, _channel: object) -> dict[int, str]:
        """Return durable message identities and revision checksums."""
        return self.existing

    async def source_anchors(self, _channel: object) -> dict[int, object]:
        """Treat media as new when no source rows have been persisted."""
        return {}

    async def existing_media_replays(self, _channel: object) -> set[object]:
        """Return no completed media replay keys."""
        return set()

    async def pending_locations(self) -> list[object]:
        """Expose one existing unresolved location in the preview."""
        return [object()]


async def test_dry_run_reports_exact_incremental_work_without_writes() -> None:
    """The preview separates new/changed work from unchanged stored messages."""
    prepared = _prepared()
    first = prepared.messages[0]
    repository = FakeDryRunRepository(
        {first.raw.external_message_id: first.raw.checksum},
    )

    result = await _dry_run(
        prepared,
        cast("SQLAlchemyCompleteImportRepository", repository),
    )

    assert result["status"] == "dry_run"
    assert result["new_messages"] == 7
    assert result["unchanged_messages"] == 1
    assert result["messages_to_process"] == 7
    assert result["media_to_process"] == 3
    assert result["locations_currently_pending"] == 1


def test_positive_batch_size_rejects_zero() -> None:
    """Operator batch controls never accept a non-progressing batch."""
    assert _positive_int("25") == 25
    with pytest.raises(argparse.ArgumentTypeError, match="positive"):
        _positive_int("0")


@dataclass
class FakeBudget:
    """Script durable reservations and retain sanitized completion evidence."""

    reservations: list[ProviderReservation | None]
    completions: list[tuple[str, str | None]] = field(default_factory=list)

    async def reserve_provider_attempt(self, **_: object) -> ProviderReservation | None:
        """Return the next scripted durable slot."""
        return self.reservations.pop(0)

    async def complete_provider_attempt(
        self,
        _attempt_id: object,
        *,
        status: str,
        error_code: str | None,
        completed_at: datetime,
    ) -> None:
        """Record only safe status/error values."""
        del completed_at
        self.completions.append((status, error_code))


@dataclass
class FakeGeocoder:
    """Return one neutral provider result and count actual hosted calls."""

    result: GeocodeResult
    provider: GeocodeProvider = GeocodeProvider.GEOAPIFY
    calls: int = 0

    async def geocode(self, _query: object) -> GeocodeResult:
        """Return the scripted result."""
        self.calls += 1
        return self.result


def _result(error: GeocodeErrorCode | None = None) -> GeocodeResult:
    return GeocodeResult(
        provider=GeocodeProvider.GEOAPIFY,
        provider_result_id="fixture" if error is None else None,
        longitude=Decimal("21.0") if error is None else None,
        latitude=Decimal("52.2") if error is None else None,
        display_name="Warszawa" if error is None else None,
        precision=GeocodePrecision.BUILDING if error is None else GeocodePrecision.UNKNOWN,
        confidence=Decimal("0.9") if error is None else Decimal(0),
        within_scope=True if error is None else None,
        attribution_text="fixture attribution",
        error_code=error,
    )


async def test_budgeted_geocoder_reserves_before_call_and_enforces_local_cap() -> None:
    """Every call consumes one durable slot and the local cap causes a pause."""
    budget = FakeBudget([ProviderReservation(uuid4(), NOW)])
    hosted = FakeGeocoder(_result())
    geocoder = DurableBudgetedGeocoder(
        geocoder=hosted,
        budget=budget,
        run_id=uuid4(),
        account_identity="test-account",
        daily_limit=2_700,
        minimum_interval=timedelta(milliseconds=250),
        max_provider_requests=1,
        clock=lambda: NOW,
    )
    query = normalize_geocode_query("ul. Testowa 1, Warszawa")

    assert await geocoder.geocode(query) == hosted.result
    with pytest.raises(ProviderBatchLimitError):
        await geocoder.geocode(query)

    assert hosted.calls == 1
    assert budget.completions == [("succeeded", None)]


async def test_budgeted_geocoder_pauses_without_network_when_daily_budget_is_full() -> None:
    """No hosted request occurs after the durable daily safety cap."""
    budget = FakeBudget([None])
    hosted = FakeGeocoder(_result())
    geocoder = DurableBudgetedGeocoder(
        geocoder=hosted,
        budget=budget,
        run_id=uuid4(),
        account_identity="test-account",
        daily_limit=1,
        minimum_interval=timedelta(milliseconds=250),
        max_provider_requests=1,
        clock=lambda: NOW,
    )

    with pytest.raises(ProviderDailyBudgetError):
        await geocoder.geocode(normalize_geocode_query("Warszawa"))

    assert hosted.calls == 0
