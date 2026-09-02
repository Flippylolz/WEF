"""Framework-independent persistence application unit tests."""

import json
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest

from wef_backend.features.catalog.domain import ContentType
from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    MessageOutcome,
    MessagePersistOutcome,
    PersistableMessage,
    PersistenceBatchError,
    PersistHistoricalIngestion,
    RunCheckpoint,
    RunCounts,
    RunLockHeldError,
    RunMetadata,
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
from wef_backend.features.ingestion.domain.extraction import (
    Confidence,
    ContactKind,
    ContactSpan,
    DecimalRange,
    ExtractedValue,
    ListingCandidate,
    MoneyRange,
    RuleProvenance,
    SourceSpan,
)
from wef_backend.features.ingestion.domain.model import RawMessage, SourceIdentity, SourcePlatform


def _provenance(start: int, end: int) -> RuleProvenance:
    """Build one minimal deterministic provenance over a single span."""
    return RuleProvenance(
        rule_id="rule",
        rule_version="v1",
        confidence=Confidence.HIGH,
        spans=(SourceSpan(start=start, end=end),),
    )


def _contact(start: int, end: int, value: str) -> ContactSpan:
    """Build one contact span covering the given range."""
    return ContactSpan(
        kind=ContactKind.PHONE,
        value=value,
        span=SourceSpan(start=start, end=end),
        provenance=_provenance(start, end),
    )


def _raw(
    message_id: int = 1,
    text: str = "Base text",
    checksum: str = "a" * 64,
) -> RawMessage:
    """Build one minimal replayable raw message."""
    return RawMessage(
        source=SourceIdentity(
            platform=SourcePlatform.TELEGRAM,
            channel_id="2180077318",
            channel_name="El Estate | Покупка Варшава",
            channel_type="public_channel",
        ),
        external_message_id=message_id,
        reply_to_message_id=None,
        published_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        edited_at=None,
        message_type="text",
        text=text,
        original_text=text,
        text_entities=(),
        media=(),
        raw_payload={"id": message_id},
        checksum=checksum,
    )


def test_confidence_scores_are_deterministic() -> None:
    """Coarse confidences map to stable numeric scores."""
    assert confidence_score(Confidence.LOW) == 0.5
    assert confidence_score(Confidence.MEDIUM) == 0.75
    assert confidence_score(Confidence.HIGH) == 0.95


def test_money_to_minor_rounds_half_up() -> None:
    """Major units convert to integer minor units deterministically."""
    assert money_to_minor(Decimal(560000)) == 56_000_000
    assert money_to_minor(Decimal("12.345")) == 1235


def test_extraction_json_shape_and_offsets() -> None:
    """Provenance serializes values, rules, and exact Python offsets."""
    listing = _listing(
        text="Цена квартиры — 560 000 zł",
        price=MoneyRange(DecimalRange(Decimal(560000), Decimal(560000)), "PLN"),
        price_span=(16, 26),
    )
    payload = json.loads(build_extraction_json(listing))
    price = payload["apartment_price"]
    assert price == {
        "value": {"min_minor": 56_000_000, "max_minor": 56_000_000, "currency": "PLN"},
        "rule": "rule@v1",
        "confidence": 0.95,
        "source_start": 16,
        "source_end": 26,
    }
    preserved = "Цена квартиры — 560 000 zł"
    assert preserved[16:26] == "560 000 zł"


def test_extraction_json_uses_python_code_point_offsets() -> None:
    """Supplementary and combining characters slice as Python does."""
    text = "Mieszkanie 𝔘𝔫𝔦𝔠𝔬𝔡𝔢 40 m² w Warszawie"  # noqa: RUF001
    area_start = text.index("40 m²")
    listing = _listing(
        text=text,
        area=DecimalRange(Decimal(40), Decimal(40)),
        area_span=(area_start, area_start + len("40 m²")),
    )
    payload = json.loads(build_extraction_json(listing))
    span = payload["area_sqm"]
    assert text[span["source_start"] : span["source_end"]] == "40 m²"
    combining = "Z\u0301ołd"
    offset = combining.index("ł")
    assert combining[offset : offset + 1] == "ł"


def test_excerpt_and_masking_remove_contact_text() -> None:
    """Contact-covered text is omitted from excerpts and masked publicly."""
    text = "Mieszkanie 40 m², tel. +48 601 602 603, @warsaw_sprzedaz"
    phone = "+48 601 602 603"
    handle = "@warsaw_sprzedaz"
    contacts = (
        _contact(text.index(phone), text.index(phone) + len(phone), phone),
        _contact(text.index(handle), text.index(handle) + len(handle), handle),
    )
    excerpt = build_source_text_excerpt(text, contacts)
    masked = build_source_text_public_masked(text, contacts)
    assert phone not in excerpt
    assert handle not in excerpt
    assert "Mieszkanie 40 m²" in excerpt
    assert phone not in masked
    assert handle not in masked
    assert "•••" in masked
    assert "Mieszkanie 40 m²" in masked


