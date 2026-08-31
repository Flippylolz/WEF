"""Persisted source message identity anchors shared across ingestion paths."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID  # noqa: TC003 — dataclass fields require runtime UUID


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """Current source/revision identity and optional canonical offer."""

    source_message_id: UUID
    revision_id: UUID
    offer_id: UUID | None
