"""Unit tests for market-type backfill reporting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
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

from wef_backend import backfill_market_type_command
from wef_backend.backfill_market_type_command import build_parser
from wef_backend.features.ingestion.infrastructure import market_type_backfill as backfill_module
from wef_backend.features.ingestion.infrastructure.market_type_backfill import (
    MarketTypeBackfillSummary,
    _apply_market_type,
    _process_backfill_row,
    backfill_market_types,
)

# Texts that trigger implicit market_type signals (e2-v12+)
_PRIMARY_TEXT = (
    "🏙 2-комнатная квартира | #Mokotów\n\n"
    "📍ul. Puławska 50, Mokotów\n"
    "📐 48 m² | 3/8 этаж | #2_комнаты\n\n"
    "Новостройка, квартира ещё не была заселена.\n\n"
    "💰 Цена — 750 000 zł"
)
_SECONDARY_TEXT = (
    "🏙 3-комнатная квартира | #Wola\n\n"
    "📍ul. Kasprzaka 12, Wola\n"
    "📐 65 m² | 5/10 этаж | #3_комнаты\n\n"
    "Продаётся от собственника, без посредников.\n\n"
    "💰 Цена — 980 000 zł"
)
_NO_SIGNAL_TEXT = (
    "🏙 2-комнатная квартира | #PragaPółnoc\n\n"
    "📍ul. Markowska 5, Praga-Północ\n"
    "📐 47 m² | 2/7 этаж\n\n"
    "Современный жилой комплекс 2019 года.\n\n"
    "💰 Цена — 899 000 zł"
)


# ---------------------------------------------------------------------------
# Minimal session-factory fakes (mirrors property_type_backfill tests)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _offer_row(*, market_type: str = "unknown") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), market_type=market_type)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_market_types_empty_database() -> None:
    """An empty database returns zeroed aggregate counts."""
    summary = await backfill_market_types(
        _EmptySessionFactory(),  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )
    assert summary == MarketTypeBackfillSummary(
        total=0,
        primary=0,
        secondary=0,
        unknown=0,
        changed=0,
        unchanged=0,
        skipped_already_known=0,
        failures=0,
        parser_version=summary.parser_version,
    )


@pytest.mark.asyncio
async def test_backfill_market_types_detects_primary_keyword() -> None:
    """'Новостройка' in body text infers PRIMARY and counts as changed."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_PRIMARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.primary == 1
    assert summary.changed == 1
    assert summary.unchanged == 0
    assert offer.market_type == "unknown"  # dry-run — not mutated


@pytest.mark.asyncio
async def test_backfill_market_types_detects_secondary_keyword() -> None:
    """'от собственника' in body text infers SECONDARY and counts as changed."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_SECONDARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.secondary == 1
    assert summary.changed == 1


@pytest.mark.asyncio
async def test_backfill_market_types_unchanged_when_no_signal() -> None:
    """Text with no market signal stays unknown and is not written."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_NO_SIGNAL_TEXT)]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.unknown == 1
    assert summary.changed == 0
    assert summary.unchanged == 1


@pytest.mark.asyncio
async def test_backfill_market_types_apply_persists_primary() -> None:
    """Apply mode writes PRIMARY when the keyword fires."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_PRIMARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=True,
    )

    assert summary.changed == 1
    assert offer.market_type == "primary"


@pytest.mark.asyncio
async def test_backfill_market_types_apply_persists_secondary() -> None:
    """Apply mode writes SECONDARY when the keyword fires."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_SECONDARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=True,
    )

    assert offer.market_type == "secondary"


