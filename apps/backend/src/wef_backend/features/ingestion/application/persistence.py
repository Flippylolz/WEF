"""Historical persistence use cases owned by the application layer."""

from __future__ import annotations

import hashlib
import json
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.domain.extraction import (
    Confidence,
    ContactSpan,
    DecimalRange,
    ExtractedValue,
    ExtractionResult,
    IntegerRange,
    ListingCandidate,
    MoneyRange,
)
from wef_backend.features.ingestion.domain.geocoding import normalize_location_display_name

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from uuid import UUID

    from wef_backend.features.ingestion.domain.model import RawMessage, SourceIdentity

EXCERPT_MAX_LENGTH = 280
MASK_FILLER = "•••"
_BATCH_DEFAULT = 50
_CONFIDENCE_SCORES = {
    Confidence.LOW: 0.5,
    Confidence.MEDIUM: 0.75,
    Confidence.HIGH: 0.95,
}


def confidence_score(confidence: Confidence) -> float:
    """Return the deterministic numeric score for one coarse confidence."""
    return _CONFIDENCE_SCORES[confidence]


class RunMode(StrEnum):
    """Persisted ingestion run modes."""

    DRY_RUN = "dry_run"
    HISTORICAL = "historical"
    REPROCESS = "reprocess"
    MEDIA_VERIFY = "media_verify"
    LIVE = "live"