def test_excerpt_truncates_to_bound() -> None:
    """Excerpts respect the persisted column bound."""
    text = "x" * 600
    excerpt = build_source_text_excerpt(text, ())
    assert len(excerpt) == 280


def test_fingerprint_and_location_keys_are_deterministic() -> None:
    """Fingerprints and location keys replay identically for equal inputs."""
    first = _listing(text="a", location=" ul. Przykładowa 5 ")
    second = _listing(text="b", location="ul. przykładowa 5")
    assert canonical_fingerprint(first) == canonical_fingerprint(second)
    assert normalized_location_key("UL. PRZYKŁADOWA 5") == normalized_location_key(
        "ul. przykładowa 5",
    )
    assert normalize_location_text("  ul.   Przykładowa  ") == "ul. Przykładowa, Warszawa"
    assert (
        normalize_location_text("ул. Dziekońskiego | Warszawa, Mokotów")
        == "ul. Dziekońskiego, Mokotów, Warszawa"
    )
    assert normalized_location_key(None) == normalized_location_key("")


def test_checkpoint_only_advances_forward() -> None:
    """Checkpoints refuse regressions."""
    checkpoint = RunCheckpoint(last_source_index=4)
    assert checkpoint.advances(5, None).last_source_index == 5
    with pytest.raises(ValueError, match="forward"):
        checkpoint.advances(4, None)


def test_counts_reconcile_every_outcome() -> None:
    """Counts stay consistent with acknowledged outcomes."""
    counts = RunCounts()
    outcome = MessagePersistOutcome(
        external_message_id=1,
        outcome=MessageOutcome.CREATED,
        revision_number=1,
    )
    counts = counts.with_outcome(outcome=outcome, offer_created=True)
    counts = counts.with_outcome(
        outcome=MessagePersistOutcome(
            external_message_id=2,
            outcome=MessageOutcome.UNCHANGED,
            revision_number=1,
        ),
        offer_created=False,
    )
    assert counts == RunCounts(
        seen=2,
        created=1,
        unchanged=1,
        offers=1,
    )


def test_redacted_error_summary_categories() -> None:
    """Error summaries expose class categories, never messages."""
    assert redacted_error_summary(PersistenceBatchError("secret")) == ("PersistenceBatchError")
    assert redacted_error_summary(RunLockHeldError("locked")) == "RunLockHeldError"
    assert redacted_error_summary(ValueError("boom")) == "ValueError"
    assert redacted_error_summary(KeyError("boom")) == "UnclassifiedError"


class FakeStore:
    """Scriptable persistence port double."""

    def __init__(self, fail_on_batch: int | None = None) -> None:
        """Script the failing batch index if any."""
        self.fail_on_batch = fail_on_batch
        self.calls: list[str] = []
        self.batches: list[int] = []
        self._channel = uuid4()
        self._run = uuid4()

    def run_lock(self, source_key: str) -> AbstractAsyncContextManager[None]:
        """Record lock acquisition with a real async context manager."""

        @asynccontextmanager
        async def _lock() -> AsyncIterator[None]:
            self.calls.append(f"lock:{source_key}")
            yield

        return _lock()

    async def ensure_channel(
        self,
        *,
        platform: str,
        external_id: str,
        display_name: str,  # noqa: ARG002
    ) -> UUID:
        """Return one stable fake channel id."""
        self.calls.append(f"channel:{platform}:{external_id}")
        return self._channel

    async def start_run(
        self,
        *,
        channel_id: UUID,  # noqa: ARG002
        mode: RunMode,  # noqa: ARG002
        parser_version: str,  # noqa: ARG002
        source_checksum: str | None,  # noqa: ARG002
        release_sha: str | None,  # noqa: ARG002
    ) -> UUID:
        """Return one stable fake run id."""
        self.calls.append("start_run")
        return self._run

    async def persist_batch(
        self,
        *,
        channel_id: UUID,  # noqa: ARG002
        run_id: UUID,  # noqa: ARG002
        batch: Sequence[tuple[PersistableMessage, int]],
        checkpoint: RunCheckpoint,
        counts: RunCounts,
    ) -> tuple[Sequence[MessagePersistOutcome], RunCheckpoint, RunCounts, int]:
        """Acknowledge the batch or fail it as scripted."""
        self.batches.append(len(batch))
        if self.fail_on_batch == len(self.batches):
            message = "injected"
            raise PersistenceBatchError(message)
        outcome = MessagePersistOutcome(
            external_message_id=batch[0][0].raw.external_message_id,
            outcome=MessageOutcome.CREATED,
            revision_number=1,
        )
        new_checkpoint = checkpoint.advances(batch[-1][1], None)
        new_counts = counts.with_outcome(outcome=outcome, offer_created=True)
        return (outcome,), new_checkpoint, new_counts, 1

    async def persist_live_upsert(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        message: PersistableMessage,
        checkpoint: RunCheckpoint,
        counts: RunCounts,
        advance_checkpoint: bool,
    ) -> tuple[MessagePersistOutcome, RunCheckpoint, RunCounts, int]:
        """Acknowledge one live upsert or fail as scripted."""
        batch = ((message, message.raw.external_message_id),)
        outcomes, new_checkpoint, new_counts, offers = await self.persist_batch(
            channel_id=channel_id,
            run_id=run_id,
            batch=batch,
            checkpoint=checkpoint,
            counts=counts,
        )
        if not advance_checkpoint:
            new_checkpoint = checkpoint
        return outcomes[0], new_checkpoint, new_counts, offers

    async def mark_source_deleted(
        self,
        *,
        channel_id: UUID,  # noqa: ARG002
        external_message_ids: Sequence[int],
    ) -> Sequence[SourceDeletionOutcome]:
        """Record delete calls without durable storage."""
        self.calls.append(f"delete:{len(external_message_ids)}")
        return tuple(
            SourceDeletionOutcome(
                external_message_id=external_id,
                outcome=DeletionOutcomeKind.MISSING,
                offers_hidden=0,
            )
            for external_id in external_message_ids
        )

    async def persist_owner_ai_listing(
        self,
        *,
        source_message_revision_id: UUID,
        listing: ListingCandidate,
    ) -> UUID:
        """Stub owner AI listing persistence for protocol conformance."""
        _ = (source_message_revision_id, listing)
        return uuid4()

    async def finish_run(
        self,
        *,
        run_id: UUID,  # noqa: ARG002
        status: RunStatus,
        counts: RunCounts,  # noqa: ARG002
        checkpoint: RunCheckpoint,  # noqa: ARG002
        error_summary: str | None,
    ) -> None:
        """Record the terminal status."""
        self.calls.append(f"finish:{status.value}:{error_summary}")


