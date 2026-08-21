"""Recurring-ingestion geocoder selection and Nominatim exclusion policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider


class RecurringProviderForbiddenError(ValueError):
    """Raised when a provider is not allowed for always-on live ingestion."""


@dataclass(frozen=True, slots=True)
class RecurringGeocoderDecision:
    """Dated retain/migrate decision for always-on geocoding (D-002 / E8-T4)."""

    retained_provider: GeocodeProvider
    checked_on: date
    daily_credit_limit: int
    requests_per_second: Decimal
    attribution_required: bool
    public_nominatim_for_recurring: bool
    paid_plan_required: bool
    evidence_notes: tuple[str, ...]


def default_recurring_geocoder_decision(
    *,
    checked_on: date | None = None,
) -> RecurringGeocoderDecision:
    """Return the E8-T4 retain-Geoapify decision under free-plan soft limits."""
    return RecurringGeocoderDecision(
        retained_provider=GeocodeProvider.GEOAPIFY,
        checked_on=checked_on or date(2026, 8, 21),
        # Soft under Geoapify free 3000 credits/day; matches WEF_GEOAPIFY_DAILY_QUOTA default.
        daily_credit_limit=2_700,
        requests_per_second=Decimal(4),
        attribution_required=True,
        public_nominatim_for_recurring=False,
        paid_plan_required=False,
        evidence_notes=(
            (
                "Geoapify free: 3000 credits/day, <=5 rps, commercial OK with attribution "
                "(https://www.geoapify.com/pricing/ checked 2026-08-21)"
            ),
            "Live volume is cache-first and few new/changed posts/day; free quota fits",
            "Public Nominatim remains ineligible for recurring jobs",
            "Quota/rate exhaustion defers work; no provider fan-out fallback",
        ),
    )


def assert_provider_allowed_for_recurring(provider: GeocodeProvider) -> None:
    """Forbid public Nominatim and unselected providers for the live worker path."""
    if provider in {GeocodeProvider.GEOAPIFY, GeocodeProvider.FIXTURE}:
        return
    if provider is GeocodeProvider.NOMINATIM:
        message = "public Nominatim is not allowed for recurring ingestion"
        raise RecurringProviderForbiddenError(message)
    message = (
        "LocationIQ is not selected for recurring ingestion"
        if provider is GeocodeProvider.LOCATIONIQ
        else f"provider {provider.value!r} is not allowed for recurring ingestion"
    )
    raise RecurringProviderForbiddenError(message)
