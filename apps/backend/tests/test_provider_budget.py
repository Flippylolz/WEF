"""No provider side effects without attribution, preflight and reservation."""

from dataclasses import asdict
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)
from wef_backend.features.admin.application.provider_budget import BudgetedProvider
from wef_backend.features.admin.application.provider_context import (
    provider_actor,
    provider_operation,
)


class Clock:
    """Fixed UTC clock for request-boundary tests."""

    def now(self) -> datetime:
        return datetime(2026, 9, 5, tzinfo=UTC)


async def test_preflight_context_reservation_and_failure_are_atomic_boundaries() -> None:
    provider, store = AsyncMock(), AsyncMock()
    store.reserve.return_value = uuid4()
    provider.complete.return_value = StructuredCompletion({}, 1, 1, 1, None)
    wrapped = BudgetedProvider(provider, store, Clock())
    request = asdict(
        BatchCompletionRequest(
            custom_id="one",
            model=ALLOWED_GROQ_MODEL,
            messages=({"role": "user", "content": "masked"},),
            schema_name="test",
            schema={},
            max_output_tokens=1500,
        )
    )
    request.pop("custom_id")
    with pytest.raises(ProviderRequestError):
        await wrapped.complete(**request)
    token = provider_actor.set((uuid4(), uuid4()))
    try:
        for changed in (
            {"messages": ({"content": "x" * 12000},)},
            {"max_output_tokens": 1501},
            {"model": "wrong"},
        ):
            with pytest.raises(ProviderRequestError):
                await wrapped.complete(**(request | changed))
        store.reserve.assert_not_called()
        await wrapped.complete(**request)
        assert provider.complete.await_count == 1
        assert store.finish.await_count == 1
        provider.complete.side_effect = ProviderRequestError(ProviderOutcome.TIMEOUT)
        result = await wrapped.complete_many((BatchCompletionRequest("one", **request),))
        assert result[0].error is not None
        assert store.finish.await_count == 2
        provider.complete.side_effect = TimeoutError
        with pytest.raises(ProviderRequestError) as failure:
            await wrapped.complete(**request)
        assert failure.value.uncertain is True
        assert provider.complete.await_count == 3
        assert store.finish.await_count == 3
    finally:
        provider_actor.reset(token)


async def test_provider_attribution_restores_context_even_on_failure() -> None:
    @provider_operation
    async def fail(*, owner_id: object, request_id: object) -> None:
        assert provider_actor.get() == (owner_id, request_id)
        raise RuntimeError

    with pytest.raises(RuntimeError):
        await fail(owner_id=uuid4(), request_id=uuid4())
    assert provider_actor.get() is None
    with pytest.raises(TypeError):
        await fail(owner_id=None, request_id=None)