def _identity() -> SourceIdentity:
    """Return one stable channel identity."""
    return SourceIdentity(
        platform=SourcePlatform.TELEGRAM,
        channel_id="2180077318",
        channel_name="El Estate",
        channel_type="public_channel",
    )


def _service(store: FakeStore, batch_size: int = 2) -> PersistHistoricalIngestion:
    """Compose the orchestrator over the fake store."""
    return PersistHistoricalIngestion(store=store, batch_size=batch_size)


async def test_service_batches_locks_and_finishes() -> None:
    """The orchestrator locks, batches, and records success."""
    store = FakeStore()
    messages = [PersistableMessage(raw=_raw(message_id=i), extraction=None) for i in range(1, 6)]
    summary = await _service(store)(
        channel=_identity(),
        messages=messages,
        metadata=RunMetadata(parser_version="test@1"),
    )
    assert store.batches == [2, 2, 1]
    assert store.calls[0] == "lock:telegram:2180077318"
    assert store.calls[-1] == "finish:succeeded:None"
    assert summary.counts.seen == 3
    assert summary.status is RunStatus.SUCCEEDED


async def test_service_failure_keeps_last_checkpoint() -> None:
    """A failing batch marks the run failed and re-raises."""
    store = FakeStore(fail_on_batch=2)
    messages = [PersistableMessage(raw=_raw(message_id=i), extraction=None) for i in range(1, 5)]
    with pytest.raises(PersistenceBatchError):
        await _service(store)(
            channel=_identity(),
            messages=messages,
            metadata=RunMetadata(parser_version="test@1"),
        )
    assert store.batches == [2, 2]
    assert store.calls[-1] == "finish:failed:PersistenceBatchError"


def _listing(
    text: str,
    *,
    price: MoneyRange | None = None,
    price_span: tuple[int, int] | None = None,
    area: DecimalRange | None = None,
    area_span: tuple[int, int] | None = None,
    location: str | None = None,
    contacts: tuple[ContactSpan, ...] = (),
) -> ListingCandidate:
    """Build one minimal listing candidate for provenance tests."""

    def valued(value: object, span: tuple[int, int] | None) -> ExtractedValue[object] | None:
        if value is None or span is None:
            return None
        return ExtractedValue(
            value=value,
            provenance=_provenance(span[0], span[1]),
        )

    location_value = None
    if location is not None:
        location_value = ExtractedValue[str](
            value=location,
            provenance=_provenance(0, min(len(text), len(location))),
        )
    return ListingCandidate(
        source_message_id=1,
        source_checksum="a" * 64,
        parser_version="test@1",
        content_type=ExtractedValue(
            value=ContentType.UNIT,
            provenance=_provenance(0, min(9, len(text))),
        ),
        market_type=None,
        property_type=None,
        location=location_value,
        district=None,
        development_name=None,
        apartment_price=cast(
            "ExtractedValue[MoneyRange] | None",
            valued(price, price_span),
        ),
        parking_price=None,
        storage_price=None,
        parking_included_in_price=None,
        storage_included_in_price=None,
        area_sqm=cast(
            "ExtractedValue[DecimalRange] | None",
            valued(area, area_span),
        ),
        rooms=None,
        floor=None,
        delivery=None,
        map_links=(),
        contacts=contacts,
    )


def test_run_metadata_defaults() -> None:
    """Run metadata defaults to historical mode without optional inputs."""
    metadata = RunMetadata(parser_version="p@1")
    assert metadata.mode.value == "historical"
    assert metadata.source_checksum is None
    assert metadata.release_sha is None
