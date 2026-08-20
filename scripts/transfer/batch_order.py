"""FK-safe insert ordering for historical bundle tables."""

from __future__ import annotations

from scripts.transfer.constants import INCLUDED_TABLES

TABLE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "source_messages": ("source_channels",),
    "source_message_revisions": ("source_messages",),
    "developments": ("source_channels",),
    "offer_sources": ("offers", "source_messages"),
    "offers": ("locations", "developments"),
    "provider_attempts": ("provider_daily_budgets",),
    "geocode_miss_claims": ("geocode_results",),
    "location_geocode_selections": ("locations", "geocode_results"),
    "media_assets": ("stored_media_objects", "source_messages"),
    "media_disposition_attempts": ("media_assets",),
    "media_derivatives": ("media_assets",),
    "media_derivative_attempts": ("media_derivatives",),
    "offer_media": ("offers", "media_assets"),
}


def insert_order(tables: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Return one FK-safe insert order for the selected tables."""
    selected = set(tables or INCLUDED_TABLES)
    ordered: list[str] = []
    pending = set(selected)

    while pending:
        ready = sorted(
            table
            for table in pending
            if all(dep in ordered or dep not in selected for dep in TABLE_DEPENDENCIES.get(table, ()))
        )
        if not ready:
            msg = "unable to resolve FK-safe insert order"
            raise ValueError(msg)
        ordered.extend(ready)
        pending.difference_update(ready)

    return tuple(ordered)
