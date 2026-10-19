"""Adapter fallbacks retain typed errors, transaction ownership and bounded output."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_groq_provider import ScriptedTransport, _completion
from tests.test_ingestion_persistence_boundaries import _factory
from wef_backend.features.admin.application.ai_review import ALLOWED_GROQ_MODEL
from wef_backend.features.admin.infrastructure.groq_provider import GroqAiProvider, _retry_after
from wef_backend.features.catalog.application import BoundingBox, MapFilters
from wef_backend.features.catalog.domain import ContentType
from wef_backend.features.catalog.infrastructure.map_query_adapter import SQLAlchemyMapQueryAdapter
from wef_backend.features.contacts.domain.model import RevealOutcome
from wef_backend.features.contacts.infrastructure.store import SQLAlchemyContactStore
from wef_backend.features.identity.infrastructure.favorite_store import SQLAlchemyFavoriteStore
from wef_backend.features.identity.infrastructure.models import SessionRow
from wef_backend.features.identity.infrastructure.store import SQLAlchemyIdentityStore
from wef_backend.features.ingestion.application import ChannelExpectation
from wef_backend.features.ingestion.domain import SourceIdentity, SourcePlatform
from wef_backend.features.ingestion.infrastructure import report_writer
from wef_backend.features.ingestion.infrastructure.telegram_export import (
    TelegramDesktopExportAdapter,
)
from wef_backend.features.ingestion.infrastructure.telegram_record import convert_record

if TYPE_CHECKING:
    from pathlib import Path


async def test_favorite_remove_is_idempotent_and_commits_only_existing_row() -> None:
    row = MagicMock()
    session = MagicMock(
        scalar=AsyncMock(side_effect=[row, None]), delete=AsyncMock(), commit=AsyncMock()
    )
    store = SQLAlchemyFavoriteStore(_factory(session))
    user, location = uuid4(), uuid4()
    await store.remove_favorite(user, location)
    await store.remove_favorite(user, location)
    session.delete.assert_awaited_once_with(row)
    session.commit.assert_awaited_once_with()


async def test_favorite_insert_commits_visible_location() -> None:
    session = MagicMock(
        scalar=AsyncMock(return_value=uuid4()), execute=AsyncMock(), commit=AsyncMock()
    )
    store = SQLAlchemyFavoriteStore(_factory(session))
    assert await store.add_favorite(uuid4(), uuid4())
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once_with()


async def test_identity_session_lookup_maps_persisted_expiry_and_revoke_is_scoped() -> None:
    now = datetime.now(UTC)
    row = SessionRow(
        id=uuid4(),
        user_id=uuid4(),
        token_hash="a" * 64,
        expires_at=now + timedelta(hours=1),
        revoked_at=None,
        created_at=now,
    )
    session = MagicMock(scalar=AsyncMock(return_value=row), execute=AsyncMock(), commit=AsyncMock())
    store = SQLAlchemyIdentityStore(_factory(session))
    found = await store.find_session_by_token_hash(row.token_hash)
    assert found is not None
    assert found.account_id == row.user_id
    assert found.expires_at == row.expires_at
    await store.revoke_session(row.id)
    update = session.execute.await_args.args[0]
    assert update.compile().params["id_1"] == row.id
    session.commit.assert_awaited_once_with()


async def test_contact_audit_skips_missing_offer_without_foreign_key_write() -> None:
    session = MagicMock(scalar=AsyncMock(return_value=None))
    await SQLAlchemyContactStore(_factory(session)).record_reveal(
        user_id=uuid4(),
        offer_id=uuid4(),
        source_message_id=None,
        request_id=uuid4(),
        outcome=RevealOutcome.FORBIDDEN,
    )
    session.add.assert_not_called()


def test_map_query_includes_upper_price_area_content_and_publication_bounds() -> None:
    now = datetime.now(UTC)
    filters = MapFilters(
        bbox=BoundingBox(20.9, 52.1, 21.1, 52.3),
        price_max=90000000,
        area_min=Decimal(30),
        area_max=Decimal(80),
        content_types=(ContentType.UNIT,),
        published_to=now,
    )
    params: dict[str, object] = {}
    for clause in SQLAlchemyMapQueryAdapter.filter_conditions(filters):
        params.update(clause.compile().params)
    assert 90000000 in params.values()
    assert Decimal(30) in params.values()
    assert Decimal(80) in params.values()
    assert now in params.values()
    assert [ContentType.UNIT.value] in params.values()


async def test_provider_interactive_completion_and_empty_batch_route_correctly() -> None:
    transport = ScriptedTransport([(200, _completion({"ok": True}), {})])
    provider = GroqAiProvider("synthetic-key", transport=transport)
    assert await provider.complete_many(()) == ()
    assert not transport.calls
    result = await provider.complete(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "synthetic"},),
        schema_name="fixture",
        schema={"type": "object"},
        max_output_tokens=20,
    )
    assert result.payload == {"ok": True}
    assert len(transport.calls) == 1


@pytest.mark.parametrize("value", ["Wed, 21 Oct 2037 07:28:00 GMT", "malformed", "9" * 100])
def test_provider_retry_after_supports_dates_and_refuses_unbounded_values(value: str) -> None:
    result = _retry_after({"Retry-After": value})
    expected = datetime(2037, 10, 21, 7, 28, tzinfo=UTC) if value.startswith("Wed") else None
    assert result == expected


@pytest.mark.parametrize(
    "fields",
    [
        {"date_unixtime": "not-a-number"},
        {"date_unixtime": 10**100},
        {"grouped_id": " "},
        {"reply_to_message_id": -1},
        {"grouped_id": 3, "media_group_id": 4},
    ],
)
def test_telegram_malformed_timestamp_reply_and_group_are_retained_as_malformed(
    fields: dict[str, object],
) -> None:
    source = SourceIdentity(SourcePlatform.TELEGRAM, "9001", "Synthetic", "public_channel")
    result = convert_record(
        {"id": 1, "type": "message", "date_unixtime": "1792368000", "text": "fixture"} | fields,
        0,
        source,
    ).result
    assert result.message is None
    assert result.reason is not None


def test_scan_metadata_is_available_without_starting_iteration(tmp_path: Path) -> None:
    source = tmp_path / "export.json"
    source.write_text('{"id":9001,"name":"Synthetic","type":"public_channel","messages":[]}')
    expected = ChannelExpectation("9001", "public_channel", "Synthetic")
    scan = TelegramDesktopExportAdapter(source, expected).open_scan()
    try:
        assert scan.source.identity.channel_id == "9001"
        assert not scan.is_complete
    finally:
        scan.close()


def test_report_temporary_file_is_removed_after_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_descriptor: int) -> None:
        message = "synthetic filesystem failure"
        raise OSError(message)

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="filesystem failure"):
        report_writer._write_temporary(tmp_path, b"synthetic")  # noqa: SLF001
    assert list(tmp_path.iterdir()) == []
