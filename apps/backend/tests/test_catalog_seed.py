"""Unit tests for the explicit synthetic catalog seed."""

from collections.abc import Sequence
from types import TracebackType
from typing import TYPE_CHECKING, cast

import pytest

from wef_backend.features.catalog.application import (
    ProductionSeedError,
    SeedLocation,
    SeedM1Catalog,
    SeedOffer,
    SeedResult,
)
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class FakeSeedPort:
    """Record seed calls without persistence."""

    def __init__(self) -> None:
        """Initialize an empty call counter."""
        self.calls = 0

    async def upsert_seed(
        self,
        locations: Sequence[SeedLocation],
        offers: Sequence[SeedOffer],
    ) -> SeedResult:
        """Return counts matching the supplied fixture."""
        self.calls += 1
        return SeedResult(locations=len(locations), offers=len(offers))


class FakeSession:
    """Capture SQL statements emitted by the infrastructure adapter."""

    def __init__(self) -> None:
        """Initialize an empty statement list."""
        self.statements: list[object] = []

    async def execute(self, statement: object) -> None:
        """Record a statement without opening PostgreSQL."""
        self.statements.append(statement)


class FakeTransaction:
    """Provide the async context expected from a session factory."""

    def __init__(self, session: FakeSession) -> None:
        """Store the recording session."""
        self._session = session

    async def __aenter__(self) -> FakeSession:
        """Return the recording session."""
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Leave the synthetic transaction."""
        del exc_type, exc_value, traceback


class FakeSessionFactory:
    """Return one recording transaction."""

    def __init__(self) -> None:
        """Create one recording session."""
        self.session = FakeSession()

    def begin(self) -> FakeTransaction:
        """Open the recording transaction."""
        return FakeTransaction(self.session)


async def test_seed_service_reconciles_non_production_fixture() -> None:
    """A non-production service delegates one complete fixture transaction."""
    port = FakeSeedPort()
    result = await SeedM1Catalog(port, environment="test")(*m1_fixture())

    assert result == SeedResult(locations=4, offers=5)
    assert port.calls == 1


async def test_seed_service_rejects_production_before_persistence() -> None:
    """Production cannot invoke the synthetic persistence port."""
    port = FakeSeedPort()

    with pytest.raises(ProductionSeedError, match="disabled in production"):
        await SeedM1Catalog(port, environment="production")(*m1_fixture())

    assert port.calls == 0


async def test_seed_service_requires_explicit_production_rehearsal_opt_in() -> None:
    """A production fixture is allowed only through the narrow explicit flag."""
    port = FakeSeedPort()

    result = await SeedM1Catalog(
        port,
        environment="production",
        allow_production=True,
    )(*m1_fixture())

    assert result == SeedResult(locations=4, offers=5)
    assert port.calls == 1


def test_m1_fixture_is_stable_and_explicitly_synthetic() -> None:
    """Repeated fixture construction preserves IDs and synthetic labeling."""
    first = m1_fixture()
    second = m1_fixture()

    assert first == second
    assert len({location.id for location in first[0]}) == 4
    assert len({offer.id for offer in first[1]}) == 5
    assert all("Synthetic" in location.display_name for location in first[0])
    assert all(offer.published_at.tzinfo is not None for offer in first[1])


async def test_sqlalchemy_seed_adapter_emits_two_upserts() -> None:
    """The adapter emits location then offer convergence in one transaction."""
    factory = FakeSessionFactory()
    adapter = SQLAlchemyCatalogSeedAdapter(
        cast("async_sessionmaker[AsyncSession]", factory),
    )

    result = await adapter.upsert_seed(*m1_fixture())

    assert result == SeedResult(locations=4, offers=5)
    assert len(factory.session.statements) == 2
