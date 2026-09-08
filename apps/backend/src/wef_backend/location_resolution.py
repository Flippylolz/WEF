"""Composition of municipal, budgeted hosted, and source-only AI lookup stages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from wef_backend.features.admin.application.provider_budget import BudgetedProvider
from wef_backend.features.admin.infrastructure.address_recovery import (
    AddressRecoveryGeocoder,
    CachedAddressRecovery,
)
from wef_backend.features.admin.infrastructure.groq_provider import GroqChatCompletionsAdapter
from wef_backend.features.admin.infrastructure.provider_budget_store import SQLAlchemyProviderBudget
from wef_backend.features.identity.infrastructure.security import SystemClock
from wef_backend.features.ingestion.application.geocoding import ResolveGeocode
from wef_backend.features.ingestion.application.location_resolution import ResolveLocation
from wef_backend.features.ingestion.infrastructure.geocode_store import SQLAlchemyGeocodeStore
from wef_backend.features.ingestion.infrastructure.municipal_geocoder import (
    MunicipalGeocoder,
    MunicipalHTTP,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.geocoding import GeocoderPort
    from wef_backend.settings import Settings


def build_location_resolver(
    sessions: async_sessionmaker[AsyncSession], hosted: GeocoderPort, settings: Settings
) -> ResolveLocation:
    """Keep all provider clients and budgets outside inward orchestration."""
    store = SQLAlchemyGeocodeStore(sessions)
    municipal = ResolveGeocode(
        store,
        MunicipalGeocoder(sessions, MunicipalHTTP()),
        lease_duration=timedelta(seconds=120),
        request_version="municipal-v2-" + datetime.now(UTC).strftime("%G-W%V"),
        fallback_forms=False,
    )
    recovery = None
    key = settings.groq_api_key
    owner = settings.ai_recovery_owner_id
    if (
        settings.ai_curation_enabled
        and settings.ai_recovery_enabled
        and settings.ai_recovery_activation_verified
        and settings.groq_zdr_verified
        and settings.groq_model == "openai/gpt-oss-20b"
        and key
        and isinstance(owner, UUID)
    ):
        provider = BudgetedProvider(
            GroqChatCompletionsAdapter(key.get_secret_value(), timeout_seconds=30),
            SQLAlchemyProviderBudget(sessions),
            SystemClock(),
        )
        recovery = CachedAddressRecovery(
            ResolveGeocode(
                store,
                AddressRecoveryGeocoder(provider, sessions, owner),
                lease_duration=timedelta(seconds=120),
                fallback_forms=False,
            )
        )
    return ResolveLocation(municipal, ResolveGeocode(store, hosted), store, recovery)
