"""Small explicit test doubles for application and app-state boundaries."""

from dataclasses import dataclass

from wef_backend.features.estates.application import EstateRecord


@dataclass(frozen=True, slots=True)
class FakeEstateQuery:
    """In-memory implementation of the application-owned query port."""

    records: tuple[EstateRecord, ...]

    async def list_estate_records(self) -> tuple[EstateRecord, ...]:
        """Return deterministic fake records."""
        return self.records


async def always_ready() -> bool:
    """Return a healthy readiness result."""
    return True


async def never_ready() -> bool:
    """Return an unhealthy readiness result."""
    return False


async def close_nothing() -> None:
    """Satisfy resource cleanup without external resources."""
