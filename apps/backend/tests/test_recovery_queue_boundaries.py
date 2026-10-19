"""Durable recovery batches and provider receipts retain bounded state transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_provider_budget import Clock
from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)
from wef_backend.features.admin.application.automatic_recovery import RecoveryWork
from wef_backend.features.admin.application.provider_budget import BudgetedProvider
from wef_backend.features.admin.application.provider_context import provider_actor
from wef_backend.features.admin.infrastructure.provider_budget_store import (
    SQLAlchemyProviderBudget,
)
from wef_backend.features.admin.infrastructure.recovery_queue import SQLAlchemyRecoveryQueue

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def _work() -> RecoveryWork:
    return RecoveryWork(uuid4(), uuid4(), uuid4(), uuid4(), None, None, 1)


async def test_enqueue_caps_discovery_at_ten_short_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"id": uuid4(), "source_message_revision_id": uuid4(), "fields_json": []} for _ in range(10)
    ]
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    session = MagicMock(execute=AsyncMock(return_value=result))
    queue = SQLAlchemyRecoveryQueue(_factory(session))
    monkeypatch.setattr(queue, "reconcile_unsubmitted", AsyncMock(return_value=0))
    assert await queue.enqueue(uuid4(), NOW) == 100
    # One selection and ten inserts per transaction; no unbounded scan follows.
    assert session.execute.await_count == 110


@pytest.mark.parametrize("applied", [False, True])
async def test_cohort_approved_events_distinguish_applied_and_observed(*, applied: bool) -> None:
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {"reason": "below_threshold", "outcome": "observed"},
        {
            "reason": "applied" if applied else "below_threshold",
            "outcome": "applied" if applied else "observed",
        },
    ]
    queue = SQLAlchemyRecoveryQueue(_factory(MagicMock(execute=AsyncMock(return_value=result))))
    assert await queue.cohort_outcome(_work()) == (
        ("applied", None) if applied else ("observed", "validated_observation")
    )


@pytest.mark.parametrize("used", [0, 20])
async def test_provider_defer_requires_future_window_or_exhausted_daily_budget(used: int) -> None:
    attempt, account = MagicMock(), MagicMock()
    attempt.mappings.return_value.one_or_none.return_value = None
    account.mappings.return_value.one_or_none.return_value = {
        "next_eligible_at": NOW,
        "budget_day": NOW.date(),
        "used": used,
    }
    session = MagicMock(
        execute=AsyncMock(side_effect=[attempt, account, MagicMock()]),
        scalar=AsyncMock(return_value=None),
    )
    queue = SQLAlchemyRecoveryQueue(_factory(session))
    assert await queue.defer_provider(_work(), NOW) is (used == 20)
    assert session.execute.await_count == (3 if used else 2)
    if used:
        assert session.execute.await_args.args[1]["next"] == NOW + timedelta(days=1)


async def test_finished_provider_receipt_is_idempotent() -> None:
    result = MagicMock()
    result.mappings.return_value.one.return_value = {"state": "succeeded"}
    session = MagicMock(execute=AsyncMock(return_value=result))
    await SQLAlchemyProviderBudget(_factory(session)).finish(uuid4(), NOW, None, None)
    assert session.execute.await_count == 2


@pytest.mark.parametrize("safe_retry", [False, True])
async def test_network_receipt_distinguishes_safe_retry_from_uncertain_submission(
    *,
    safe_retry: bool,
) -> None:
    result = MagicMock()
    result.mappings.return_value.one.return_value = {
        "state": "submitting",
        "ordinal": 1,
        "owner_id": uuid4(),
    }
    session = MagicMock(execute=AsyncMock(return_value=result))
    error = ProviderRequestError(ProviderOutcome.NETWORK, safe_retry=safe_retry)
    await SQLAlchemyProviderBudget(_factory(session)).finish(uuid4(), NOW, error, None)
    update = session.execute.await_args_list[2].args[1]
    assert update["state"] == ("retry" if safe_retry else "uncertain")
    if safe_retry:
        assert update["eligible"] == error.retry_at == NOW + timedelta(seconds=60)
    else:
        assert update["reason"] == "uncertain_submission"
        assert error.retry_at is None


async def test_budgeted_complete_many_returns_successful_completion_and_releases_context() -> None:
    completion = StructuredCompletion({"ok": True}, 1, 1, 1, None)
    provider = MagicMock(complete=AsyncMock(return_value=completion))
    store = MagicMock(reserve=AsyncMock(return_value=uuid4()), finish=AsyncMock())
    request = BatchCompletionRequest(
        "synthetic",
        ALLOWED_GROQ_MODEL,
        ({"role": "user", "content": "fixture"},),
        "fixture",
        {},
        20,
    )
    actor = provider_actor.set((uuid4(), uuid4()))
    try:
        result = await BudgetedProvider(provider, store, Clock()).complete_many((request,))
    finally:
        provider_actor.reset(actor)
    assert len(result) == 1
    assert result[0].completion is completion
    assert result[0].error is None
    store.finish.assert_awaited_once()
