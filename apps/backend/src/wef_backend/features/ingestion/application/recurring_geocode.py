"""Worker-shaped defer/monitoring contract for recurring geocoding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.complete_import import (
    ProviderBatchLimitError,
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.domain.geocoding import GeocodeErrorCode, GeocodeProvider
from wef_backend.features.ingestion.domain.recurring_geocoder import (
    RecurringGeocoderDecision,
    assert_provider_allowed_for_recurring,
    default_recurring_geocoder_decision,
)

if TYPE_CHECKING:
    from datetime import date


class RecurringDeferAction(StrEnum):
    """How the always-on worker should treat one provider outcome."""

    CONTINUE = "continue"
    DEFER_UNTIL_NEXT_UTC_DAY = "defer_until_next_utc_day"
    DEFER_TRANSIENT = "defer_transient"
    LEAVE_UNGEOCODED = "leave_ungeocoded"


@dataclass(frozen=True, slots=True)
class RecurringGeocodeMonitorEvent:
    """Redacted structured event for quota/rate/error/defer observability."""

    event: str
    provider: str
    disposition: str
    error_code: str | None
    account_identity: str

    def as_log_fields(self) -> dict[str, str | None]:
        """Return a JSON-friendly payload with no secret material."""
        return asdict(self)


def classify_recurring_provider_outcome(
    error_code: GeocodeErrorCode | None,
) -> RecurringDeferAction:
    """Map provider-neutral error codes to worker defer behavior."""
    if error_code is None or error_code is GeocodeErrorCode.NO_RESULT:
        return RecurringDeferAction.CONTINUE
    if error_code is GeocodeErrorCode.QUOTA:
        return RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY
    if error_code in {
        GeocodeErrorCode.TRANSIENT,
        GeocodeErrorCode.TIMEOUT,
        GeocodeErrorCode.INVALID_RESPONSE,
    }:
        return RecurringDeferAction.DEFER_TRANSIENT
    return RecurringDeferAction.LEAVE_UNGEOCODED


def classify_recurring_budget_error(error: BaseException) -> RecurringDeferAction:
    """Map durable budget/pause exceptions to the same defer vocabulary."""
    if isinstance(error, ProviderDailyBudgetError):
        return RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY
    if isinstance(error, ProviderBatchLimitError):
        return RecurringDeferAction.DEFER_TRANSIENT
    if isinstance(error, ProviderPauseError):
        return RecurringDeferAction.DEFER_TRANSIENT
    message = "unsupported recurring geocode budget error"
    raise TypeError(message)


def build_recurring_monitor_event(
    *,
    provider: GeocodeProvider,
    disposition: RecurringDeferAction,
    error_code: GeocodeErrorCode | None,
    account_identity: str,
) -> RecurringGeocodeMonitorEvent:
    """Build one redacted monitor event for logs or future E8-T5 alerts."""
    assert_provider_allowed_for_recurring(provider)
    return RecurringGeocodeMonitorEvent(
        event="recurring_geocode_outcome",
        provider=provider.value,
        disposition=disposition.value,
        error_code=error_code.value if error_code is not None else None,
        account_identity=account_identity,
    )


def revalidation_report(
    *,
    checked_on: date | None = None,
    live_check: dict[str, object] | None = None,
) -> dict[str, object]:
    """Serialize the dated retain decision and optional live readiness proof."""
    decision = default_recurring_geocoder_decision(checked_on=checked_on)
    assert_provider_allowed_for_recurring(decision.retained_provider)
    payload: dict[str, object] = {
        "decision": _decision_payload(decision),
        "defer_policy": {
            "quota": RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY.value,
            "transient": RecurringDeferAction.DEFER_TRANSIENT.value,
            "no_result": RecurringDeferAction.CONTINUE.value,
            "provider_fan_out": False,
            "public_nominatim_fallback": False,
        },
        "live_check": live_check,
        "status": "revalidated_retain_geoapify",
    }
    return payload


def _decision_payload(decision: RecurringGeocoderDecision) -> dict[str, object]:
    return {
        "attribution_required": decision.attribution_required,
        "checked_on": decision.checked_on.isoformat(),
        "daily_credit_limit": decision.daily_credit_limit,
        "evidence_notes": list(decision.evidence_notes),
        "paid_plan_required": decision.paid_plan_required,
        "public_nominatim_for_recurring": decision.public_nominatim_for_recurring,
        "requests_per_second": str(decision.requests_per_second),
        "retained_provider": decision.retained_provider.value,
    }
