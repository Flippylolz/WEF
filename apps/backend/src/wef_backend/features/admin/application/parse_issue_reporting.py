"""Owner read models for ingestion parse issue reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.features.ingestion.domain.parse_issue import SourceMessageParseIssue


class ParseIssueReportingStore(Protocol):
    """Read recent parse issues for admin export."""

    async def list_recent(self, *, limit: int = 500) -> tuple[SourceMessageParseIssue, ...]:
        """Return newest parse issues."""
        ...


class ParseIssueOfferLinkStore(Protocol):
    """Link recovered offers back onto parse issue ledger rows."""

    async def link_offer_for_message(
        self,
        *,
        source_message_id: UUID,
        offer_id: UUID,
    ) -> int:
        """Attach one offer id to unset parse issue rows for the same message."""
        ...


class ListParseIssueEvents:
    """Return bounded parse issue rows for reporting/export."""

    def __init__(self, store: ParseIssueReportingStore) -> None:
        """Initialize the store."""
        self._store = store

    async def __call__(
        self,
        *,
        owner_id: UUID,
        limit: int = 500,
    ) -> tuple[SourceMessageParseIssue, ...]:
        """Return newest parse issues for the owner console."""
        _ = owner_id
        return await self._store.list_recent(limit=limit)
