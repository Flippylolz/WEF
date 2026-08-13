"""Chronological deterministic media association for E2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from wef_backend.features.ingestion.domain import (
    Confidence,
    GroupingInput,
    MediaAssociation,
    MediaAssociationRule,
    MediaDisposition,
    MediaReference,
    UnassociatedMediaReason,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import datetime

    from wef_backend.features.ingestion.domain import RawMessage

GROUPING_VERSION = "e2-media-v1"
TIME_BURST_SECONDS = 120
_TIME_BURST = timedelta(seconds=TIME_BURST_SECONDS)


@dataclass(slots=True)
class _GroupingState:
    active_listing_id: int | None = None
    active_at: datetime | None = None
    last_seen_at: datetime | None = None
    candidates: dict[int, int] = field(default_factory=dict)
    explicit_groups: dict[str, int] = field(default_factory=dict)

    def clear_active(self) -> None:
        self.active_listing_id = None
        self.active_at = None

    def activate(self, listing_id: int, published_at: datetime) -> None:
        self.active_listing_id = listing_id
        self.active_at = published_at


def group_media(
    records: Iterable[GroupingInput],
    *,
    grouping_version: str = GROUPING_VERSION,
) -> Iterator[MediaDisposition]:
    """Yield one ordered disposition per descriptor without reading media files."""
    if not grouping_version:
        error = "grouping version must not be empty"
        raise ValueError(error)
    state = _GroupingState()
    for item in records:
        message = item.message
        _validate_chronology(state, message)
        if message.message_type == "service":
            state.clear_active()
            yield from _unassociated(message, UnassociatedMediaReason.SERVICE_BOUNDARY)
        elif item.candidate.is_candidate:
            yield from _candidate_media(message, state, grouping_version)
        else:
            yield from _non_candidate_media(message, state, grouping_version)
        state.last_seen_at = message.published_at


def _validate_chronology(state: _GroupingState, message: RawMessage) -> None:
    if state.last_seen_at is not None and message.published_at < state.last_seen_at:
        error = "media grouping input must be chronological"
        raise ValueError(error)


def _candidate_media(
    message: RawMessage,
    state: _GroupingState,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    listing_id = message.external_message_id
    state.candidates[listing_id] = listing_id
    if message.media_group_id is not None:
        state.explicit_groups[message.media_group_id] = listing_id
    state.activate(listing_id, message.published_at)
    yield from _associated(
        message,
        listing_id,
        MediaAssociationRule.SAME_MESSAGE,
        Confidence.HIGH,
        grouping_version,
    )


def _non_candidate_media(
    message: RawMessage,
    state: _GroupingState,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    if message.reply_to_message_id is not None:
        state.clear_active()
    if message.media_group_id is not None:
        yield from _explicit_group_media(message, state, grouping_version)
        return
    if message.reply_to_message_id is not None:
        yield from _reply_media(message, state, grouping_version)
        return
    if message.text.strip():
        state.clear_active()
        yield from _unassociated(message, UnassociatedMediaReason.TEXT_BOUNDARY)
        return
    if not message.media:
        state.clear_active()
        return
    yield from _adjacent_media(message, state, grouping_version)


def _explicit_group_media(
    message: RawMessage,
    state: _GroupingState,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    group_id = cast("str", message.media_group_id)
    owner = state.explicit_groups.get(group_id)
    if owner is None:
        state.clear_active()
        yield from _unassociated(message, UnassociatedMediaReason.UNKNOWN_EXPLICIT_GROUP)
        return
    yield from _associated(
        message,
        owner,
        MediaAssociationRule.EXPLICIT_GROUP,
        Confidence.HIGH,
        grouping_version,
    )
    if message.reply_to_message_id is None:
        state.activate(owner, message.published_at)


def _reply_media(
    message: RawMessage,
    state: _GroupingState,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    reply_id = cast("int", message.reply_to_message_id)
    owner = state.candidates.get(reply_id)
    if owner is None:
        yield from _unassociated(message, UnassociatedMediaReason.UNKNOWN_REPLY_TARGET)
        return
    yield from _associated(
        message,
        owner,
        MediaAssociationRule.REPLY,
        Confidence.HIGH,
        grouping_version,
    )


def _adjacent_media(
    message: RawMessage,
    state: _GroupingState,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    if state.active_listing_id is None or state.active_at is None:
        yield from _unassociated(message, UnassociatedMediaReason.NO_ACTIVE_CANDIDATE)
        return
    if message.published_at - state.active_at > _TIME_BURST:
        state.clear_active()
        yield from _unassociated(message, UnassociatedMediaReason.TIME_GAP)
        return
    owner = state.active_listing_id
    yield from _associated(
        message,
        owner,
        MediaAssociationRule.TIME_BURST,
        Confidence.MEDIUM,
        grouping_version,
    )
    state.activate(owner, message.published_at)


def _associated(
    message: RawMessage,
    listing_id: int,
    rule: MediaAssociationRule,
    confidence: Confidence,
    grouping_version: str,
) -> Iterator[MediaDisposition]:
    for media_index, descriptor in enumerate(message.media):
        reference = MediaReference(
            source_message_id=message.external_message_id,
            media_index=media_index,
            descriptor=descriptor,
        )
        association = MediaAssociation(
            reference=reference,
            listing_message_id=listing_id,
            rule=rule,
            confidence=confidence,
            grouping_version=grouping_version,
        )
        yield MediaDisposition(reference=reference, association=association)


def _unassociated(
    message: RawMessage,
    reason: UnassociatedMediaReason,
) -> Iterator[MediaDisposition]:
    for media_index, descriptor in enumerate(message.media):
        reference = MediaReference(
            source_message_id=message.external_message_id,
            media_index=media_index,
            descriptor=descriptor,
        )
        yield MediaDisposition(reference=reference, unassociated_reason=reason)
