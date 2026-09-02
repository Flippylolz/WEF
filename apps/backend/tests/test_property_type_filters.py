"""Unit tests for map property-type filter semantics."""

from wef_backend.features.catalog.application import BoundingBox, MapFilters
from wef_backend.features.catalog.domain import FilterablePropertyType


def test_map_filters_include_property_types_in_normalized_key() -> None:
    """Equivalent property-type selections share one cache identity."""
    bbox = BoundingBox.parse("20.9,52.1,21.2,52.4")
    first = MapFilters(
        bbox=bbox,
        property_types=(
            FilterablePropertyType.HOUSE,
            FilterablePropertyType.APARTMENT,
        ),
    )
    second = MapFilters(
        bbox=bbox,
        property_types=(
            FilterablePropertyType.APARTMENT,
            FilterablePropertyType.HOUSE,
        ),
    )
    third = MapFilters(bbox=bbox, property_types=(FilterablePropertyType.HOUSE,))

    assert first.normalized_key() == second.normalized_key()
    assert first.normalized_key() != third.normalized_key()
