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
    BrowseViewportListings,
    CursorCodec,
    CursorError,
    ListingBrowseRecord,
    ListingCursor,
    ListingCursorCodec,
    ListingLocationContext,
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
            FakeScalarResult(
                ["srodmiescie", None, "wola", "Praga Po\u0141Udnie", "Praga-Po\u0142udnie"]
            ),
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
        parking_price_min_minor=5_000_000 if complete else None,
        parking_price_max_minor=5_000_000 if complete else None,
        parking_included_in_price=False,
        storage_price_min_minor=None,
        storage_price_max_minor=None,
        storage_included_in_price=complete,
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

    assert facets.districts == ("Praga-Po\u0142udnie", "Wola", "\u015ar\u00f3dmie\u015bcie")
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
    assert page.items[0].parking_price_min_minor == 5_000_000
    assert page.items[0].storage_included_in_price is True
    assert page.items[1].data_confidence == "partial"
    assert page.next_cursor is not None
    decoded = CursorCodec.decode(page.next_cursor)
    assert decoded is not None
    assert decoded.offer_id == records[1].id


def listing_record(index: int, *, complete: bool = True) -> ListingBrowseRecord:
    """Build a stable viewport listing record with parent context."""
    return ListingBrowseRecord(
        id=UUID(f"20000000-0000-4000-8000-{index:012d}"),
        content_type=ContentType.DEVELOPMENT,
        market_type=MarketType.PRIMARY,
        published_at=datetime(2026, 8, index, tzinfo=UTC),
        currency="PLN" if complete else None,
        price_min_minor=90_000_000 if complete else None,
        price_max_minor=90_000_000 if complete else None,
        parking_price_min_minor=None,
        parking_price_max_minor=None,
        parking_included_in_price=False,
        storage_price_min_minor=None,
        storage_price_max_minor=None,
        storage_included_in_price=False,
        area_min_sqm=Decimal("35.00") if complete else None,
        area_max_sqm=Decimal("35.00") if complete else None,
        rooms_min=1 if complete else None,
        rooms_max=3 if complete else None,
        floor_label=None,
        delivery_label="Q3 2026",
        location=ListingLocationContext(
            id=UUID(f"10000000-0000-4000-8000-{index:012d}"),
            display_name=f"Synthetic Residence {index}",
            display_address=f"Synthetic address {index}, Warsaw",
            district="wola",
            precision="address",
            confidence=Decimal("0.95") if index % 2 else Decimal("0.60"),
            longitude=20.99 + index / 100,
            latitude=52.23 + index / 100,
        ),
    )


def test_listing_cursor_codec_round_trips_and_rejects_tampering() -> None:
    """Keep viewport pagination transport opaque, bounded, and strict."""
    cursor = ListingCursor(
        published_at=datetime(2026, 8, 2, tzinfo=UTC),
        offer_id=UUID("20000000-0000-4000-8000-000000000002"),
    )

    encoded = ListingCursorCodec.encode(cursor)

    assert ListingCursorCodec.decode(encoded) == cursor
    assert ListingCursorCodec.decode(None) is None
    with pytest.raises(CursorError):
        ListingCursorCodec.decode("not valid base64!")
    with pytest.raises(CursorError):
        ListingCursorCodec.decode("x" * 513)


async def test_viewport_listings_decorate_location_context_and_paginate() -> None:
    """Return a newest-first page with decorated parent location context."""
    records = (listing_record(3), listing_record(2, complete=False), listing_record(1))
    adapter = FakeCatalogBrowse(
        facets=empty_facet_snapshot(),
        viewport_records=records,
        viewport_matching_count=3,
    )
    service = BrowseViewportListings(adapter)

    page = await service(
        filters=MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4")),
        cursor=None,
        limit=2,
    )

    assert [item.id for item in page.items] == [records[0].id, records[1].id]
    assert page.matching_count == 3
    first = page.items[0]
    assert first.display_name == "Development post · Primary market"
    assert first.data_confidence == "complete"
    assert first.delivery_label == "Q3 2026"
    assert first.location.display_name == "Synthetic Residence 3"
    assert first.location.district == "wola"
    assert first.location.confidence_indicator == "high"
    assert (first.location.longitude, first.location.latitude) == (
        records[0].location.longitude,
        records[0].location.latitude,
    )
    assert page.items[1].data_confidence == "partial"
    assert page.items[1].location.confidence_indicator == "low"
    assert page.next_cursor is not None
    decoded = ListingCursorCodec.decode(page.next_cursor)
    assert decoded is not None
    assert decoded.offer_id == records[1].id
    assert decoded.published_at == records[1].published_at


async def test_viewport_listings_last_page_has_no_cursor() -> None:
    """A page that exhausts the candidate set carries no continuation."""
    adapter = FakeCatalogBrowse(
        facets=empty_facet_snapshot(),
        viewport_records=(listing_record(2), listing_record(1)),
        viewport_matching_count=2,
    )
    service = BrowseViewportListings(adapter)

    page = await service(
        filters=MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4")),
        cursor=None,
        limit=2,
    )

    assert len(page.items) == 2
    assert page.next_cursor is None


async def test_viewport_listings_reject_invalid_cursor() -> None:
    """A malformed cursor surfaces as a controlled query error."""
    adapter = FakeCatalogBrowse(facets=empty_facet_snapshot())
    service = BrowseViewportListings(adapter)

    with pytest.raises(CursorError):
        await service(
            filters=MapFilters(bbox=BoundingBox.parse("20.9,52.1,21.2,52.4")),
            cursor="broken-cursor",
            limit=10,
        )
