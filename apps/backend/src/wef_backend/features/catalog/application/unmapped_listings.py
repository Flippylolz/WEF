"""Discover visible offers without pretending their location is in the viewport."""

from dataclasses import dataclass
from typing import Protocol

from wef_backend.features.catalog.application.browse_catalog import (
    BrowseViewportListings,
    CursorError,
    ListingCursor,
    ListingCursorCodec,
    ListingSummaryDTO,
    ViewportListingSnapshot,
)
from wef_backend.features.catalog.application.map_query import MapFilters


class UnmappedListingQueryPort(Protocol):
    """Non-spatial listing discovery plus a separately scoped mapped count."""

    async def query_unmapped_listings(
        self, *, filters: MapFilters, cursor: ListingCursor | None, limit: int
    ) -> ViewportListingSnapshot:
        """Return bounded uncertain offers under non-spatial filters."""
        ...


@dataclass(frozen=True, slots=True)
class UnmappedListingPage:
    """Separate counts never imply point-less offers are inside a map viewport."""

    items: tuple[ListingSummaryDTO, ...]
    matching_count: int
    mapped_matching_count: int
    next_cursor: str | None


class BrowseUnmappedListings:
    """Apply a distinct cursor namespace and the shared offer display projection."""

    def __init__(self, query_port: UnmappedListingQueryPort) -> None:
        """Store the bounded discovery port."""
        self._query_port = query_port

    async def __call__(
        self, *, filters: MapFilters, cursor: str | None, limit: int
    ) -> UnmappedListingPage:
        """Keep non-spatial continuation independent from viewport pagination."""
        if cursor is not None and not cursor.startswith("u1."):
            msg = "uncertain listing cursor is invalid"
            raise CursorError(msg)
        decoded = ListingCursorCodec.decode(cursor[3:] if cursor is not None else None)
        snapshot = await self._query_port.query_unmapped_listings(
            filters=filters, cursor=decoded, limit=limit + 1
        )
        records = snapshot.records[:limit]
        next_cursor = None
        if len(snapshot.records) > limit:
            last = records[-1]
            next_cursor = "u1." + ListingCursorCodec.encode(
                ListingCursor(published_at=last.published_at, offer_id=last.id)
            )
        return UnmappedListingPage(
            items=tuple(BrowseViewportListings.decorate(record) for record in records),
            matching_count=snapshot.matching_count,
            mapped_matching_count=snapshot.mapped_matching_count,
            next_cursor=next_cursor,
        )
