"""Unit tests for area backfill reporting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self, cast
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.catalog.infrastructure.models import OfferRow
    from wef_backend.features.ingestion.infrastructure.models import (
        SourceChannelRow,
        SourceMessageRow,
    )

from wef_backend import backfill_area_command
from wef_backend.backfill_area_command import build_parser
from wef_backend.features.ingestion.infrastructure.area_backfill import (
    AreaBackfillSummary,
    _apply_area,
    _process_backfill_row,
    backfill_areas,
)

_AREA_TEXT = (
    "🏙 2-комнатная квартира | #Mokotów\n\n"
    "📍ul. Puławska 50, Mokotów\n"
    "📐 48 m² | 3/8 этаж | #2_комнаты\n\n"
    "💰 Цена — 750 000 zł"
)
_NO_AREA_TEXT = (
    "🏙 2-комнатная квартира | #Wola\n\n"
    "📍ul. Kasprzaka 12, Wola\n"
    "3/8 этаж | #2_комнаты\n\n"
    "💰 Цена — 750 000 zł"
)

_BackfillRow = tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, datetime]


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


def _backfill_row(*, offer: SimpleNamespace, text: str) -> _BackfillRow:
    return (
        offer,
        _source_message(text=text),
        _source_channel(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def _offer_row(*, area_min_sqm: Decimal | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), area_min_sqm=area_min_sqm, area_max_sqm=area_min_sqm)


@pytest.mark.asyncio
async def test_backfill_areas_empty_database() -> None:
    """An empty database returns zeroed aggregate counts."""
    summary = await backfill_areas(
        _EmptySessionFactory(),  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )
    assert summary == AreaBackfillSummary(
        total=0,
        filled=0,
        unchanged=0,
        skipped_already_known=0,
        failures=0,
        parser_version=summary.parser_version,
    )


@pytest.mark.asyncio
async def test_backfill_areas_dry_run_fills_emoji_measurement() -> None:
    """📐 measurements count as filled without mutating the offer in dry-run."""
    offer = _offer_row()
    factory = _BackfillSessionFactory([_backfill_row(offer=offer, text=_AREA_TEXT)])

    summary = await backfill_areas(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.filled == 1
    assert offer.area_min_sqm is None


@pytest.mark.asyncio
async def test_backfill_areas_apply_persists_range() -> None:
    """Apply mode writes both area bounds from a 📐 measurement."""
    offer = _offer_row()
    factory = _BackfillSessionFactory([_backfill_row(offer=offer, text=_AREA_TEXT)])

    summary = await backfill_areas(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=True,
    )

    assert summary.filled == 1
    assert offer.area_min_sqm == Decimal(48)
    assert offer.area_max_sqm == Decimal(48)


@pytest.mark.asyncio
async def test_backfill_areas_unchanged_when_no_area() -> None:
    """Text without an area measurement is counted as unchanged."""
    offer = _offer_row()
    factory = _BackfillSessionFactory([_backfill_row(offer=offer, text=_NO_AREA_TEXT)])

    summary = await backfill_areas(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.unchanged == 1
    assert summary.filled == 0


@pytest.mark.asyncio
async def test_backfill_areas_skips_already_known() -> None:
    """Offers that already have area are counted as skipped, not overwritten."""
    offer = _offer_row(area_min_sqm=Decimal(30))
    factory = _BackfillSessionFactory([_backfill_row(offer=offer, text=_AREA_TEXT)])
    counts: dict[str, int] = {
        "total": 0,
        "filled": 0,
        "unchanged": 0,
        "skipped_already_known": 0,
        "failures": 0,
    }
    await _process_backfill_row(
        cast("async_sessionmaker[AsyncSession]", factory),
        counts=counts,
        offer=cast("OfferRow", offer),
        message=cast("SourceMessageRow", _source_message(text=_AREA_TEXT)),
        channel=cast("SourceChannelRow", _source_channel()),
        apply=True,
    )

    assert counts["skipped_already_known"] == 1
    assert offer.area_min_sqm == Decimal(30)


@pytest.mark.asyncio
async def test_backfill_areas_counts_failures() -> None:
    """Non-listing source text increments the failure counter."""
    offer = _offer_row()
    factory = _BackfillSessionFactory(
        [_backfill_row(offer=offer, text="random channel notice")],
    )

    summary = await backfill_areas(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.failures == 1


@pytest.mark.asyncio
async def test_apply_area_noops_when_offer_missing() -> None:
    """Missing offers are ignored during apply."""
    factory = _BackfillSessionFactory([])
    await _apply_area(
        cast("async_sessionmaker[AsyncSession]", factory),
        uuid4(),
        Decimal(40),
        Decimal(40),
    )


def test_backfill_area_cli_parser_accepts_apply_flag() -> None:
    """The operator CLI exposes dry-run by default and optional --apply."""
    args = build_parser().parse_args(["--limit", "25", "--apply"])
    assert args.limit == 25
    assert args.apply is True


@pytest.mark.asyncio
async def test_backfill_area_command_run_disposes_engine(
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
    ) -> AreaBackfillSummary:
        return AreaBackfillSummary(
            total=0,
            filled=0,
            unchanged=0,
            skipped_already_known=0,
            failures=0,
            parser_version="test",
        )

    monkeypatch.setattr(
        backfill_area_command,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://example/unused"),
    )
    monkeypatch.setattr(
        backfill_area_command,
        "create_database_resources",
        lambda _url: _Database(),
    )
    monkeypatch.setattr(backfill_area_command, "backfill_areas", _fake_backfill)
    payload = await backfill_area_command.run(limit=10, apply=False)
    assert payload["total"] == 0
    assert disposed is True


def test_backfill_area_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI stdout emits one JSON summary payload."""

    async def _fake_run(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        assert limit == 50
        assert apply is True
        return {
            "total": 50,
            "filled": 40,
            "unchanged": 10,
            "skipped_already_known": 0,
            "failures": 0,
            "parser_version": "test",
        }

    monkeypatch.setattr(backfill_area_command, "run", _fake_run)
    backfill_area_command.main(["--limit", "50", "--apply"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["filled"] == 40


def test_backfill_area_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI failures exit with code 2."""

    async def _boom(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        _ = (limit, apply)
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(backfill_area_command, "run", _boom)
    with pytest.raises(SystemExit) as exited:
        backfill_area_command.main([])
    assert exited.value.code == 2
