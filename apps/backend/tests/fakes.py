"""Small explicit test doubles for application and app-state boundaries."""

from dataclasses import dataclass

from wef_backend.features.catalog.application import (
    FacetSnapshot,
    MapFilters,
    MapLocationRecord,
    MapQuerySnapshot,
    OfferBrowseRecord,
    OfferBrowseSnapshot,
    OfferCursor,
)
from wef_backend.features.estates.application import EstateRecord


@dataclass(frozen=True, slots=True)
class FakeEstateQuery:
    """In-memory implementation of the application-owned query port."""

    records: tuple[EstateRecord, ...]

    async def list_estate_records(self) -> tuple[EstateRecord, ...]:
        """Return deterministic fake records."""
        return self.records


@dataclass(frozen=True, slots=True)
class FakeMapQuery:
    """In-memory implementation of the grouped map query port."""

    records: tuple[MapLocationRecord, ...] = ()

    async def query_map(self, _: MapFilters) -> MapQuerySnapshot:
        """Return deterministic grouped records without a database."""
        return MapQuerySnapshot(records=self.records, data_version=None)


@dataclass(frozen=True, slots=True)
class FakeCatalogBrowse:
    """In-memory facets and selected-location query adapter."""

    facets: FacetSnapshot
    records: tuple[OfferBrowseRecord, ...] = ()
    location_exists: bool = True
    matching_count: int = 0
    total_count: int = 0

    async def query_facets(self) -> FacetSnapshot:
        """Return deterministic facet values."""
        return self.facets

    async def query_location_offers(
        self,
        *,
        location_id: object,
        filters: MapFilters,
        include_non_matching: bool,
        cursor: OfferCursor | None,
        limit: int,
    ) -> OfferBrowseSnapshot:
        """Return deterministic records while satisfying the port shape."""
        del location_id, filters, include_non_matching, cursor
        return OfferBrowseSnapshot(
            location_exists=self.location_exists,
            records=self.records[:limit],
            matching_count=self.matching_count,
            total_count=self.total_count,
        )


def empty_facet_snapshot() -> FacetSnapshot:
    """Return an empty valid facet response for app-state tests."""
    return FacetSnapshot(
        districts=(),
        rooms=(),
        market_types=(),
        content_types=(),
        price_min_minor=None,
        price_max_minor=None,
        area_min_sqm=None,
        area_max_sqm=None,
        published_from=None,
        published_to=None,
    )


async def always_ready() -> bool:
    """Return a healthy readiness result."""
    return True


async def never_ready() -> bool:
    """Return an unhealthy readiness result."""
    return False


async def close_nothing() -> None:
    """Satisfy resource cleanup without external resources."""