@pytest.mark.asyncio
async def test_backfill_market_types_skips_already_known() -> None:
    """Offers with a known market_type are counted as skipped, not changed."""
    offer = _offer_row(market_type="primary")
    rows = [_backfill_row(offer=offer, text=_SECONDARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    counts: dict[str, int] = {
        "total": 0,
        "primary": 0,
        "secondary": 0,
        "unknown": 0,
        "changed": 0,
        "unchanged": 0,
        "skipped_already_known": 0,
        "failures": 0,
    }
    await _process_backfill_row(
        cast("async_sessionmaker[AsyncSession]", factory),
        counts=counts,
        offer=cast("OfferRow", offer),
        message=cast("SourceMessageRow", _source_message(text=_SECONDARY_TEXT)),
        channel=cast("SourceChannelRow", _source_channel()),
        apply=False,
    )

    assert counts["skipped_already_known"] == 1
    assert counts["changed"] == 0
    assert offer.market_type == "primary"  # not mutated


@pytest.mark.asyncio
async def test_backfill_market_types_counts_failures() -> None:
    """Non-listing source text increments the failure counter."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text="random channel notice")]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.failures == 1


@pytest.mark.asyncio
async def test_backfill_market_types_respects_limit() -> None:
    """The limit parameter caps the number of processed offers."""
    rows = [_backfill_row(offer=_offer_row(), text=_PRIMARY_TEXT) for _ in range(5)]
    factory = _BackfillSessionFactory(rows)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=2,
        apply=False,
    )

    assert summary.total == 2


@pytest.mark.asyncio
async def test_backfill_market_types_survives_row_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected row failures are counted without aborting the run."""
    offer = _offer_row()
    rows = [_backfill_row(offer=offer, text=_PRIMARY_TEXT)]
    factory = _BackfillSessionFactory(rows)

    async def _boom(*_args: object, **_kwargs: object) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(backfill_module, "_process_backfill_row", _boom)

    summary = await backfill_market_types(
        cast("async_sessionmaker[AsyncSession]", factory),
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.failures == 1


@pytest.mark.asyncio
async def test_apply_market_type_noops_when_offer_missing() -> None:
    """Missing offers are ignored during apply."""
    factory = _BackfillSessionFactory([])

    await _apply_market_type(
        cast("async_sessionmaker[AsyncSession]", factory),
        uuid4(),
        "primary",
    )  # must not raise


def test_backfill_market_type_cli_parser_accepts_apply_flag() -> None:
    """The operator CLI exposes dry-run by default and optional --apply."""
    args = build_parser().parse_args(["--limit", "500", "--apply"])
    assert args.limit == 500
    assert args.apply is True


@pytest.mark.asyncio
async def test_backfill_market_type_command_run_disposes_engine(
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
    ) -> MarketTypeBackfillSummary:
        return MarketTypeBackfillSummary(
            total=0,
            primary=0,
            secondary=0,
            unknown=0,
            changed=0,
            unchanged=0,
            skipped_already_known=0,
            failures=0,
            parser_version="test",
        )

    monkeypatch.setattr(
        backfill_market_type_command,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://example/unused"),
    )
    monkeypatch.setattr(
        backfill_market_type_command,
        "create_database_resources",
        lambda _url: _Database(),
    )
    monkeypatch.setattr(
        backfill_market_type_command,
        "backfill_market_types",
        _fake_backfill,
    )
    payload = await backfill_market_type_command.run(limit=10, apply=False)
    assert payload["total"] == 0
    assert disposed is True


def test_backfill_market_type_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI stdout emits one JSON summary payload."""

    async def _fake_run(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        assert limit == 100
        assert apply is True
        return {
            "total": 100,
            "primary": 60,
            "secondary": 25,
            "unknown": 15,
            "changed": 85,
            "unchanged": 15,
            "skipped_already_known": 0,
            "failures": 0,
            "parser_version": "test",
        }

    monkeypatch.setattr(backfill_market_type_command, "run", _fake_run)
    backfill_market_type_command.main(["--limit", "100", "--apply"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] == 85
    assert payload["parser_version"] == "test"


def test_backfill_market_type_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI failures exit with code 2."""

    async def _boom(*, limit: int | None, apply: bool) -> dict[str, int | str]:
        _ = (limit, apply)
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(backfill_market_type_command, "run", _boom)
    with pytest.raises(SystemExit) as exited:
        backfill_market_type_command.main([])
    assert exited.value.code == 2