class RunStatus(StrEnum):
    """Persisted ingestion run statuses."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageOutcome(StrEnum):
    """Per-message replay reconciliation outcome."""

    CREATED = "created"
    UNCHANGED = "unchanged"
    REVISED = "revised"
    SKIPPED_NON_CANDIDATE = "skipped_non_candidate"


class RunLockHeldError(RuntimeError):
    """Another process owns the complete-run lock for this source."""


class PersistenceBatchError(RuntimeError):
    """A bounded batch failed; its transaction rolled back entirely."""

    def __init__(self, category: str) -> None:
        """Store one redacted stable category without raw causes."""
        self.category = category
        super().__init__(f"ingestion batch failed: {category}")


class OfferFieldOriginSync(Protocol):
    """Optional parser-upsert hook implemented by admin provenance."""

    async def protected_field_names(self, offer_id: UUID) -> frozenset[str]:
        """Return AI-owned fields that parser upsert must not clobber."""
        ...

    async def after_offer_upsert(
        self,
        *,
        offer_id: UUID,
        parser_values: dict[str, object],
        parser_version: str,
        source_changed: bool,
        actor_id: str,
    ) -> None:
        """Invalidate or compare AI origins after a committed offer upsert."""
        ...


@dataclass(frozen=True, slots=True)
class PersistableMessage:
    """One raw source message paired with its extraction result."""

    raw: RawMessage
    extraction: ExtractionResult | None
    archive_event_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MessagePersistOutcome:
    """Reconciliation result for one persistable message."""

    external_message_id: int
    outcome: MessageOutcome
    revision_number: int


class DeletionOutcomeKind(StrEnum):
    """Per-id source delete reconciliation outcome."""

    DELETED = "deleted"
    ALREADY_DELETED = "already_deleted"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class SourceDeletionOutcome:
    """Result of marking one source message deleted."""

    external_message_id: int
    outcome: DeletionOutcomeKind
    offers_hidden: int


@dataclass(frozen=True, slots=True)
class RunCheckpoint:
    """Exactly the work acknowledged by the last committed transaction."""

    last_source_index: int = -1
    source_checksum: str | None = None

    def advances(self, source_index: int, checksum: str | None) -> RunCheckpoint:
        """Return the checkpoint acknowledging one more processed record."""
        if source_index <= self.last_source_index:
            message = "checkpoint may only advance forward"
            raise ValueError(message)
        return RunCheckpoint(
            last_source_index=source_index,
            source_checksum=checksum,
        )


@dataclass(frozen=True, slots=True)
class RunCounts:
    """Reconciled run counters kept atomic with the checkpoint."""

    seen: int = 0
    created: int = 0
    unchanged: int = 0
    revised: int = 0
    skipped_non_candidate: int = 0
    offers: int = 0

    def with_outcome(
        self,
        *,
        outcome: MessagePersistOutcome,
        offer_created: bool,
    ) -> RunCounts:
        """Return counts acknowledging one message outcome."""
        delta = {
            MessageOutcome.CREATED: "created",
            MessageOutcome.UNCHANGED: "unchanged",
            MessageOutcome.REVISED: "revised",
            MessageOutcome.SKIPPED_NON_CANDIDATE: "skipped_non_candidate",
        }[outcome.outcome]
        fields: dict[str, int] = {
            "seen": self.seen + 1,
            "created": self.created,
            "unchanged": self.unchanged,
            "revised": self.revised,
            "skipped_non_candidate": self.skipped_non_candidate,
            "offers": self.offers + (1 if offer_created else 0),
        }
        fields[delta] = fields[delta] + 1
        return RunCounts(**fields)


@dataclass(frozen=True, slots=True)
class IngestRunSummary:
    """Final reconciled state of one persisted ingestion run."""

    run_id: UUID
    channel_id: UUID
    mode: RunMode
    status: RunStatus
    counts: RunCounts
    checkpoint: RunCheckpoint
    parser_version: str
    error_summary: str | None


@dataclass(frozen=True, slots=True)
class RevisionAnchor:
    """The immutable revision a message now resolves to."""

    source_message_id: UUID
    revision_id: UUID
    revision_number: int
    checksum: str


RunLock = AbstractAsyncContextManager[None]


class IngestionPersistencePort(Protocol):
    """Persistence contract for historical ingestion."""

    def run_lock(self, source_key: str) -> RunLock:
        """Acquire the complete-run lock for one source key."""
        ...

    async def ensure_channel(
        self,
        *,
        platform: str,
        external_id: str,
        display_name: str,
    ) -> UUID:
        """Return the stable channel id, creating it once."""
        ...

    async def start_run(
        self,
        *,
        channel_id: UUID,
        mode: RunMode,
        parser_version: str,
        source_checksum: str | None,
        release_sha: str | None,
    ) -> UUID:
        """Create one running ingest run row."""
        ...

    async def persist_batch(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        batch: Sequence[tuple[PersistableMessage, int]],
        checkpoint: RunCheckpoint,
        counts: RunCounts,
    ) -> tuple[Sequence[MessagePersistOutcome], RunCheckpoint, RunCounts, int]:
        """Commit one bounded transaction of messages plus checkpoint.

        Returns per-message outcomes, the acknowledged checkpoint, the
        acknowledged counts, and the number of newly created offers.
        """
        ...

    async def persist_live_upsert(  # noqa: PLR0913
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        message: PersistableMessage,
        checkpoint: RunCheckpoint,
        counts: RunCounts,
        advance_checkpoint: bool,
    ) -> tuple[MessagePersistOutcome, RunCheckpoint, RunCounts, int]:
        """Upsert one live message; optionally advance the durable message-id cursor."""
        ...

    async def mark_source_deleted(
        self,
        *,
        channel_id: UUID,
        external_message_ids: Sequence[int],
        archive_event_ids: dict[int, UUID] | None = None,
    ) -> Sequence[SourceDeletionOutcome]:
        """Mark source messages deleted and hide linked offers without erasing lineage."""
        ...

    async def finish_run(
        self,
        *,
        run_id: UUID,
        status: RunStatus,
        counts: RunCounts,
        checkpoint: RunCheckpoint,
        error_summary: str | None,
    ) -> None:
        """Record the terminal run state."""
        ...

    async def persist_owner_ai_listing(
        self,
        *,
        source_message_revision_id: UUID,
        listing: ListingCandidate,
    ) -> UUID:
        """Create or update one offer from an owner-approved AI listing proposal."""
        ...


def money_to_minor(amount: Decimal) -> int:
    """Convert source major units to integer minor units."""
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _field_value(value: object) -> object:
    """Serialize one extracted field value without source span text."""
    if isinstance(value, MoneyRange):
        return {
            "min_minor": money_to_minor(value.amount.lower),
            "max_minor": money_to_minor(value.amount.upper),
            "currency": value.currency,
        }
    if isinstance(value, DecimalRange):
        return {"min": str(value.lower), "max": str(value.upper)}
    if isinstance(value, IntegerRange):
        return {"min": value.lower, "max": value.upper}
    if hasattr(value, "value") and isinstance(value, StrEnum):
        return value.value
    return value


def build_extraction_json(listing: ListingCandidate) -> str:
    """Serialize contact-free field provenance anchored to one revision."""
    fields: dict[str, dict[str, object]] = {}
    extracted: tuple[tuple[str, ExtractedValue[object] | None], ...] = (
        ("content_type", listing.content_type),
        ("market_type", listing.market_type),
        ("property_type", listing.property_type),
        ("location", listing.location),
        ("district", listing.district),
        ("development_name", listing.development_name),
        ("apartment_price", listing.apartment_price),
        ("parking_price", listing.parking_price),
        ("storage_price", listing.storage_price),
        ("parking_included_in_price", listing.parking_included_in_price),
        ("storage_included_in_price", listing.storage_included_in_price),
        ("area_sqm", listing.area_sqm),
        ("rooms", listing.rooms),
        ("floor", listing.floor),
        ("delivery", listing.delivery),
    )
    for name, item in extracted:
        if item is None:
            continue
        first_span = item.provenance.spans[0]
        fields[name] = {
            "value": _field_value(item.value),
            "rule": f"{item.provenance.rule_id}@{item.provenance.rule_version}",
            "confidence": confidence_score(item.provenance.confidence),
            "source_start": first_span.start,
            "source_end": first_span.end,
        }
    return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contact_spans(contacts: Sequence[ContactSpan]) -> tuple[tuple[int, int], ...]:
    """Return sorted merged contact-covered half-open ranges."""
    ranges = sorted((c.span.start, c.span.end) for c in contacts)
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def build_source_text_excerpt(text: str, contacts: Sequence[ContactSpan]) -> str:
    """Return a contact-free excerpt that omits covered source text."""
    pieces: list[str] = []
    cursor = 0
    for start, end in _contact_spans(contacts):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    excerpt = "".join(pieces)
    return excerpt[:EXCERPT_MAX_LENGTH]


def build_source_text_public_masked(text: str, contacts: Sequence[ContactSpan]) -> str:
    """Return the public rendering with contact spans replaced by filler."""
    pieces: list[str] = []
    cursor = 0
    for start, end in _contact_spans(contacts):
        pieces.append(text[cursor:start])
        pieces.append(MASK_FILLER)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def canonical_fingerprint(listing: ListingCandidate) -> str:
    """Hash the canonical typed projection as a duplicate suggestion key."""
    return extraction_fingerprint(json.loads(build_extraction_json(listing)))


def extraction_fingerprint(document: dict[str, object]) -> str:
    """Hash the same projection after a guarded partial extraction refresh."""
    values: dict[str, object] = {}
    for name in (
        "content_type",
        "market_type",
        "property_type",
        "location",
        "district",
        "development_name",
        "apartment_price",
        "parking_price",
        "storage_price",
        "area_sqm",
        "rooms",
        "floor",
        "delivery",
    ):
        field = document.get(name)
        value = field.get("value") if isinstance(field, dict) else None
        values[name] = " ".join(value.casefold().split()) if isinstance(value, str) else value
    payload = json.dumps(
        values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def normalized_location_key(location: str | None) -> str:
    """Return the deterministic replay key for one parsed location string."""
    candidate = " ".join((location or "").casefold().split())
    if not candidate:
        candidate = "unknown-location"
    return hashlib.sha256(candidate.encode()).hexdigest()


def normalize_location_text(
    location: str | None,
    *,
    district: str | None = None,
) -> str:
    """Return the canonical display name for one parsed location line."""
    return normalize_location_display_name(location, district=district)


def redacted_error_summary(error: BaseException) -> str:
    """Return one bounded redacted category for run error summaries."""
    names: Sequence[type[BaseException]] = (
        PersistenceBatchError,
        RunLockHeldError,
        ValueError,
        OSError,
    )
    for expected in names:
        if isinstance(error, expected):
            return expected.__name__
    return "UnclassifiedError"


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Run-level inputs recorded alongside persisted messages."""

    parser_version: str
    source_checksum: str | None = None
    release_sha: str | None = None
    mode: RunMode = RunMode.HISTORICAL


