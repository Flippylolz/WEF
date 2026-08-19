"""Unit tests for registry-backed quick filter resolution."""

from datetime import UTC, datetime, timedelta

import pytest

from wef_backend.features.catalog.application.map_query import (
    BoundingBox,
    MapFilterError,
    MapFilters,
)
from wef_backend.features.catalog.application.quick_filters import (
    apply_quick_filter,
    list_quick_filter_presets,
    resolve_quick_filter_published_from,
)


def test_list_quick_filter_presets_is_stable() -> None:
    """Expose at least the last-day preset in deterministic order."""
    presets = list_quick_filter_presets()
    assert [preset.id for preset in presets] == ["last_day"]
    assert presets[0].label_key == "quickFilter.last_day"


def test_last_day_resolves_to_rolling_twenty_four_hours() -> None:
    """Resolve last_day relative to the backend clock."""
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    published_from = resolve_quick_filter_published_from(preset_id="last_day", now=now)
    assert published_from == now - timedelta(days=1)


def test_apply_quick_filter_sets_published_from_and_identifier() -> None:
    """Apply one quick filter onto normalized map filters."""
    now = datetime(2026, 8, 19, tzinfo=UTC)
    bbox = BoundingBox.parse("20.9,52.1,21.2,52.4")
    base = MapFilters(bbox=bbox)
    resolved = apply_quick_filter(base, preset_id="last_day", now=now)
    assert resolved.quick_filter == "last_day"
    assert resolved.published_from == now - timedelta(days=1)


def test_apply_quick_filter_rejects_manual_publication_conflict() -> None:
    """Reject combining quick filters with explicit published_from."""
    now = datetime(2026, 8, 19, tzinfo=UTC)
    bbox = BoundingBox.parse("20.9,52.1,21.2,52.4")
    base = MapFilters(
        bbox=bbox,
        published_from=datetime(2026, 8, 1, tzinfo=UTC),
    )
    with pytest.raises(MapFilterError, match="quick_filter conflicts"):
        apply_quick_filter(base, preset_id="last_day", now=now)


def test_unknown_quick_filter_is_rejected() -> None:
    """Reject unsupported preset identifiers."""
    now = datetime(2026, 8, 19, tzinfo=UTC)
    with pytest.raises(MapFilterError, match="unknown"):
        resolve_quick_filter_published_from(preset_id="last_week", now=now)
