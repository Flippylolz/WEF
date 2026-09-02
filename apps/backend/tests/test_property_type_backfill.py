"""Unit tests for property-type backfill reporting."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self, cast
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.infrastructure.models import (
        SourceChannelRow,
        SourceMessageRow,
    )

from wef_backend import backfill_property_type_command
from wef_backend.backfill_property_type_command import build_parser
from wef_backend.features.ingestion.infrastructure import property_type_backfill as backfill_module
from wef_backend.features.ingestion.infrastructure.property_type_backfill import (
    PropertyTypeBackfillSummary,
    _row_to_raw,
    backfill_property_types,
)

_APARTMENT_TEXT = "🏙 Kupno | Rynek wtórny\nMieszkanie 2-pokojowe\n💰 Cena: 900 000 zł"
_HOUSE_TEXT = "🏙 Kupno | Rynek wtórny\nDom jednorodzinny w Wilanowie\n💰 Cena: 2 500 000 zł"
_SEMI_DETACHED_TEXT = "🏙 Kupno | Rynek wtórny\nBliźniak w zielonej okolicy\n💰 Cena: 1 800 000 zł"
_CONFLICT_TEXT = (
    "🏙 Kupno | Rynek wtórny\n"
    "Mieszkanie w bloku i dom jednorodzinny na jednej działce\n"
    "💰 Cena: 1 000 000 zł"
)

_BackfillRow = tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]


class _EmptyResult:
    def all(self) -> list[object]:
        return []


class _EmptySession:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, _: object) -> _EmptyResult:
        return _EmptyResult()


class _EmptySessionFactory:
    def __call__(self) -> _EmptySession:
        return _EmptySession()


class _QueryResult:
    def __init__(self, rows: Sequence[_BackfillRow]) -> None:
        self._rows = list(rows)

    def all(self) -> list[_BackfillRow]:
        return self._rows


class _ReadSession:
    def __init__(self, rows: Sequence[_BackfillRow]) -> None:
        self._rows = list(rows)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, _: object) -> _QueryResult:
        return _QueryResult(self._rows)


class _WriteSession:
    def __init__(self, offers: dict[UUID, SimpleNamespace]) -> None:
        self._offers = offers

    async def get(self, _: object, offer_id: UUID) -> SimpleNamespace | None:
        return self._offers.get(offer_id)


class _WriteContext:
    def __init__(self, offers: dict[UUID, SimpleNamespace]) -> None:
        self._offers = offers

    async def __aenter__(self) -> _WriteSession:
        return _WriteSession(self._offers)

    async def __aexit__(self, *_: object) -> None:
        return None


class _BackfillSessionFactory:
    def __init__(self, rows: Sequence[_BackfillRow]) -> None:
        self._rows = list(rows)
        self._offers = {row[0].id: row[0] for row in self._rows}

    def __call__(self) -> _ReadSession:
        return _ReadSession(self._rows)

    def begin(self) -> _WriteContext:
        return _WriteContext(self._offers)


def _source_message(*, text: str) -> SimpleNamespace:
    return SimpleNamespace(
        raw_payload_json={"id": 42},
        external_message_id=42,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        edited_at=None,
        message_type="message",
        text_original=text,
        raw_checksum="a" * 64,
    )


def _source_channel() -> SimpleNamespace:
    return SimpleNamespace(external_id="fixture-channel", display_name="Fixture")


def _offer_row(*, property_type: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), property_type=property_type)


@pytest.mark.asyncio
async def test_backfill_property_types_reports_empty_summary() -> None:
    """An empty database returns zeroed aggregate counts."""
    summary = await backfill_property_types(
        _EmptySessionFactory(),  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )
    assert summary == PropertyTypeBackfillSummary(
        total=0,
        apartment=0,
        house=0,
        semi_detached=0,
        unknown=0,
        conflicts=0,
        changed=0,
        unchanged=0,
        failures=0,
        parser_version=summary.parser_version,
    )


def test_backfill_cli_parser_accepts_apply_flag() -> None:
    """The operator CLI exposes dry-run by default and optional apply."""
    args = build_parser().parse_args(["--limit", "10", "--apply"])
    assert args.limit == 10
    assert args.apply is True


def test_row_to_raw_builds_replayable_message() -> None:
    """Stored source rows rebuild one replayable raw message."""
    message = SimpleNamespace(
        raw_payload_json={"id": 42},
        external_message_id=42,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        edited_at=None,
        message_type="message",
        text_original="Mieszkanie 2-pokojowe",
        raw_checksum="a" * 64,
    )
    channel = SimpleNamespace(external_id="fixture-channel", display_name="Fixture")

    raw = _row_to_raw(
        message=cast("SourceMessageRow", message),
        channel=cast("SourceChannelRow", channel),
    )

    assert raw.external_message_id == 42
    assert raw.text == "Mieszkanie 2-pokojowe"
    assert raw.source.channel_id == "fixture-channel"


def test_payload_for_message_falls_back_to_external_id() -> None:
    """Missing payloads still rebuild one replayable message envelope."""
    payload = backfill_module._payload_for_message(payload="", external_message_id=99)  # noqa: SLF001
    assert payload == {"id": 99}


def test_payload_for_message_parses_json_string() -> None:
    """String payloads decode before replay."""
    payload = backfill_module._payload_for_message(  # noqa: SLF001
        payload='{"id": 7, "text": "hello"}',
        external_message_id=7,
    )
    assert payload == {"id": 7, "text": "hello"}


def test_payload_for_message_returns_mapping() -> None:
    """Stored JSON objects pass through unchanged."""
    payload = backfill_module._payload_for_message(payload={"id": 5}, external_message_id=5)  # noqa: SLF001
    assert payload == {"id": 5}


def test_payload_for_message_ignores_non_object_payloads() -> None:
    """Non-object payloads fall back to the external message id."""
    payload = backfill_module._payload_for_message(payload=[1, 2, 3], external_message_id=11)  # noqa: SLF001
    assert payload == {"id": 11}


@pytest.mark.asyncio
async def test_backfill_property_types_counts_semi_detached_offers() -> None:
    """Semi-detached extraction increments the dedicated counter."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text=_SEMI_DETACHED_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=1,
        apply=False,
    )

    assert summary.semi_detached == 1
    assert summary.changed == 1