@dataclass(frozen=True, slots=True)
class PersistHistoricalIngestion:
    """Replay-safe historical persistence orchestrator."""

    store: IngestionPersistencePort
    batch_size: int = _BATCH_DEFAULT
    progress: Callable[[RunCounts], Awaitable[None]] | None = None

    async def __call__(
        self,
        *,
        channel: SourceIdentity,
        messages: Sequence[PersistableMessage],
        metadata: RunMetadata,
    ) -> IngestRunSummary:
        """Persist every message under the complete-run lock in bounded batches."""
        source_key = f"{channel.platform.value}:{channel.channel_id}"
        async with self.store.run_lock(source_key):
            channel_id = await self.store.ensure_channel(
                platform=channel.platform.value,
                external_id=channel.channel_id,
                display_name=channel.channel_name,
            )
            run_id = await self.store.start_run(
                channel_id=channel_id,
                mode=metadata.mode,
                parser_version=metadata.parser_version,
                source_checksum=metadata.source_checksum,
                release_sha=metadata.release_sha,
            )
            checkpoint = RunCheckpoint(source_checksum=metadata.source_checksum)
            counts = RunCounts()
            try:
                for start in range(0, len(messages), self.batch_size):
                    batch = tuple(
                        (message, index)
                        for index, message in enumerate(
                            messages[start : start + self.batch_size],
                            start=start,
                        )
                    )
                    _, checkpoint, counts, _ = await self.store.persist_batch(
                        channel_id=channel_id,
                        run_id=run_id,
                        batch=batch,
                        checkpoint=checkpoint,
                        counts=counts,
                    )
                    if self.progress is not None:
                        await self.progress(counts)
            except PersistenceBatchError as error:
                await self.store.finish_run(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    counts=counts,
                    checkpoint=checkpoint,
                    error_summary=redacted_error_summary(error),
                )
                raise
            await self.store.finish_run(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                counts=counts,
                checkpoint=checkpoint,
                error_summary=None,
            )
            return IngestRunSummary(
                run_id=run_id,
                channel_id=channel_id,
                mode=metadata.mode,
                status=RunStatus.SUCCEEDED,
                counts=counts,
                checkpoint=checkpoint,
                parser_version=metadata.parser_version,
                error_summary=None,
            )
