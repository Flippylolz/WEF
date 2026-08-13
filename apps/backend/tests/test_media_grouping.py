"""Deterministic E2 media grouping and boundary tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from wef_backend.features.ingestion.application import (
    GROUPING_VERSION,
    TIME_BURST_SECONDS,
    detect_candidate,
    group_media,
)
from wef_backend.features.ingestion.domain import (
    Confidence,
    GroupingInput,
    MalformedReason,
    MediaAssociation,
    MediaAssociationRule,
    MediaDescriptor,
    MediaDisposition,
    MediaGroup,
    MediaKind,
    MediaReference,
    RawMessage,
    SourceIdentity,
    SourcePlatform,
    UnassociatedMediaReason,
    canonical_json_checksum,
    freeze_json,
)
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from collections.abc import Iterator

FIXTURE = (
    Path(__file__).parent / "fixtures" / "telegram_export" / "sanitized-media-grouping-cases.json"
)
_BASE_TIME = datetime(2031, 1, 1, tzinfo=UTC)


def _source() -> SourceIdentity:
    return SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="grouping-fixture",
        channel_name="Grouping Fixture",
        channel_type="public_channel",
    )


def _message(  # noqa: PLR0913
    message_id: int,
    second: int,
    *,
    text: str = "",
    message_type: str = "message",
    media_kinds: tuple[MediaKind, ...] = (),
    reply_to: int | None = None,
    group_id: str | None = None,
) -> RawMessage:
    payload = {
        "id": message_id,
        "type": message_type,
        "text": text,
        "reply_to_message_id": reply_to,
        "grouped_id": group_id,
    }
    frozen = freeze_json(payload)
    assert isinstance(frozen, Mapping)
    return RawMessage(
        source=_source(),
        external_message_id=message_id,
        reply_to_message_id=reply_to,
        published_at=_BASE_TIME + timedelta(seconds=second),
        edited_at=None,
        message_type=message_type,
        text=text,
        original_text=text,
        text_entities=(),
        media=tuple(
            MediaDescriptor(
                kind=kind,
                path=f"photos/sample_{message_id}_{index}.bin",
            )
            for index, kind in enumerate(media_kinds)
        ),
        raw_payload=frozen,
        checksum=canonical_json_checksum(payload),
        media_group_id=group_id,
    )


def _input(message: RawMessage, *, expected_candidate: bool) -> GroupingInput:
    decision = detect_candidate(message)
    assert decision.is_candidate is expected_candidate
    return GroupingInput(message=message, candidate=decision)


def _fixture_inputs() -> list[GroupingInput]:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    items: list[GroupingInput] = []
    for event in document["events"]:
        message = _message(
            event["message_id"],
            event["second"],
            text=event["text"],
            message_type=event.get("type", "message"),
            media_kinds=tuple(MediaKind(kind) for kind in event["media"]),
            reply_to=event.get("reply_to"),
            group_id=event.get("group_id"),
        )
        items.append(_input(message, expected_candidate=event["candidate"]))
    return items


def _snapshot(disposition: MediaDisposition) -> dict[str, Any]:
    association = disposition.association
    return {
        "message_id": disposition.reference.source_message_id,
        "media_index": disposition.reference.media_index,
        "listing_id": association.listing_message_id if association else None,
        "rule": association.rule.value if association else None,
        "reason": (
            disposition.unassociated_reason.value
            if disposition.unassociated_reason is not None
            else None
        ),
    }


def test_media_grouping_matches_complete_reviewed_golden() -> None:
    """Every descriptor follows the approved evidence order and is reconciled."""
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    first = tuple(group_media(_fixture_inputs()))
    second = tuple(group_media(_fixture_inputs()))

    assert first == second
    assert [_snapshot(item) for item in first] == document["expected"]
    assert len(first) == sum(len(event["media"]) for event in document["events"])
    assert all(
        item.association is not None or item.unassociated_reason is not None for item in first
    )
    assert first[1].association is not None
    assert first[1].association.rule is MediaAssociationRule.EXPLICIT_GROUP
    assert first[3].association is not None
    assert first[3].association.rule is MediaAssociationRule.REPLY
    assert first[4].association is not None
    assert first[4].association.confidence is Confidence.MEDIUM
    assert first[6].association is not None
    assert first[6].association.listing_message_id == 208
    assert first[6].association.listing_message_id != 205


def test_time_burst_accepts_exact_boundary_and_uses_each_adjacent_gap() -> None:
    """A 120-second adjacent gap is accepted and advances the active run."""
    candidate = _message(301, 0, text="Kupno | Mieszkanie")
    first_media = _message(302, TIME_BURST_SECONDS, media_kinds=(MediaKind.PHOTO,))
    second_media = _message(
        303,
        TIME_BURST_SECONDS * 2,
        media_kinds=(MediaKind.VIDEO,),
    )

    dispositions = tuple(
        group_media(
            (
                _input(candidate, expected_candidate=True),
                _input(first_media, expected_candidate=False),
                _input(second_media, expected_candidate=False),
            )
        )
    )

    assert tuple(item.association.rule for item in dispositions if item.association) == (
        MediaAssociationRule.TIME_BURST,
        MediaAssociationRule.TIME_BURST,
    )
    assert all(
        item.association is not None and item.association.listing_message_id == 301
        for item in dispositions
    )


def test_empty_non_media_record_and_reply_end_active_burst() -> None:
    """Adjacency does not cross an empty record or explicit reply boundary."""
    records = (
        _input(
            _message(401, 0, text="Kupno | Mieszkanie"),
            expected_candidate=True,
        ),
        _input(_message(402, 10), expected_candidate=False),
        _input(
            _message(403, 20, media_kinds=(MediaKind.PHOTO,)),
            expected_candidate=False,
        ),
        _input(
            _message(404, 30, text="Kupno | Mieszkanie"),
            expected_candidate=True,
        ),
        _input(_message(405, 40, reply_to=999), expected_candidate=False),
        _input(
            _message(406, 50, media_kinds=(MediaKind.PHOTO,)),
            expected_candidate=False,
        ),
    )

    dispositions = tuple(group_media(records))

    assert tuple(item.unassociated_reason for item in dispositions) == (
        UnassociatedMediaReason.NO_ACTIVE_CANDIDATE,
        UnassociatedMediaReason.NO_ACTIVE_CANDIDATE,
    )


def test_grouping_is_lazy_and_rejects_non_chronological_input() -> None:
    """The service yields from active state and fails on unsorted records."""
    first = _input(
        _message(501, 10, text="Kupno | Mieszkanie", media_kinds=(MediaKind.PHOTO,)),
        expected_candidate=True,
    )

    def guarded_records() -> Iterator[GroupingInput]:
        yield first
        message = "grouping eagerly consumed beyond the requested result"
        raise AssertionError(message)

    iterator = group_media(guarded_records())
    assert next(iterator).association is not None

    with pytest.raises(ValueError, match="chronological"):
        tuple(
            group_media(
                (
                    _input(
                        _message(502, 20, text="Kupno | Mieszkanie"),
                        expected_candidate=True,
                    ),
                    _input(
                        _message(503, 10, media_kinds=(MediaKind.PHOTO,)),
                        expected_candidate=False,
                    ),
                )
            )
        )
    with pytest.raises(ValueError, match="version"):
        tuple(group_media((), grouping_version=""))


def test_media_domain_values_reject_mixed_or_duplicate_shapes() -> None:
    """Association groups retain source ownership and disjoint dispositions."""
    reference = MediaReference(601, 0, MediaDescriptor(MediaKind.PHOTO, "safe/sample.jpg"))
    association = MediaAssociation(
        reference=reference,
        listing_message_id=600,
        rule=MediaAssociationRule.REPLY,
        confidence=Confidence.HIGH,
        grouping_version=GROUPING_VERSION,
    )

    assert MediaDisposition(reference, association=association).reference == reference
    assert MediaGroup(600, (association,)).associations == (association,)
    with pytest.raises(ValueError, match="positive source"):
        MediaReference(0, 0, reference.descriptor)
    with pytest.raises(ValueError, match="associated or unassociated"):
        MediaDisposition(reference)
    with pytest.raises(ValueError, match="retain"):
        MediaDisposition(
            MediaReference(602, 0, reference.descriptor),
            association=association,
        )
    with pytest.raises(ValueError, match="listing identity"):
        MediaGroup(600, ())
    with pytest.raises(ValueError, match="one listing"):
        MediaGroup(
            601,
            (association,),
        )
    with pytest.raises(ValueError, match="duplicate"):
        MediaGroup(600, (association, association))


def test_telegram_adapter_populates_and_validates_source_group_id() -> None:
    """Adapter conversion keeps optional group IDs source-neutral."""
    raw = {
        "id": 701,
        "type": "message",
        "date_unixtime": "1924992000",
        "grouped_id": 123456,
        "text": "",
        "text_entities": [],
    }

    converted = convert_record(raw, 0, _source())
    assert converted.result.message is not None
    assert converted.result.message.media_group_id == "123456"

    invalid = convert_record({**raw, "grouped_id": False}, 0, _source())
    assert invalid.result.message is None
    assert invalid.result.reason is MalformedReason.INVALID_MEDIA_GROUP_ID
