"""One durable reservation and one transport attempt per generation item."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    BatchCompletionResult,
    ChatCompletionsPort,
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
    estimate_tokens,
)
from wef_backend.features.admin.application.provider_context import provider_actor

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from wef_backend.features.identity.application.identity import Clock


MAX_INPUT_TOKENS = 5500
MAX_OUTPUT_TOKENS = 1500


class ProviderBudgetStore(Protocol):
    """Atomic allocation, pacing and append-only attempt outcomes."""

    async def reserve(
        self, owner: UUID, key: str, now: datetime, limit: int, *, operation_id: UUID | None = None
    ) -> UUID:
        """Reserve or raise a bounded deferred/terminal provider error."""
        ...

    async def finish(
        self,
        attempt: UUID,
        now: datetime,
        error: ProviderRequestError | None,
        completion: StructuredCompletion | None,
    ) -> None:
        """Save minimized outcome and release the allocation lease."""
        ...


class BudgetedProvider:
    """Enforce shared durable limits for every composed manual/scheduled call."""

    durable_budget = True

    def __init__(
        self,
        provider: ChatCompletionsPort,
        store: ProviderBudgetStore,
        clock: Clock,
        limit: int = 20,
    ) -> None:
        """Bind the single-attempt transport and authoritative reservation store."""
        self._provider, self._store, self._clock = provider, store, clock
        self._limit = min(20, max(0, limit))

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
        schema_name: str,
        schema: dict[str, object],
        max_output_tokens: int,
    ) -> StructuredCompletion:
        """Check whole-request size, reserve, then perform exactly one call."""
        actor = provider_actor.get()
        if actor is None:
            raise ProviderRequestError(ProviderOutcome.DISABLED)
        encoded = json.dumps([messages, schema], ensure_ascii=False)
        if (
            model != ALLOWED_GROQ_MODEL
            or max(estimate_tokens(encoded), len(encoded.encode()) + 256) > MAX_INPUT_TOKENS
        ):
            raise ProviderRequestError(ProviderOutcome.SCHEMA)
        if not 0 < max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ProviderRequestError(ProviderOutcome.SCHEMA)
        owner, operation = actor
        key = hashlib.sha256(f"{operation}:{schema_name}:{encoded}".encode()).hexdigest()
        attempt = await self._store.reserve(
            owner, key, self._clock.now(), self._limit, operation_id=operation
        )
        try:
            async with asyncio.timeout(30):
                completion = await self._provider.complete(
                    model=model,
                    messages=messages,
                    schema_name=schema_name,
                    schema=schema,
                    max_output_tokens=max_output_tokens,
                )
        except TimeoutError as timed_out:
            error = ProviderRequestError(ProviderOutcome.TIMEOUT, uncertain=True)
            await self._store.finish(attempt, self._clock.now(), error, None)
            raise error from timed_out
        except ProviderRequestError as error:
            await self._store.finish(attempt, self._clock.now(), error, None)
            raise
        await self._store.finish(attempt, self._clock.now(), None, completion)
        return completion

    async def complete_many(
        self,
        requests: tuple[BatchCompletionRequest, ...],
    ) -> tuple[BatchCompletionResult, ...]:
        """Return paced item outcomes without any Batch/Files API or hidden retry."""
        results = []
        for request in requests[:10]:
            try:
                completion = await self.complete(
                    model=request.model,
                    messages=request.messages,
                    schema_name=request.schema_name,
                    schema=request.schema,
                    max_output_tokens=request.max_output_tokens,
                )
                results.append(BatchCompletionResult(request.custom_id, completion, None))
            except ProviderRequestError as error:
                results.append(BatchCompletionResult(request.custom_id, None, error))
        return tuple(results)
