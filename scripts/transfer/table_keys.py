"""Primary-key metadata for historical restore tables."""

from __future__ import annotations

from scripts.transfer.constants import INCLUDED_TABLES

TABLE_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "locations": ("id",),
    "offers": ("id",),
    "source_channels": ("id",),
    "source_messages": ("id",),
    "source_message_revisions": ("id",),
    "developments": ("id",),
    "offer_sources": ("id",),
    "ingest_runs": ("id",),
    "complete_import_runs": ("id",),
    "provider_daily_budgets": ("provider", "budget_date", "account_identity"),
    "provider_attempts": ("id",),
    "geocode_results": ("id",),
    "geocode_miss_claims": ("query_hash",),
    "location_geocode_selections": ("id",),
    "stored_media_objects": ("id",),
    "media_assets": ("id",),
    "media_disposition_attempts": ("id",),
    "media_derivatives": ("id",),
    "media_derivative_attempts": ("id",),
    "offer_media": ("offer_id", "media_asset_id"),
}

for table in INCLUDED_TABLES:
    if table not in TABLE_PRIMARY_KEYS:
        msg = f"missing primary-key metadata for restore table: {table}"
        raise RuntimeError(msg)
