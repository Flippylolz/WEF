"""Small explicit test doubles for application and app-state boundaries."""

from dataclasses import dataclass

from wef_backend.features.catalog.application import (
    MapFilters,
    MapLocationRecord,
    MapQuerySnapshot,
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


async def always_ready() -> bool:
    """Return a healthy readiness result."""
    return True


async def never_ready() -> bool:
    """Return an unhealthy readiness result."""
    return False


async def close_nothing() -> None:
    """Satisfy resource cleanup without external resources."""
