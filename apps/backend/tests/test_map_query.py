"""Unit tests for backend-owned map filter and projection behavior."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from wef_backend.features.catalog.application import (
    BoundingBox,
    MapFilterError,
    MapFilters,
    MapQuerySnapshot,
    QueryMapLocations,
)


@dataclass(frozen=True, slots=True)
class VersionedMapQuery:
    """Return an empty projection with a controlled data version."""

    data_version: datetime | None

    async def query_map(self, _: MapFilters) -> MapQuerySnapshot:
        """Return the controlled snapshot."""
        return MapQuerySnapshot(records=(), data_version=self.data_version)


@pytest.mark.parametrize(
    "value",
    [
        "20.9,52.2,21.0",
        "not-a-bbox",
        "21.2,52.1,21.0,52.4",
        "-180,-90,180,90",
        "20.5,51.8,21.5,52.6",
    ],
)
def test_bbox_rejects_malformed_or_unsafe_extent(value: str) -> None:
    """Keep map queries finite, ordered, local, and bounded."""
    with pytest.raises(MapFilterError):
        BoundingBox.parse(value)


def test_filter_rejects_contradictory_ranges() -> None:
    """Reject ranges the adapter cannot meaningfully intersect."""
    bbox = BoundingBox.parse("20.9,52.1,21.2,52.4")

    with pytest.raises(MapFilterError, match="price_min"):
        MapFilters(bbox=bbox, price_min=2, price_max=1)
    with pytest.raises(MapFilterError, match="area_min"):
        MapFilters(bbox=bbox, area_min=Decimal(20), area_max=Decimal(10))
    with pytest.raises(MapFilterError, match="published_from"):
        MapFilters(
            bbox=bbox,
            published_from=datetime(2026, 8, 2, tzinfo=UTC),
            published_to=datetime(2026, 8, 1, tzinfo=UTC),
        )


def test_normalized_key_identity_is_repeat_and_order_stable() -> None:
    """Equivalent repeated/ordered filter inputs serialize to one identity."""
    base = MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"))
    repeated = MapFilters(
        bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"),
        districts=("Wola", "Wola", "Mokotów"),
        rooms=(2, 1, 2),
    )
    ordered = MapFilters(
        bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"),
        districts=("Mokotów", "Wola"),
        rooms=(1, 2),
    )
    assert repeated.normalized_key() == ordered.normalized_key()
    assert (
        base.normalized_key()
        == MapFilters(
            bbox=BoundingBox.parse("20.9,52.1,21.2,52.4"),
        ).normalized_key()
    )


async def test_etag_normalizes_equivalent_filters_and_tracks_data_version() -> None:
    """Request ordering does not churn ETags while persisted changes do."""
    bbox = BoundingBox.parse("20.9000000,52.1000,21.200,52.400")
    left = MapFilters(
        bbox=bbox,
        area_min=Decimal("40.0"),
        rooms=(2, 1, 2),
        districts=("Wola", "Mokotów"),
    )
    right = MapFilters(
        bbox=bbox,
        area_min=Decimal(40),
        rooms=(1, 2),
        districts=("Mokotów", "Wola"),
    )
    first_service = QueryMapLocations(
        VersionedMapQuery(datetime(2026, 8, 1, tzinfo=UTC)),
    )
    changed_service = QueryMapLocations(
        VersionedMapQuery(datetime(2026, 8, 2, tzinfo=UTC)),
    )

    first = await first_service(left)
    equivalent = await first_service(right)
    changed = await changed_service(right)

    assert first.etag == equivalent.etag
    assert changed.etag != equivalent.etag