@pytest.mark.asyncio
async def test_row_to_raw_rejects_non_object_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Frozen payloads must remain JSON objects for replay."""
    monkeypatch.setattr(backfill_module, "freeze_json", lambda _payload: [1, 2, 3])
    message = _source_message(text=_APARTMENT_TEXT)

    with pytest.raises(TypeError, match="source message payload must freeze as an object"):
        backfill_module._row_to_raw(  # noqa: SLF001
            message=cast("SourceMessageRow", message),
            channel=cast("SourceChannelRow", _source_channel()),
        )


@pytest.mark.asyncio
async def test_backfill_property_types_dry_run_counts_changed_offers() -> None:
    """Dry-run reports changed values without persisting them."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text=_APARTMENT_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.apartment == 1
    assert summary.changed == 1
    assert summary.unchanged == 0
    assert offer.property_type == "unknown"


@pytest.mark.asyncio
async def test_backfill_property_types_apply_persists_changed_values() -> None:
    """Apply mode writes only changed property types."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text=_HOUSE_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=True,
    )

    assert summary.house == 1
    assert summary.changed == 1
    assert offer.property_type == "house"


@pytest.mark.asyncio
async def test_backfill_property_types_counts_unchanged_offers() -> None:
    """Already-correct values are counted as unchanged."""
    offer = _offer_row(property_type="apartment")
    rows = [(offer, _source_message(text=_APARTMENT_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.apartment == 1
    assert summary.changed == 0
    assert summary.unchanged == 1


@pytest.mark.asyncio
async def test_backfill_property_types_counts_conflicts() -> None:
    """Conflicting extraction evidence increments the conflict counter."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text=_CONFLICT_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.conflicts == 1
    assert summary.unknown == 1


@pytest.mark.asyncio
async def test_backfill_property_types_counts_extraction_failures() -> None:
    """Non-listing source text increments the failure counter."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text="random channel notice"), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.failures == 1


@pytest.mark.asyncio
async def test_backfill_property_types_survives_row_processing_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected row failures are counted without aborting the run."""
    offer = _offer_row(property_type="unknown")
    rows = [(offer, _source_message(text=_APARTMENT_TEXT), _source_channel())]
    factory = _BackfillSessionFactory(rows)

    async def _boom(*_args: object, **_kwargs: object) -> None:
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(backfill_module, "_process_backfill_row", _boom)

    summary = await backfill_property_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.failures == 1


@pytest.mark.asyncio
async def test_apply_property_type_noops_when_offer_missing() -> None:
    """Missing offers are ignored during apply."""
    factory = _BackfillSessionFactory([])

    await backfill_module._apply_property_type(  # noqa: SLF001
        cast("async_sessionmaker[AsyncSession]", factory),
        uuid4(),
        "apartment",
    )


@pytest.mark.asyncio
async def test_backfill_property_type_command_run_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The operator CLI disposes database resources after one run."""
    disposed = False

    class _Engine:
        async def dispose(self) -> None:
            nonlocal disposed
            disposed = True

    class _Database:
        session_factory = object()
        engine = _Engine()

    async def _fake_backfill(
        *_args: object,
        **_kwargs: object,
    ) -> PropertyTypeBackfillSummary:
        return PropertyTypeBackfillSummary(
            total=0,
            apartment=0,
            house=0,
            semi_detached=0,
            unknown=0,
            conflicts=0,
            changed=0,
            unchanged=0,
            failures=0,
            parser_version="test",
        )

    monkeypatch.setattr(
        backfill_property_type_command,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://example/unused"),
    )
    monkeypatch.setattr(
        backfill_property_type_command,
        "create_database_resources",
        lambda _url: _Database(),
    )
    monkeypatch.setattr(
        backfill_property_type_command,
        "backfill_property_types",
        _fake_backfill,
    )
    payload = await backfill_property_type_command.run(limit=10, apply=False)
    assert payload["total"] == 0
    assert disposed is True


def test_backfill_property_type_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI stdout emits one JSON summary payload."""

    async def _fake_run(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        assert limit == 25
        assert apply is True
        return {
            "total": 25,
            "apartment": 10,
            "house": 8,
            "semi_detached": 2,
            "unknown": 5,
            "conflicts": 1,
            "changed": 12,
            "unchanged": 13,
            "failures": 0,
            "parser_version": "test",
        }

    monkeypatch.setattr(backfill_property_type_command, "run", _fake_run)
    backfill_property_type_command.main(["--limit", "25", "--apply"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] == 12
    assert payload["parser_version"] == "test"


def test_backfill_property_type_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI failures exit with code 2."""

    async def _boom(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        _ = (limit, apply)
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(backfill_property_type_command, "run", _boom)
    with pytest.raises(SystemExit) as exited:
        backfill_property_type_command.main([])
    assert exited.value.code == 2
