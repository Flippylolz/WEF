"""Legacy ledger readbacks, source observations and owner refusal boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.fakes import FakeAdminAuditStore, FakeClock, FakeHasher, FakeIdentityStore
from tests.test_area_backfill import _AREA_TEXT, _backfill_row, _offer_row
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_persistence_application import _raw
from wef_backend.features.admin.application.admin_ops import (
    AdminDeniedError,
    AdminOutcome,
    ForceResetUserPassword,
    SetPlacePoint,
)
from wef_backend.features.admin.infrastructure.address_recovery import AddressRecoveryGeocoder
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parse_issue_serialization import (
    build_parse_issue_insert,
)
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
)
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.infrastructure import area_backfill
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)
from wef_backend.features.ingestion.infrastructure.models import ParseEvaluationRow
from wef_backend.features.ingestion.infrastructure.parse_issue_store import (
    SQLAlchemyParseIssueStore,
    insert_parse_issue,
)


async def test_parse_issue_readback_uses_latest_versioned_evaluation_and_can_link_offer() -> None:
    raw = _raw(message_id=7, text="random service message", checksum="a" * 64)
    issue = build_parse_issue_insert(
        extraction=extract_listing(raw),
        raw=raw,
        message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE,
        channel_id=uuid4(),
        source_message_id=uuid4(),
        source_message_revision_id=uuid4(),
        ingest_run_id=None,
        offer_id=None,
    )
    assert issue is not None
    session = MagicMock(execute=AsyncMock(return_value=MagicMock(rowcount=1)), commit=AsyncMock())
    await insert_parse_issue(session, issue)
    row = session.add.call_args.args[0]
    row.created_at = datetime.now(UTC)
    evaluation = ParseEvaluationRow(
        source_message_revision_id=issue.source_message_revision_id,
        parser_version=issue.parser_version,
        policy_version="fixture-policy",
        classification="parser_miss",
        state="open",
        recovery_eligible=True,
    )
    session.scalars = AsyncMock(
        side_effect=[
            MagicMock(all=MagicMock(return_value=[row])),
            MagicMock(all=MagicMock(return_value=[evaluation])),
        ]
    )
    store = SQLAlchemyParseIssueStore(_factory(session))
    found = await store.list_recent(limit=1)
    assert len(found) == 1
    assert found[0].recovery_eligible is True
    assert found[0].policy_version == "fixture-policy"
    assert (
        await store.link_offer_for_message(
            source_message_id=issue.source_message_id, offer_id=uuid4()
        )
        == 1
    )
    session.commit.assert_awaited_once_with()


async def test_area_backfill_limits_work_and_isolates_unexpected_row_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [_backfill_row(offer=_offer_row(), text=_AREA_TEXT) for _ in range(2)]
    session = MagicMock(execute=AsyncMock(return_value=MagicMock(all=MagicMock(return_value=rows))))
    process = AsyncMock(side_effect=OSError("synthetic row failure"))
    monkeypatch.setattr(area_backfill, "_process_backfill_row", process)
    summary = await area_backfill.backfill_areas(_factory(session), limit=1, apply=False)
    assert summary.total == summary.failures == 1
    process.assert_awaited_once()


async def test_missing_owner_authorization_prevents_address_provider_request() -> None:
    provider = MagicMock(complete=AsyncMock())
    adapter = AddressRecoveryGeocoder(
        provider,
        _factory(MagicMock(scalar=AsyncMock(return_value=None))),
        uuid4(),
    )
    result = await adapter.geocode(normalize_geocode_query("Testowa 7, Warszawa"))
    assert result.error_code is GeocodeErrorCode.NO_RESULT
    provider.complete.assert_not_awaited()


async def test_owner_point_write_failure_is_audited_and_refused() -> None:
    audits = FakeAdminAuditStore()
    point = SetPlacePoint(
        MagicMock(apply_set_point=AsyncMock(return_value=False)), audits, FakeClock()
    )
    with pytest.raises(AdminDeniedError, match="location not found"):
        await point(
            owner_id=uuid4(),
            location_id=uuid4(),
            longitude=Decimal("21.01"),
            latitude=Decimal("52.23"),
            request_id=uuid4(),
        )
    assert audits.events[-1].outcome is AdminOutcome.DENIED


async def test_owner_can_reset_another_owner_when_two_active_owners_remain() -> None:
    store, audits = FakeIdentityStore(), FakeAdminAuditStore()
    owners = [
        await store.create_account(
            username_normalized=name,
            username_display=name,
            hashed_password="old",
            role=UserRole.OWNER,
            must_change_password=False,
        )
        for name in ("owner-one", "owner-two")
    ]
    await ForceResetUserPassword(store, audits, FakeHasher(), FakeClock())(
        owner_id=owners[0].id,
        target_user_id=owners[1].id,
        temporary_password="temporary123",
        request_id=uuid4(),
    )
    updated = await store.find_account_by_id(owners[1].id)
    assert updated is not None
    assert updated.must_change_password is True
    assert audits.events[-1].outcome is AdminOutcome.ALLOWED


async def test_fake_source_observation_distinguishes_retained_and_unknown_message_ids() -> None:
    entity = TelegramChannelEntity("synthetic", "9001", "Synthetic")
    message = LiveTelegramMessage(7, "fixture", datetime.now(UTC), None)
    client = FakeTelegramLiveClient(entity, (message,))
    observations = await client.observe_messages(username="synthetic", ids=(7, 8))
    assert [item.disposition for item in observations] == ["present", "unknown"]
    assert observations[0].message is message
