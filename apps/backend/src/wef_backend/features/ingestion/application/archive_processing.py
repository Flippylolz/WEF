"""Original-event recovery contracts and source-preserving orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.persistence import PersistableMessage
from wef_backend.features.ingestion.application.telegram_live import source_identity_from_channel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.ingestion.application.persistence import RunLock
    from wef_backend.features.ingestion.application.telegram_events import RawEventRecord
    from wef_backend.features.ingestion.domain.model import RawMessage, SourceIdentity
    from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity

ArchiveDisposition = Literal[
    "applied", "already_canonical", "non_candidate", "superseded", "deleted"
]
ARCHIVE_POLICY_VERSION = "archive-identity-v1"


@dataclass(frozen=True, slots=True)
class ArchiveResolution:
    """Immutable proof of an original event's committed canonical disposition."""

    event_id: UUID
    disposition: ArchiveDisposition
    committed_at: datetime


class ArchivedPayloadDecoder(Protocol):
    """Decode historical JSON without importing its adapter into application code."""

    def __call__(self, payload: Mapping[str, object], source: SourceIdentity) -> RawMessage:
        """Return lossless source evidence or reject malformed input."""
        ...


class ArchivePersistencePort(Protocol):
    """Canonical transaction and retained provenance required by recovery."""

    def run_lock(self, source_key: str) -> RunLock:
        """Serialize canonical work across worker processes."""
        ...

    async def archive_resolution(self, event_id: UUID) -> ArchiveResolution | None:
        """Read an already committed receipt before decoding or extracting."""
        ...

    async def archive_payload(self, record: RawEventRecord) -> Mapping[str, object]:
        """Prove the original JSON, including any legacy flattened seed lineage."""
        ...

    async def persist_archived_event(
        self,
        *,
        record: RawEventRecord,
        identity: TelegramChannelIdentity,
        message: PersistableMessage | None,
        release_sha: str | None,
    ) -> ArchiveResolution:
        """Commit canonical effect/no-op and original-event receipt atomically."""
        ...


@dataclass(frozen=True, slots=True)
class ArchivedEventProcessor:
    """Recover the original UUID; never synthesize and re-land a live sibling."""

    store: ArchivePersistencePort
    decoder: ArchivedPayloadDecoder

    async def __call__(
        self,
        *,
        record: RawEventRecord,
        identity: TelegramChannelIdentity,
        release_sha: str | None = None,
    ) -> ArchiveResolution:
        """Resume a committed receipt or apply validated archived source evidence."""
        if record.channel_external_id != identity.channel_id:
            msg = "archive channel mismatch"
            raise ValueError(msg)
        payload_id = record.payload.get("id")
        if (
            isinstance(payload_id, bool)
            or not isinstance(payload_id, int)
            or payload_id <= 0
            or payload_id != record.external_message_id
            or record.event_kind not in {"new", "edit", "delete"}
        ):
            msg = "archive identity mismatch"
            raise ValueError(msg)
        source = source_identity_from_channel(identity)
        async with self.store.run_lock(f"telegram:{identity.channel_id}"):
            receipt = await self.store.archive_resolution(record.id)
            if receipt is not None:
                return receipt
            payload = await self.store.archive_payload(record)
            message = None
            if record.event_kind != "delete":
                raw = self.decoder(payload, source)
                message = PersistableMessage(raw=raw, extraction=extract_listing(raw))
            return await self.store.persist_archived_event(
                record=record,
                identity=identity,
                message=message,
                release_sha=release_sha,
            )
