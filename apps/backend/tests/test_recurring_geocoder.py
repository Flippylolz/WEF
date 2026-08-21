"""Tests for recurring geocoder revalidation and defer classification."""

from __future__ import annotations

import pytest

from wef_backend.features.ingestion.application.complete_import import (
    ProviderDailyBudgetError,
    ProviderPauseError,
)
from wef_backend.features.ingestion.application.recurring_geocode import (
    RecurringDeferAction,
    build_recurring_monitor_event,
    classify_recurring_budget_error,
    classify_recurring_provider_outcome,
    revalidation_report,
)
from wef_backend.features.ingestion.domain.geocoding import GeocodeErrorCode, GeocodeProvider
from wef_backend.features.ingestion.domain.recurring_geocoder import (
    RecurringProviderForbiddenError,
    assert_provider_allowed_for_recurring,
    default_recurring_geocoder_decision,
)


def test_default_decision_retains_geoapify_and_forbids_nominatim() -> None:
    decision = default_recurring_geocoder_decision()
    assert decision.retained_provider is GeocodeProvider.GEOAPIFY
    assert decision.public_nominatim_for_recurring is False
    assert decision.attribution_required is True
    assert decision.daily_credit_limit == 2_700
    assert_provider_allowed_for_recurring(GeocodeProvider.GEOAPIFY)
    with pytest.raises(RecurringProviderForbiddenError):
        assert_provider_allowed_for_recurring(GeocodeProvider.NOMINATIM)
    with pytest.raises(RecurringProviderForbiddenError):
        assert_provider_allowed_for_recurring(GeocodeProvider.LOCATIONIQ)


def test_classify_quota_and_transient_defer() -> None:
    assert (
        classify_recurring_provider_outcome(GeocodeErrorCode.QUOTA)
        is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY
    )
    assert (
        classify_recurring_provider_outcome(GeocodeErrorCode.TRANSIENT)
        is RecurringDeferAction.DEFER_TRANSIENT
    )
    assert classify_recurring_provider_outcome(None) is RecurringDeferAction.CONTINUE
    assert (
        classify_recurring_budget_error(ProviderDailyBudgetError())
        is RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY
    )
    assert (
        classify_recurring_budget_error(ProviderPauseError())
        is RecurringDeferAction.DEFER_TRANSIENT
    )


def test_monitor_event_is_redacted_and_blocks_nominatim() -> None:
    event = build_recurring_monitor_event(
        provider=GeocodeProvider.GEOAPIFY,
        disposition=RecurringDeferAction.DEFER_UNTIL_NEXT_UTC_DAY,
        error_code=GeocodeErrorCode.QUOTA,
        account_identity="default",
    )
    fields = event.as_log_fields()
    assert fields["event"] == "recurring_geocode_outcome"
    assert fields["disposition"] == "defer_until_next_utc_day"
    assert "api_key" not in fields
    with pytest.raises(RecurringProviderForbiddenError):
        build_recurring_monitor_event(
            provider=GeocodeProvider.NOMINATIM,
            disposition=RecurringDeferAction.CONTINUE,
            error_code=None,
            account_identity="default",
        )


def test_revalidation_report_status() -> None:
    report = revalidation_report()
    assert report["status"] == "revalidated_retain_geoapify"
    decision = report["decision"]
    assert isinstance(decision, dict)
    assert decision["retained_provider"] == "geoapify"
    assert decision["public_nominatim_for_recurring"] is False
    defer = report["defer_policy"]
    assert isinstance(defer, dict)
    assert defer["provider_fan_out"] is False
    assert defer["public_nominatim_fallback"] is False
