"""Unit tests for facet/offer browsing application behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import UUID

import pytest

from tests.fakes import FakeCatalogBrowse, empty_facet_snapshot
from wef_backend.features.catalog.application import (
    BoundingBox,
    BrowseLocationOffers,
    CursorCodec,
    CursorError,
    MapFilters,
    OfferBrowseRecord,
    OfferCursor,
)
from wef_backend.features.catalog.domain import ContentType, MarketType
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogBrowseAdapter

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class FakeResult:
    """Return one controlled aggregate row."""

    def __init__(self, row: tuple[Any, ...]) -> None:
        """Store the row."""
        self._row = row

    def one(self) -> tuple[Any, ...]:
        """Return the aggregate row."""
        return self._row


class FakeScalarResult:
    """Return one controlled scalar collection."""

    def __init__(self, values: list[Any]) -> None:
        """Store scalar values."""
        self._values = values

    def all(self) -> list[Any]:
        """Return scalar values."""
        return self._values


class FakeFacetSession:
    """Provide aggregate and scalar query results in call order."""

    def __init__(self) -> None:
        """Initialize deterministic scalar responses."""
        self._scalars = [
            FakeScalarResult(["srodmiescie", None, "wola"]),
            FakeScalarResult(["primary", "secondary"]),
            FakeScalarResult(["development", "unit"]),
        ]

    async def __aenter__(self) -> Self:
        """Enter the fake session."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Exit the fake session."""

    async def execute(self, _: object) -> FakeResult:
        """Return one visible dataset bounds row."""
        return FakeResult(
            (
                69_000_000,
                149_000_000,
                Decimal("29.50"),
                Decimal("72.00"),
                1,
                3,
                datetime(2026, 6, 30, tzinfo=UTC),
                datetime(2026, 8, 5, tzinfo=UTC),
            ),
        )

    async def scalars(self, _: object) -> FakeScalarResult:
        """Return the next scalar query response."""
        return self._scalars.pop(0)


class FakeFacetSessionFactory:
    """Create one fake facet session."""

    def __call__(self) -> FakeFacetSession:
        """Return a new fake session."""
        return FakeFacetSession()


def offer_record(index: int, *, complete: bool = True) -> OfferBrowseRecord:
    """Build a stable dated offer record."""
    return OfferBrowseRecord(
        id=UUID(f"20000000-0000-4000-8000-{index:012d}"),
        content_type=ContentType.UNIT,
        market_type=MarketType.SECONDARY,
        published_at=datetime(2026, 8, index, tzinfo=UTC),
        currency="PLN" if complete else None,
        price_min_minor=100_000_000 if complete else None,
        price_max_minor=100_000_000 if complete else None,
        area_min_sqm=Decimal("40.00") if complete else None,
        area_max_sqm=Decimal("40.00") if complete else None,
        rooms_min=2 if complete else None,
        rooms_max=2 if complete else None,
        floor_label=None,
        delivery_label=None,
        matches_filters=True,
    )


def test_cursor_codec_round_trips_and_rejects_tampering() -> None:
    """Keep pagination transport opaque, bounded, and strict."""
    cursor = OfferCursor(
        match_rank=1,
        published_at=datetime(2026, 8, 2, tzinfo=UTC),
        offer_id=UUID("20000000-0000-4000-8000-000000000002"),
    )

    encoded = CursorCodec.encode(cursor)

    assert CursorCodec.decode(encoded) == cursor
    with pytest.raises(CursorError):
        CursorCodec.decode("not valid base64!")
    with pytest.raises(CursorError):
        CursorCodec.decode("x" * 513)


async def test_facet_adapter_normalizes_visible_aggregate_values() -> None:
    """Map SQL aggregate values into canonical sorted domain options."""
    factory = cast(
        "async_sessionmaker[AsyncSession]",
        FakeFacetSessionFactory(),
    )
    adapter = SQLAlchemyCatalogBrowseAdapter(factory)

    facets = await adapter.query_facets()

    assert facets.districts == ("srodmiescie", "wola")
    assert facets.rooms == (1, 2, 3)
    assert facets.market_types == (MarketType.PRIMARY, MarketType.SECONDARY)
    assert facets.content_types == (ContentType.DEVELOPMENT, ContentType.UNIT)
    assert facets.price_min_minor == 69_000_000


async def test_browse_decorates_and_paginates_without_exposing_source_data() -> None:
    """Return a limit-sized page and cursor from the last emitted item."""
    records = (
        offer_record(3),
        offer_record(2, complete=False),
        offer_record(1),
    )
    adapter = FakeCatalogBrowse(
        facets=empty_facet_snapshot(),
        records=records,
        matching_count=3,
        total_count=3,
    )
    service = BrowseLocationOffers(adapter)

    page = await service(
        location_id=UUID("10000000-0000-4000-8000-000000000001"),
        filters=MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4")),
        include_non_matching=False,
        cursor=None,
        limit=2,
    )

    assert [item.id for item in page.items] == [records[0].id, records[1].id]
    assert page.items[0].data_confidence == "complete"
    assert page.items[1].data_confidence == "partial"
    assert page.next_cursor is not None
    decoded = CursorCodec.decode(page.next_cursor)
    assert decoded is not None
    assert decoded.offer_id == records[1].id
