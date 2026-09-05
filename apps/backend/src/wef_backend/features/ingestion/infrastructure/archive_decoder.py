"""Historical converter adaptation for archive recovery and parser replay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.model import RecordDisposition
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from collections.abc import Mapping

    from wef_backend.features.ingestion.domain.model import RawMessage, SourceIdentity


def decode_archived_payload(payload: Mapping[str, object], source: SourceIdentity) -> RawMessage:
    """Preserve source JSON, entities, mixed text, media and checksum exactly."""
    converted = convert_record(payload, 0, source).result
    if converted.message is None or converted.disposition is not RecordDisposition.ACCEPTED:
        msg = "archived source record is malformed or unsupported"
        raise ValueError(msg)
    return converted.message
