"""SQLAlchemy persistence for historical ingestion with complete-run locking."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text, update

from wef_backend.features.catalog.domain import OfferVisibility
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.contacts.application.reveal import (
    ContactCipher,
    ContactCryptoUnavailableError,
    ContactInput,
    build_contact_records,
)
from wef_backend.features.contacts.domain.model import ContactKind as StoredContactKind
from wef_backend.features.contacts.infrastructure.models import ContactPointRow
from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    IngestionPersistencePort,
    MessageOutcome,
    MessagePersistOutcome,
    OfferFieldOriginSync,
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunLock,
    RunLockHeldError,
    RunMode,
    RunStatus,
    SourceDeletionOutcome,
    build_extraction_json,
    build_source_text_excerpt,
    build_source_text_public_masked,
    canonical_fingerprint,
    confidence_score,
    money_to_minor,
    normalize_location_text,
    normalized_location_key,
    redacted_error_summary,
)
from wef_backend.features.ingestion.infrastructure.models import (
    DevelopmentRow,
    IngestRunRow,
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRevisionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.domain.extraction import ListingCandidate
    from wef_backend.features.ingestion.domain.model import RawMessage

_SIGNED_64 = (1 << 63) - 1
_PRIMARY_RELATIONSHIP = "primary"
_FIELD_COLUMNS = {
    "market_type": "market_type",
    "currency": "currency",
    "apartment_price_min": "price_min_minor",
    "apartment_price_max": "price_max_minor",
    "parking_price_min": "parking_price_min_minor",
    "parking_price_max": "parking_price_max_minor",
    "parking_included_in_price": "parking_included_in_price",
    "storage_price_min": "storage_price_min_minor",
    "storage_price_max": "storage_price_max_minor",
    "storage_included_in_price": "storage_included_in_price",
    "area_min_sqm": "area_min_sqm",
    "area_max_sqm": "area_max_sqm",
    "rooms_min": "rooms_min",
    "rooms_max": "rooms_max",
    "floor_label": "floor_label",
    "delivery_label": "delivery_label",
}


def _allowlisted_parser_values(values: dict[str, object]) -> dict[str, object]:
    """Project canonical offer columns onto allowlisted enrichment fields."""
    area_min = values.get("area_min_sqm")
    area_max = values.get("area_max_sqm")
    return {
        "market_type": values.get("market_type"),
        "currency": values.get("currency"),
        "apartment_price_min": values.get("price_min_minor"),
        "apartment_price_max": values.get("price_max_minor"),
        "parking_price_min": values.get("parking_price_min_minor"),
        "parking_price_max": values.get("parking_price_max_minor"),
        "parking_included_in_price": bool(values.get("parking_included_in_price")),
        "storage_price_min": values.get("storage_price_min_minor"),
        "storage_price_max": values.get("storage_price_max_minor"),
        "storage_included_in_price": bool(values.get("storage_included_in_price")),
        "area_min_sqm": None if area_min is None else str(area_min),
        "area_max_sqm": None if area_max is None else str(area_max),
        "rooms_min": values.get("rooms_min"),
        "rooms_max": values.get("rooms_max"),
        "floor_label": values.get("floor_label"),
        "delivery_label": values.get("delivery_label"),
    }


def _lock_id(source_key: str) -> int:
    """Return one stable signed 64-bit advisory lock key."""
    digest = hashlib.sha256(source_key.encode()).digest()
    value = int.from_bytes(digest[:8], "big")
    return value if value <= _SIGNED_64 else value - (1 << 64)


def _json_text(value: object) -> str:
    """Serialize source JSON values deterministically."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def _json_default(value: object) -> object:
    """Thaw immutable source mappings without weakening JSON type checks."""
    if isinstance(value, Mapping):
        return dict(value)
    message = f"Object of type {type(value).__name__} is not JSON serializable"
    raise TypeError(message)


@dataclass(frozen=True, slots=True)
class _MessageResult:
    """Internal reconciliation result for one message in a transaction."""

    outcome: MessageOutcome
    offer_created: bool
    revision_number: int
    offer_id: UUID | None = None
    parser_version: str | None = None
    parser_values: dict[str, object] | None = None
    source_changed: bool = False


