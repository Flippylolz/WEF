"""Registry-backed publication quick filters for catalog map queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from wef_backend.features.catalog.application.map_query import MapFilterError, MapFilters

_QUICK_FILTER_IDS: Final[frozenset[str]] = frozenset({"last_day"})


@dataclass(frozen=True, slots=True)
class QuickFilterPreset:
    """One server-defined quick filter exposed to clients."""

    id: str
    label_key: str


def list_quick_filter_presets() -> tuple[QuickFilterPreset, ...]:
    """Return every supported quick filter in stable display order."""
    return (
        QuickFilterPreset(id="last_day", label_key="quickFilter.last_day"),
    )


def resolve_quick_filter_published_from(*, preset_id: str, now: datetime) -> datetime:
    """Resolve one quick-filter identifier to an inclusive published_from timestamp."""
    if preset_id not in _QUICK_FILTER_IDS:
        message = "quick_filter is unknown"
        raise MapFilterError(message)
    if preset_id == "last_day":
        return now.astimezone(UTC) - timedelta(days=1)
    message = "quick_filter is unknown"
    raise MapFilterError(message)


def apply_quick_filter(
    filters: MapFilters,
    *,
    preset_id: str | None,
    now: datetime,
) -> MapFilters:
    """Apply one quick filter to normalized map filters."""
    if preset_id is None:
        return filters
    if filters.published_from is not None:
        message = "quick_filter conflicts with published_from"
        raise MapFilterError(message)
    published_from = resolve_quick_filter_published_from(preset_id=preset_id, now=now)
    return MapFilters(
        bbox=filters.bbox,
        price_min=filters.price_min,
        price_max=filters.price_max,
        area_min=filters.area_min,
        area_max=filters.area_max,
        rooms=filters.rooms,
        districts=filters.districts,
        market_types=filters.market_types,
        content_types=filters.content_types,
        published_from=published_from,
        published_to=filters.published_to,
        quick_filter=preset_id,
    )
