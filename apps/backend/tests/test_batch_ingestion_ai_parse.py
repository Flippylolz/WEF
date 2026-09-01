"""Tests for ingestion AI parse batch operator CLI."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from wef_backend.batch_ingestion_ai_parse_command import (
    BatchCandidate,
    BatchIngestionAiParseOptions,
    BatchIngestionAiParseSummary,
    build_parser,
    link_existing_offers,
    load_candidates,
    resolve_owner_id,
    run_batch,
)
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyOutcome,
    IngestionAiApplyStatus,
    IngestionAiParseOutcome,
    IngestionAiParseRun,
    IngestionAiParseStatus,
)
from wef_backend.settings import Settings


def _async_session_factory(session: AsyncMock) -> MagicMock:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=context)


def test_build_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.limit == 10
    assert args.spacing_seconds == 2.5
    assert args.generate_only is False
    assert args.link_existing_offers is False


@pytest.mark.asyncio
async def test_resolve_owner_id_uses_cli_value() -> None:
    owner_id = uuid4()
    resolved = await resolve_owner_id(
        MagicMock(),
        Settings(),
        owner_id=owner_id,
    )
    assert resolved == owner_id


@pytest.mark.asyncio
async def test_resolve_owner_id_loads_bootstrap_owner() -> None:
    owner_id = uuid4()
    session = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = owner_id
    session.execute = AsyncMock(return_value=lookup)
    resolved = await resolve_owner_id(
        _async_session_factory(session),
        Settings(bootstrap_owner_username="wef_owner"),
        owner_id=None,
    )
    assert resolved == owner_id


@pytest.mark.asyncio
async def test_link_existing_offers_returns_rowcount() -> None:
    session = AsyncMock()
    update_result = MagicMock()
    update_result.rowcount = 4
    session.execute = AsyncMock(return_value=update_result)
    linked = await link_existing_offers(_async_session_factory(session))
    assert linked == 4
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_candidates_maps_rows() -> None:
    revision_id = uuid4()
    session = AsyncMock()
    query_result = MagicMock()
    query_result.all.return_value = [(42, revision_id)]
    session.execute = AsyncMock(return_value=query_result)
    factory = _async_session_factory(session)
    candidates = await load_candidates(factory, limit=1, min_text_length=100)
    assert candidates == (
        BatchCandidate(external_message_id=42, source_message_revision_id=revision_id),
    )


@pytest.mark.asyncio
async def test_run_batch_generate_only_skips_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    owner_id = uuid4()
    revision_id = uuid4()
    run = cast(
        "IngestionAiParseRun",
        SimpleNamespace(id=uuid4(), offer_id=None),
    )

    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.resolve_owner_id",
        AsyncMock(return_value=owner_id),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.link_existing_offers",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.load_candidates",
        AsyncMock(
            return_value=(
                BatchCandidate(external_message_id=9, source_message_revision_id=revision_id),
            ),
        ),
    )
    fake_admin = SimpleNamespace(
        generate_ingestion_ai_parse=AsyncMock(
            return_value=IngestionAiParseOutcome(
                status=IngestionAiParseStatus.GENERATED,
                reason="",
                run=run,
            ),
        ),
        apply_ingestion_ai_parse=AsyncMock(),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.build_services",
        lambda _settings: SimpleNamespace(admin=fake_admin),
    )
    fake_engine = AsyncMock()
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.create_database_resources",
        lambda _url: SimpleNamespace(session_factory=MagicMock(), engine=fake_engine),
    )

    summary = await run_batch(
        BatchIngestionAiParseOptions(
            owner_id=owner_id,
            limit=1,
            spacing_seconds=0,
            generate_only=True,
            link_existing=False,
            min_text_length=120,
        ),
    )
    assert summary.generated == 1
    assert summary.applied == 0
    fake_admin.apply_ingestion_ai_parse.assert_not_called()


@pytest.mark.asyncio
async def test_run_batch_links_generates_and_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    owner_id = uuid4()
    revision_id = uuid4()
    run_id = uuid4()
    offer_id = uuid4()
    run = cast(
        "IngestionAiParseRun",
        SimpleNamespace(id=run_id, offer_id=offer_id),
    )

    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.resolve_owner_id",
        AsyncMock(return_value=owner_id),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.link_existing_offers",
        AsyncMock(return_value=2),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.load_candidates",
        AsyncMock(
            return_value=(
                BatchCandidate(external_message_id=7, source_message_revision_id=revision_id),
            ),
        ),
    )
    fake_admin = SimpleNamespace(
        generate_ingestion_ai_parse=AsyncMock(
            return_value=IngestionAiParseOutcome(
                status=IngestionAiParseStatus.GENERATED,
                reason="",
                run=run,
            ),
        ),
        apply_ingestion_ai_parse=AsyncMock(
            return_value=IngestionAiApplyOutcome(
                status=IngestionAiApplyStatus.APPLIED,
                run=run,
                offer_id=offer_id,
            ),
        ),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.build_services",
        lambda _settings: SimpleNamespace(admin=fake_admin),
    )
    fake_engine = AsyncMock()
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.create_database_resources",
        lambda _url: SimpleNamespace(session_factory=AsyncMock(), engine=fake_engine),
    )

    summary = await run_batch(
        BatchIngestionAiParseOptions(
            owner_id=None,
            limit=1,
            spacing_seconds=0,
            generate_only=False,
            link_existing=True,
            min_text_length=120,
            settings=Settings(),
        ),
    )
    assert summary == BatchIngestionAiParseSummary(
        linked_existing_offers=2,
        candidates_considered=1,
        generated=1,
        applied=1,
        skipped={},
    )
    fake_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_batch_records_generate_and_apply_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = uuid4()
    revision_ok = uuid4()
    revision_fail = uuid4()
    run = cast(
        "IngestionAiParseRun",
        SimpleNamespace(id=uuid4(), offer_id=None),
    )

    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.resolve_owner_id",
        AsyncMock(return_value=owner_id),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.link_existing_offers",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.load_candidates",
        AsyncMock(
            return_value=(
                BatchCandidate(external_message_id=1, source_message_revision_id=revision_ok),
                BatchCandidate(external_message_id=2, source_message_revision_id=revision_fail),
            ),
        ),
    )

    async def _generate(
        *,
        owner_id: UUID,
        source_message_revision_id: UUID,
        request_id: UUID,
    ) -> IngestionAiParseOutcome:
        _ = owner_id, request_id
        if source_message_revision_id == revision_fail:
            return IngestionAiParseOutcome(
                status=IngestionAiParseStatus.DENIED,
                reason="offer_exists",
                run=None,
            )
        return IngestionAiParseOutcome(
            status=IngestionAiParseStatus.GENERATED,
            reason="",
            run=run,
        )

    async def _apply(
        *,
        owner_id: UUID,
        run_id: UUID,
        request_id: UUID,
    ) -> IngestionAiApplyOutcome:
        _ = owner_id, run_id, request_id
        message = "proposal missing required fields"
        raise AdminDeniedError(message)

    fake_admin = SimpleNamespace(
        generate_ingestion_ai_parse=_generate,
        apply_ingestion_ai_parse=_apply,
    )
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.build_services",
        lambda _settings: SimpleNamespace(admin=fake_admin),
    )
    fake_engine = AsyncMock()
    monkeypatch.setattr(
        "wef_backend.batch_ingestion_ai_parse_command.create_database_resources",
        lambda _url: SimpleNamespace(session_factory=AsyncMock(), engine=fake_engine),
    )

    summary = await run_batch(
        BatchIngestionAiParseOptions(
            owner_id=owner_id,
            limit=2,
            spacing_seconds=0,
            generate_only=False,
            link_existing=False,
            min_text_length=120,
        ),
    )
    assert summary.generated == 1
    assert summary.applied == 0
    assert summary.skipped["offer_exists"] == 1
    assert summary.skipped["proposal missing required fields"] == 1
