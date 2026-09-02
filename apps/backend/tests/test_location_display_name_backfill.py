"""Unit tests for location display-name backfill reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self, cast
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence


from wef_backend import backfill_location_display_name_command
from wef_backend.backfill_location_display_name_command import build_parser
from wef_backend.features.ingestion.infrastructure import (
    location_display_name_backfill as backfill_module,
)
from wef_backend.features.ingestion.infrastructure.location_display_name_backfill import (
    LocationDisplayNameBackfillSummary,
    _LocationSourceBackfillRow,
    _newest_primary_source_rows,
    backfill_location_display_names,
)

_CYRILLIC_LOCATION_TEXT = "Покупка | Квартира\n📍 Wola | ул. Konstruktorska\nЦена: 850 000 zł"  # noqa: RUF001
_CLEAN_LOCATION_TEXT = "Покупка | Квартира\n📍 ul. Przykładowa 1, Miasto Testowe\nЦена: 850 000 zł"  # noqa: RUF001
_NO_LOCATION_TEXT = "Покупка | Квартира\nЦена: 850 000 zł"  # noqa: RUF001

_BackfillRow = tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, datetime]


class _ScalarResult:
    def __init__(self, values: Sequence[UUID]) -> None:
        self._values = list(values)

    def __iter__(self) -> iter[UUID]:
        return iter(self._values)


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

    async def scalars(self, _: object) -> _ScalarResult:
        return _ScalarResult([])


class _EmptySessionFactory:
    def __call__(self) -> _EmptySession:
        return _EmptySession()


class _QueryResult:
    def __init__(self, rows: Sequence[_BackfillRow]) -> None:
        self._rows = list(rows)

    def all(self) -> list[_BackfillRow]:
        return self._rows


class _ReadSession:
    def __init__(
        self,
        rows: Sequence[_BackfillRow],
        *,
        verified_location_ids: Sequence[UUID] = (),
    ) -> None:
        self._rows = list(rows)
        self._verified_location_ids = list(verified_location_ids)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, _: object) -> _QueryResult:
        return _QueryResult(self._rows)

    async def scalars(self, _: object) -> _ScalarResult:
        return _ScalarResult(self._verified_location_ids)


class _WriteSession:
    def __init__(self, locations: dict[UUID, SimpleNamespace]) -> None:
        self._locations = locations

    async def get(self, _: object, location_id: UUID) -> SimpleNamespace | None:
        return self._locations.get(location_id)


class _WriteContext:
    def __init__(self, locations: dict[UUID, SimpleNamespace]) -> None:
        self._locations = locations

    async def __aenter__(self) -> _WriteSession:
        return _WriteSession(self._locations)

    async def __aexit__(self, *_: object) -> None:
        return None


class _BackfillSessionFactory:
    def __init__(
        self,
        rows: Sequence[_BackfillRow],
        *,
        verified_location_ids: Sequence[UUID] = (),
    ) -> None:
        self._rows = list(rows)
        self._verified_location_ids = list(verified_location_ids)
        self._locations = {row[0].id: row[0] for row in self._rows}

    def __call__(self) -> _ReadSession:
        return _ReadSession(self._rows, verified_location_ids=self._verified_location_ids)

    def begin(self) -> _WriteContext:
        return _WriteContext(self._locations)


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


def _location_row(
    *,
    display_name: str,
    normalized_address_hash: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        display_name=display_name,
        display_address=display_name,
        normalized_address_hash=normalized_address_hash or uuid4().hex,
    )


def _backfill_row(
    *,
    location: SimpleNamespace,
    text: str,
    source_created_at: datetime | None = None,
) -> _BackfillRow:
    created_at = source_created_at or datetime(2026, 1, 1, tzinfo=UTC)
    return (
        location,
        _source_message(text=text),
        _source_channel(),
        created_at,
    )


@pytest.mark.asyncio
async def test_backfill_location_display_names_reports_empty_summary() -> None:
    """An empty database returns zeroed aggregate counts."""
    summary = await backfill_location_display_names(
        _EmptySessionFactory(),  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )
    assert summary == LocationDisplayNameBackfillSummary(
        total=0,
        changed=0,
        unchanged=0,
        skipped_verified=0,
        failures=0,
    )


def test_newest_primary_source_rows_keeps_latest_revision_per_location() -> None:
    """Multiple primary revisions for one location collapse to the newest source."""
    location = _location_row(display_name="Wola | ул. Old Street")
    older = _LocationSourceBackfillRow(
        location=cast("SimpleNamespace", location),
        message=cast("SimpleNamespace", _source_message(text=_CYRILLIC_LOCATION_TEXT)),
        channel=cast("SimpleNamespace", _source_channel()),
        source_created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = _LocationSourceBackfillRow(
        location=cast("SimpleNamespace", location),
        message=cast(
            "SimpleNamespace",
            _source_message(
                text="Покупка | Квартира\n📍 Wola | ул. Newer Street\nЦена: 850 000 zł",  # noqa: RUF001
            ),
        ),
        channel=cast("SimpleNamespace", _source_channel()),
        source_created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    selected = _newest_primary_source_rows([older, newer])
    assert len(selected) == 1
    assert "ул. Newer Street" in selected[0].message.text_original


@pytest.mark.asyncio
async def test_backfill_location_display_names_dry_run_counts_changed_locations() -> None:
    """Dry-run reports changed rows without persisting display fields."""
    location = _location_row(display_name="Wola | ул. Konstruktorska")
    factory = _BackfillSessionFactory(
        [_backfill_row(location=location, text=_CYRILLIC_LOCATION_TEXT)],
    )

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.changed == 1
    assert summary.unchanged == 0
    assert summary.failures == 0
    assert location.display_name == "Wola | ул. Konstruktorska"


@pytest.mark.asyncio
async def test_backfill_location_display_names_apply_persists_changed_values() -> None:
    """Apply updates display_name and display_address while preserving the hash."""
    location = _location_row(display_name="Wola | ул. Konstruktorska")
    expected_hash = location.normalized_address_hash
    factory = _BackfillSessionFactory(
        [_backfill_row(location=location, text=_CYRILLIC_LOCATION_TEXT)],
    )

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=True,
    )

    assert summary.changed == 1
    assert location.display_name == "ul. Konstruktorska, Wola, Warszawa"
    assert location.display_address == "ul. Konstruktorska, Wola, Warszawa"
    assert location.normalized_address_hash == expected_hash


@pytest.mark.asyncio
async def test_backfill_location_display_names_counts_unchanged_locations() -> None:
    """Already canonical display names stay in the unchanged bucket."""
    location = _location_row(display_name="ul. Przykładowa 1, Miasto Testowe")
    factory = _BackfillSessionFactory([_backfill_row(location=location, text=_CLEAN_LOCATION_TEXT)])

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.changed == 0
    assert summary.unchanged == 1


@pytest.mark.asyncio
async def test_backfill_location_display_names_skips_operator_verified_locations() -> None:
    """Owner-verified locations with operator lineage are excluded from totals."""
    location = _location_row(display_name="Owner curated name")
    factory = _BackfillSessionFactory(
        [_backfill_row(location=location, text=_CYRILLIC_LOCATION_TEXT)],
        verified_location_ids=[location.id],
    )

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )

    assert summary.total == 0
    assert summary.skipped_verified == 1
    assert location.display_name == "Owner curated name"


@pytest.mark.asyncio
async def test_backfill_location_display_names_counts_extraction_failures() -> None:
    """Rows without replayable location evidence count as failures."""
    location = _location_row(display_name="Unknown location")
    factory = _BackfillSessionFactory([_backfill_row(location=location, text=_NO_LOCATION_TEXT)])

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.failures == 1
    assert summary.changed == 0


@pytest.mark.asyncio
async def test_backfill_location_display_names_is_idempotent_after_apply() -> None:
    """A second dry-run after apply reports zero changed rows."""
    location = _location_row(display_name="Wola | ул. Konstruktorska")
    factory = _BackfillSessionFactory(
        [_backfill_row(location=location, text=_CYRILLIC_LOCATION_TEXT)],
    )

    await backfill_location_display_names(factory, limit=None, apply=True)  # type: ignore[arg-type]
    summary = await backfill_location_display_names(factory, limit=None, apply=False)  # type: ignore[arg-type]

    assert summary.changed == 0
    assert summary.unchanged == 1


@pytest.mark.asyncio
async def test_backfill_location_display_names_survives_row_processing_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected row failures increment the failure bucket without aborting."""
    location = _location_row(display_name="Wola | ул. Konstruktorska")
    factory = _BackfillSessionFactory(
        [_backfill_row(location=location, text=_CYRILLIC_LOCATION_TEXT)],
    )

    async def _boom(*_: object, **__: object) -> None:
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(backfill_module, "_process_backfill_row", _boom)

    summary = await backfill_location_display_names(
        factory,  # type: ignore[arg-type]
        limit=None,
        apply=False,
    )

    assert summary.total == 1
    assert summary.failures == 1


