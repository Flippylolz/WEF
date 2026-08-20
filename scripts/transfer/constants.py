"""Shared constants for historical transfer bundles."""

from __future__ import annotations

BUNDLE_SCHEMA = "wef-historical-bundle@1"
MIGRATION_HEAD = "20260815_0008"
PIPELINE_ID = "e3-complete-v2"

INCLUDED_TABLES: tuple[str, ...] = (
    "locations",
    "offers",
    "source_channels",
    "source_messages",
    "source_message_revisions",
    "developments",
    "offer_sources",
    "ingest_runs",
    "complete_import_runs",
    "provider_daily_budgets",
    "provider_attempts",
    "geocode_results",
    "geocode_miss_claims",
    "location_geocode_selections",
    "stored_media_objects",
    "media_assets",
    "media_disposition_attempts",
    "media_derivatives",
    "media_derivative_attempts",
    "offer_media",
)

EXCLUDED_TABLES: tuple[str, ...] = (
    "users",
    "auth_sessions",
    "e0_proof_estates",
    "alembic_version",
)

FORBIDDEN_BUNDLE_PATH_FRAGMENTS: tuple[str, ...] = (
    ".env",
    "credentials",
    "private-keys",
    "telegram-session",
    "raw-export",
    "source-reports",
)

HEADROOM_MULTIPLIER = 1.25