@dataclass(frozen=True, slots=True)
class _OfferPersistResult:
    """Offer upsert identity used after the persist transaction commits."""

    created: bool
    offer_id: UUID
    source_changed: bool
    parser_version: str
    parser_values: dict[str, object]


class SQLAlchemyIngestionPersistence(IngestionPersistencePort):
    """Ingestion persistence with advisory complete-run exclusion."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        contact_cipher: ContactCipher | None = None,
        field_origin_sync: OfferFieldOriginSync | None = None,
    ) -> None:
        """Store the lazy session factory and optional contact cipher."""
        self._session_factory = session_factory
        self._contact_cipher = contact_cipher
        self._field_origin_sync = field_origin_sync

    def run_lock(self, source_key: str) -> RunLock:
        """Hold one session-level advisory lock for the complete run."""
        return self._run_lock(source_key)

    @asynccontextmanager
    async def _run_lock(self, source_key: str) -> AsyncIterator[None]:
        """Acquire or reject the run lock on one dedicated connection."""
        engine = self._session_factory.kw["bind"]
        lock_id = _lock_id(source_key)
        async with engine.connect() as connection:
            acquired = (
                await connection.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": lock_id},
                )
            ).scalar_one()
            if not acquired:
                message = "another process owns the ingestion run lock"
                raise RunLockHeldError(message)
            await connection.commit()
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": lock_id},
                )
                await connection.commit()

    async def ensure_channel(
        self,
        *,
        platform: str,
        external_id: str,
        display_name: str,
    ) -> UUID:
        """Return the stable channel id, creating it once."""
        async with self._session_factory() as session:
            existing = await session.scalar(
                select(SourceChannelRow.id)
                .where(
                    SourceChannelRow.platform == platform,
                    SourceChannelRow.external_id == external_id,
                )
                .limit(1),
            )
            if existing is not None:
                return existing
            row = SourceChannelRow(
                id=uuid4(),
                platform=platform,
                external_id=external_id,
                display_name=display_name,
            )
            session.add(row)
            await session.commit()
            return row.id

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
        run_id = uuid4()
        async with self._session_factory() as session:
            session.add(
                IngestRunRow(
                    id=run_id,
                    source_channel_id=channel_id,
                    mode=mode.value,
                    status=RunStatus.RUNNING.value,
                    source_checksum=source_checksum,
                    parser_version=parser_version,
                    release_sha=release_sha,
                    started_at=datetime.now(UTC),
                ),
            )
            await session.commit()
        return run_id

    async def persist_batch(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        batch: Sequence[tuple[PersistableMessage, int]],
        checkpoint: RunCheckpoint,
        counts: RunCounts,
    ) -> tuple[Sequence[MessagePersistOutcome], RunCheckpoint, RunCounts, int]:
        """Commit one bounded transaction of messages plus its checkpoint."""
        outcomes: list[MessagePersistOutcome] = []
        results: list[_MessageResult] = []
        acknowledged = checkpoint
        acknowledged_counts = counts
        try:
            async with self._session_factory() as session, session.begin():
                for persistable, source_index in batch:
                    result = await self._persist_message(
                        session,
                        channel_id=channel_id,
                        persistable=persistable,
                    )
                    results.append(result)
                    outcomes.append(
                        MessagePersistOutcome(
                            external_message_id=persistable.raw.external_message_id,
                            outcome=result.outcome,
                            revision_number=result.revision_number,
                        ),
                    )
                    acknowledged = checkpoint.advances(
                        source_index,
                        persistable.raw.checksum,
                    )
                    acknowledged_counts = acknowledged_counts.with_outcome(
                        outcome=outcomes[-1],
                        offer_created=result.offer_created,
                    )
                await session.execute(
                    update(IngestRunRow)
                    .where(IngestRunRow.id == run_id)
                    .values(
                        checkpoint_json=asdict(acknowledged),
                        counts_json=asdict(acknowledged_counts),
                    ),
                )
        except PersistenceBatchError:
            raise
        except Exception as error:
            raise PersistenceBatchError(redacted_error_summary(error)) from error
        for result in results:
            await self._notify_origin_sync(result)
        offers_created = sum(1 for result in results if result.offer_created)
        return outcomes, acknowledged, acknowledged_counts, offers_created

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
        try:
            async with self._session_factory() as session, session.begin():
                result = await self._persist_message(
                    session,
                    channel_id=channel_id,
                    persistable=message,
                )
                outcome = MessagePersistOutcome(
                    external_message_id=message.raw.external_message_id,
                    outcome=result.outcome,
                    revision_number=result.revision_number,
                )
                acknowledged = checkpoint
                if advance_checkpoint:
                    acknowledged = checkpoint.advances(
                        message.raw.external_message_id,
                        message.raw.checksum,
                    )
                acknowledged_counts = counts.with_outcome(
                    outcome=outcome,
                    offer_created=result.offer_created,
                )
                await session.execute(
                    update(IngestRunRow)
                    .where(IngestRunRow.id == run_id)
                    .values(
                        checkpoint_json=asdict(acknowledged),
                        counts_json=asdict(acknowledged_counts),
                    ),
                )
        except PersistenceBatchError:
            raise
        except Exception as error:
            raise PersistenceBatchError(redacted_error_summary(error)) from error
        await self._notify_origin_sync(result)
        return outcome, acknowledged, acknowledged_counts, int(result.offer_created)

    async def mark_source_deleted(
        self,
        *,
        channel_id: UUID,
        external_message_ids: Sequence[int],
    ) -> Sequence[SourceDeletionOutcome]:
        """Mark source messages deleted and hide linked offers without erasing lineage."""
        outcomes: list[SourceDeletionOutcome] = []
        try:
            async with self._session_factory() as session, session.begin():
                now = datetime.now(UTC)
                for external_id in external_message_ids:
                    existing = await session.scalar(
                        select(SourceMessageRow)
                        .where(
                            SourceMessageRow.source_channel_id == channel_id,
                            SourceMessageRow.external_message_id == external_id,
                        )
                        .limit(1),
                    )
                    if existing is None:
                        outcomes.append(
                            SourceDeletionOutcome(
                                external_message_id=external_id,
                                outcome=DeletionOutcomeKind.MISSING,
                                offers_hidden=0,
                            ),
                        )
                        continue
                    if existing.deleted_at is not None:
                        outcomes.append(
                            SourceDeletionOutcome(
                                external_message_id=external_id,
                                outcome=DeletionOutcomeKind.ALREADY_DELETED,
                                offers_hidden=0,
                            ),
                        )
                        continue
                    existing.deleted_at = now
                    hide_result = await session.execute(
                        update(OfferRow)
                        .where(
                            OfferRow.id.in_(
                                select(OfferSourceRow.offer_id).where(
                                    OfferSourceRow.source_message_id == existing.id,
                                ),
                            ),
                            OfferRow.visibility != OfferVisibility.HIDDEN.value,
                        )
                        .values(visibility=OfferVisibility.HIDDEN.value),
                    )
                    outcomes.append(
                        SourceDeletionOutcome(
                            external_message_id=external_id,
                            outcome=DeletionOutcomeKind.DELETED,
                            offers_hidden=int(getattr(hide_result, "rowcount", 0) or 0),
                        ),
                    )
        except Exception as error:
            raise PersistenceBatchError(redacted_error_summary(error)) from error
        return tuple(outcomes)

    async def _persist_message(
        self,
        session: AsyncSession,
        *,
        channel_id: UUID,
        persistable: PersistableMessage,
    ) -> _MessageResult:
        """Reconcile one message and its candidate offer in this transaction."""
        raw = persistable.raw
        existing = await session.scalar(
            select(SourceMessageRow)
            .where(
                SourceMessageRow.source_channel_id == channel_id,
                SourceMessageRow.external_message_id == raw.external_message_id,
            )
            .limit(1),
        )
        payload = json.loads(_json_text(dict(raw.raw_payload)))
        entities = json.loads(_json_text(list(raw.text_entities)))
        now = datetime.now(UTC)
        if existing is None:
            message_id = uuid4()
            revision_id = uuid4()
            session.add(
                SourceMessageRow(
                    id=message_id,
                    source_channel_id=channel_id,
                    external_message_id=raw.external_message_id,
                    current_revision_id=revision_id,
                    message_type=raw.message_type,
                    published_at=raw.published_at,
                    edited_at=raw.edited_at,
                    text_original=raw.text,
                    entities_json=entities,
                    raw_payload_json=payload,
                    raw_checksum=raw.checksum,
                    ingested_at=now,
                ),
            )
            await session.flush()
            session.add(
                SourceMessageRevisionRow(
                    id=revision_id,
                    source_message_id=message_id,
                    revision_number=1,
                    captured_at=now,
                    message_type=raw.message_type,
                    published_at=raw.published_at,
                    edited_at=raw.edited_at,
                    text_original=raw.text,
                    entities_json=entities,
                    raw_payload_json=payload,
                    raw_checksum=raw.checksum,
                ),
            )
            outcome = MessageOutcome.CREATED
            revision_number = 1
            anchor_revision_id = revision_id
            message_id_for_offer = message_id
        elif existing.raw_checksum == raw.checksum:
            outcome = MessageOutcome.UNCHANGED
            anchor_revision_id = existing.current_revision_id
            message_id_for_offer = existing.id
            revision_number = int(
                await session.scalar(
                    select(SourceMessageRevisionRow.revision_number)
                    .where(SourceMessageRevisionRow.id == existing.current_revision_id)
                    .limit(1),
                )
                or 1,
            )
        else:
            max_number = await session.scalar(
                select(func.max(SourceMessageRevisionRow.revision_number)).where(
                    SourceMessageRevisionRow.source_message_id == existing.id,
                ),
            )
            revision_number = int(max_number or 0) + 1
            revision_id = uuid4()
            session.add(
                SourceMessageRevisionRow(
                    id=revision_id,
                    source_message_id=existing.id,
                    revision_number=revision_number,
                    captured_at=now,
                    message_type=raw.message_type,
                    published_at=raw.published_at,
                    edited_at=raw.edited_at,
                    text_original=raw.text,
                    entities_json=entities,
                    raw_payload_json=payload,
                    raw_checksum=raw.checksum,
                ),
            )
            await session.execute(
                update(SourceMessageRow)
                .where(SourceMessageRow.id == existing.id)
                .values(
                    current_revision_id=revision_id,
                    message_type=raw.message_type,
                    published_at=raw.published_at,
                    edited_at=raw.edited_at,
                    text_original=raw.text,
                    entities_json=entities,
                    raw_payload_json=payload,
                    raw_checksum=raw.checksum,
                    ingested_at=now,
                ),
            )
            outcome = MessageOutcome.REVISED
            anchor_revision_id = revision_id
            message_id_for_offer = existing.id

        listing = persistable.extraction.listing if persistable.extraction else None
        offer_created = False
        offer_id = None
        source_changed = False
        parser_version = None
        parser_values = None
        if listing is None:
            if outcome is MessageOutcome.CREATED:
                outcome = MessageOutcome.SKIPPED_NON_CANDIDATE
        else:
            persisted = await self._persist_offer(
                session,
                listing=listing,
                raw=raw,
                message_id=message_id_for_offer,
                revision_id=anchor_revision_id,
            )
            offer_created = persisted.created
            offer_id = persisted.offer_id
            source_changed = persisted.source_changed
            parser_version = persisted.parser_version
            parser_values = persisted.parser_values
        return _MessageResult(
            outcome=outcome,
            offer_created=offer_created,
            revision_number=revision_number,
            offer_id=offer_id,
            source_changed=source_changed,
            parser_version=parser_version,
            parser_values=parser_values,
        )

    async def _resolve_location(
        self,
        session: AsyncSession,
        listing: ListingCandidate,
    ) -> UUID:
        """Find or create the ungeocoded location for one parsed address."""
        parsed = listing.location.value if listing.location else None
        key = normalized_location_key(parsed)
        existing = await session.scalar(
            select(LocationRow.id).where(LocationRow.normalized_address_hash == key).limit(1),
        )
        if existing is not None:
            return existing
        location_text = normalize_location_text(parsed)
        location_id = uuid4()
        session.add(
            LocationRow(
                id=location_id,
                display_name=location_text,
                display_address=location_text,
                normalized_address=" ".join(location_text.casefold().split()),
                normalized_address_hash=key,
                district=listing.district.value if listing.district else None,
                point=None,
                precision="unknown",
                confidence=Decimal("0.00"),
                review_status="ungeocoded",
            ),
        )
        await self._resolve_development(session, location_id, listing)
        return location_id

    async def _resolve_development(
        self,
        session: AsyncSession,
        location_id: UUID,
        listing: ListingCandidate,
    ) -> None:
        """Record a named development under its location when evidenced."""
        if listing.development_name is None:
            return
        display_name = " ".join(listing.development_name.value.split())[:160]
        normalized_name = display_name.casefold()
        existing = await session.scalar(
            select(DevelopmentRow.id)
            .where(
                DevelopmentRow.location_id == location_id,
                DevelopmentRow.normalized_name == normalized_name,
            )
            .limit(1),
        )
        if existing is None:
            session.add(
                DevelopmentRow(
                    id=uuid4(),
                    location_id=location_id,
                    display_name=display_name,
                    normalized_name=normalized_name,
                    name_confidence=Decimal(
                        str(confidence_score(listing.development_name.provenance.confidence)),
                    ).quantize(Decimal("0.01")),
                ),
            )

    def _offer_values(
        self,
        listing: ListingCandidate,
        raw: RawMessage,
        location_id: UUID,
    ) -> dict[str, object]:
        """Map one typed listing onto canonical offer column values."""
        apartment = listing.apartment_price.value if listing.apartment_price else None
        parking = listing.parking_price.value if listing.parking_price else None
        storage = listing.storage_price.value if listing.storage_price else None
        parking_included = bool(
            listing.parking_included_in_price and listing.parking_included_in_price.value,
        )
        storage_included = bool(
            listing.storage_included_in_price and listing.storage_included_in_price.value,
        )
        area = listing.area_sqm.value if listing.area_sqm else None
        rooms = listing.rooms.value if listing.rooms else None
        floor = (listing.floor.value if listing.floor else None) or None
        delivery = (listing.delivery.value if listing.delivery else None) or None
        return {
            "location_id": location_id,
            "content_type": (listing.content_type.value if listing.content_type else "unit"),
            "market_type": (listing.market_type.value if listing.market_type else "unknown"),
            "visibility": "needs_review",
            "published_at": raw.published_at,
            "latest_source_at": raw.edited_at or raw.published_at,
            "currency": apartment.currency if apartment else None,
            "price_min_minor": (money_to_minor(apartment.amount.lower) if apartment else None),
            "price_max_minor": (money_to_minor(apartment.amount.upper) if apartment else None),
            "parking_price_min_minor": (
                None
                if parking_included or parking is None
                else money_to_minor(parking.amount.lower)
            ),
            "parking_price_max_minor": (
                None
                if parking_included or parking is None
                else money_to_minor(parking.amount.upper)
            ),
            "parking_included_in_price": parking_included,
            "storage_price_min_minor": (
                None
                if storage_included or storage is None
                else money_to_minor(storage.amount.lower)
            ),
            "storage_price_max_minor": (
                None
                if storage_included or storage is None
                else money_to_minor(storage.amount.upper)
            ),
            "storage_included_in_price": storage_included,
            "area_min_sqm": area.lower if area else None,
            "area_max_sqm": area.upper if area else None,
            "rooms_min": rooms.lower if rooms else None,
            "rooms_max": rooms.upper if rooms else None,
            "floor_label": floor[:80] if floor else None,
            "delivery_label": delivery[:80] if delivery else None,
            "source_text_excerpt": build_source_text_excerpt(raw.text, listing.contacts),
            "source_text_public_masked": build_source_text_public_masked(
                raw.text,
                listing.contacts,
            ),
            "canonical_fingerprint": canonical_fingerprint(listing),
            "parser_version": listing.parser_version,
        }

    async def _persist_offer(
        self,
        session: AsyncSession,
        *,
        listing: ListingCandidate,
        raw: RawMessage,
        message_id: UUID,
        revision_id: UUID,
    ) -> _OfferPersistResult:
        """Upsert the canonical offer and its revision-anchored provenance."""
        existing_offer_id = await session.scalar(
            select(OfferSourceRow.offer_id)
            .where(
                OfferSourceRow.source_message_id == message_id,
                OfferSourceRow.relationship == _PRIMARY_RELATIONSHIP,
            )
            .limit(1),
        )
        location_id = await self._resolve_location(session, listing)
        values = self._offer_values(listing, raw, location_id)
        parser_values = _allowlisted_parser_values(values)
        offer_id = existing_offer_id
        if offer_id is None:
            offer_id = uuid4()
            session.add(OfferRow(id=offer_id, **values))
        else:
            if self._field_origin_sync is not None:
                protected = await self._field_origin_sync.protected_field_names(offer_id)
                for field_name in protected:
                    values.pop(_FIELD_COLUMNS[field_name], None)
            await session.execute(
                update(OfferRow).where(OfferRow.id == offer_id).values(**values),
            )
        existing_link = await session.scalar(
            select(OfferSourceRow.id)
            .where(
                OfferSourceRow.offer_id == offer_id,
                OfferSourceRow.source_message_revision_id == revision_id,
            )
            .limit(1),
        )
        source_changed = existing_link is None
        if existing_link is None:
            confidence = (
                confidence_score(listing.content_type.provenance.confidence)
                if listing.content_type is not None
                else 0.5
            )
            session.add(
                OfferSourceRow(
                    id=uuid4(),
                    offer_id=offer_id,
                    source_message_id=message_id,
                    source_message_revision_id=revision_id,
                    relationship=_PRIMARY_RELATIONSHIP,
                    confidence=Decimal(str(confidence)).quantize(Decimal("0.001")),
                    extraction_json=json.loads(build_extraction_json(listing)),
                ),
            )
            await self._persist_contacts(
                session,
                offer_id=offer_id,
                source_message_id=message_id,
                listing=listing,
            )
        return _OfferPersistResult(
            created=existing_offer_id is None,
            offer_id=offer_id,
            source_changed=source_changed,
            parser_version=listing.parser_version,
            parser_values=parser_values,
        )

    async def _notify_origin_sync(self, result: _MessageResult) -> None:
        """Compare or invalidate AI origins after a committed offer upsert."""
        if (
            self._field_origin_sync is None
            or result.offer_id is None
            or result.parser_values is None
            or result.parser_version is None
        ):
            return
        await self._field_origin_sync.after_offer_upsert(
            offer_id=result.offer_id,
            parser_values=result.parser_values,
            parser_version=result.parser_version,
            source_changed=result.source_changed,
            actor_id="parser-replay",
        )

    async def _persist_contacts(
        self,
        session: AsyncSession,
        *,
        offer_id: UUID,
        source_message_id: UUID,
        listing: ListingCandidate,
    ) -> None:
        """Encrypt and replace contact points on the active offer session."""
        if self._contact_cipher is None:
            return
        contacts = tuple(
            ContactInput(kind=StoredContactKind(span.kind.value), value=span.value)
            for span in listing.contacts
        )
        try:
            records = build_contact_records(
                self._contact_cipher,
                offer_id=offer_id,
                source_message_id=source_message_id,
                contacts=contacts,
            )
        except ContactCryptoUnavailableError:
            # Fail closed: keep masked public text, skip ciphertext until keys exist.
            return
        await session.execute(
            delete(ContactPointRow).where(ContactPointRow.offer_id == offer_id),
        )
        for item in records:
            session.add(
                ContactPointRow(
                    id=item.id,
                    offer_id=item.offer_id,
                    source_message_id=item.source_message_id,
                    kind=item.kind.value,
                    value_ciphertext=item.value_ciphertext,
                    masked_value=item.masked_value,
                    fingerprint_hmac=item.fingerprint_hmac,
                    is_revealable=item.is_revealable,
                ),
            )

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
        async with self._session_factory() as session:
            await session.execute(
                update(IngestRunRow)
                .where(IngestRunRow.id == run_id)
                .values(
                    status=status.value,
                    checkpoint_json=asdict(checkpoint),
                    counts_json=asdict(counts),
                    error_summary=error_summary,
                    finished_at=datetime.now(UTC),
                ),
            )
            await session.commit()