@pytest.mark.asyncio
async def test_backfill_location_display_name_command_run_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI wrapper disposes database resources after each run."""
    disposed = False

    class _Database:
        session_factory = _EmptySessionFactory()

        @property
        def engine(self) -> SimpleNamespace:
            return SimpleNamespace(dispose=_dispose)

    async def _dispose() -> None:
        nonlocal disposed
        disposed = True

    monkeypatch.setattr(
        backfill_location_display_name_command,
        "load_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://example"),
    )
    monkeypatch.setattr(
        backfill_location_display_name_command,
        "create_database_resources",
        lambda _: _Database(),
    )

    async def _fake_backfill(
        *_args: object,
        **_kwargs: object,
    ) -> LocationDisplayNameBackfillSummary:
        return LocationDisplayNameBackfillSummary(
            total=0,
            changed=0,
            unchanged=0,
            skipped_verified=0,
            failures=0,
        )

    monkeypatch.setattr(
        backfill_location_display_name_command,
        "backfill_location_display_names",
        _fake_backfill,
    )

    payload = await backfill_location_display_name_command.run(limit=10, apply=False)
    assert payload == {
        "changed": 0,
        "failures": 0,
        "skipped_verified": 0,
        "total": 0,
        "unchanged": 0,
    }
    assert disposed is True


def test_backfill_location_display_name_command_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI main prints JSON summary to stdout."""

    async def _fake_run(*, limit: int | None, apply: bool) -> dict[str, int]:
        _ = (limit, apply)
        return {
            "total": 2,
            "changed": 1,
            "unchanged": 1,
            "skipped_verified": 3,
            "failures": 0,
        }

    monkeypatch.setattr(backfill_location_display_name_command, "run", _fake_run)
    backfill_location_display_name_command.main(["--limit", "25", "--apply"])
    captured = capsys.readouterr()
    assert '"changed": 1' in captured.out
    assert '"skipped_verified": 3' in captured.out


def test_backfill_location_display_name_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI main exits with code 2 when the backfill raises."""

    async def _boom(*_: object, **__: object) -> dict[str, int]:
        message = "boom"
        raise RuntimeError(message)

    monkeypatch.setattr(backfill_location_display_name_command, "run", _boom)
    with pytest.raises(SystemExit) as exc:
        backfill_location_display_name_command.main([])
    assert exc.value.code == 2


def test_build_parser_defaults_to_dry_run() -> None:
    """Dry-run is the default unless --apply is passed."""
    args = build_parser().parse_args([])
    assert args.apply is False
    assert args.limit is None
