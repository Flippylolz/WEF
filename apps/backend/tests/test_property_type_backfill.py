"""Unit tests for property-type backfill reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self, cast

import pytest

if TYPE_CHECKING:
    from wef_backend.features.ingestion.infrastructure.models import (
        SourceChannelRow,
        SourceMessageRow,
    )

from wef_backend.backfill_property_type_command import build_parser
from wef_backend.features.ingestion.infrastructure.property_type_backfill import (
    PropertyTypeBackfillSummary,
    _row_to_raw,
    backfill_property_types,
)


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
