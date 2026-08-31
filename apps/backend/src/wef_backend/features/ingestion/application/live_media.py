"""Process downloaded live Telegram media through the shared storage pipeline."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID  # noqa: TC003 — dataclass fields require runtime UUID

from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.media_grouping import (
    GROUPING_VERSION,
    StatefulMediaGrouper,
)
from wef_backend.features.ingestion.application.media_storage import MediaWorkItem, ProcessMedia
from wef_backend.features.ingestion.application.persistence import confidence_score
from wef_backend.features.ingestion.domain import GroupingInput
from wef_backend.features.ingestion.domain.media_storage import descriptor_identity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from wef_backend.features.ingestion.domain import RawMessage, SourceIdentity


@dataclass(frozen=True, slots=True)
class LiveSourceAnchor:
    """Current source/revision identity and optional canonical offer."""

    source_message_id: UUID
    revision_id: UUID
    offer_id: UUID | None


class LiveMediaAnchorPort(Protocol):
    """Resolve persisted source anchors and replay keys for live media."""

    async def source_anchors(self, channel: SourceIdentity) -> Mapping[int, LiveSourceAnchor]:
        """Return current source/revision identities keyed by external message id."""
        ...

    async def existing_media_replays(
        self,
        channel: SourceIdentity,
    ) -> set[tuple[UUID, int, UUID, str, str]]:
        """Return replay keys for media that already reached a terminal disposition."""
        ...


@dataclass(frozen=True, slots=True)
class LiveMediaPipeline:
    """Associate and store media for chronologically processed live messages."""

    processor: ProcessMedia
    anchors: LiveMediaAnchorPort
    grouper: StatefulMediaGrouper
    concurrency: int = 2

    async def process_message(
        self,
        *,
        channel: SourceIdentity,
        raw: RawMessage,
    ) -> int:
        """Group and persist media for one already-committed live message."""
        if not raw.media:
            return 0
        extraction = extract_listing(raw)
        dispositions = self.grouper.ingest(
            GroupingInput(message=raw, candidate=extraction.decision),
        )
        if not dispositions:
            return 0
        anchor_map = await self.anchors.source_anchors(channel)
        replayed = await self.anchors.existing_media_replays(channel)
        work: list[MediaWorkItem] = []
        for disposition in dispositions:
            reference = disposition.reference
            source = anchor_map.get(reference.source_message_id)
            if source is None:
                continue
            replay_key = (
                source.source_message_id,
                reference.media_index,
                source.revision_id,
                descriptor_identity(reference.descriptor),
                GROUPING_VERSION,
            )
            if replay_key in replayed:
                continue
            association = disposition.association
            listing_anchor = (
                anchor_map.get(association.listing_message_id) if association is not None else None
            )
            offer_id = listing_anchor.offer_id if listing_anchor is not None else None
            work.append(
                MediaWorkItem(
                    source_message_id=source.source_message_id,
                    source_message_revision_id=source.revision_id,
                    source_ordinal=reference.media_index,
                    descriptor=reference.descriptor,
                    association_version=GROUPING_VERSION,
                    offer_id=offer_id,
                    association_rule=(
                        association.rule if offer_id is not None and association else None
                    ),
                    association_confidence=(
                        confidence_score(association.confidence)
                        if offer_id is not None and association is not None
                        else None
                    ),
                ),
            )
        if not work:
            return 0
        limit = max(1, self.concurrency)
        processed = 0
        while processed < len(work):
            batch = work[processed : processed + limit]
            await asyncio.gather(*(self.processor(item) for item in batch))
            processed += len(batch)
        return len(work)
