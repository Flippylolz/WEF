"""Groq Chat Completions adapter using existing httpx only."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Protocol

import httpx

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    BatchCompletionResult,
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)
from wef_backend.features.admin.infrastructure.groq_batch_provider import (
    GroqBatchCompletionsAdapter,
    GroqBatchSettings,
)
from wef_backend.features.admin.infrastructure.groq_common import (
    GROQ_CHAT_COMPLETIONS_URL,
    groq_chat_completion_body,
    header_request_id,
    parse_completion_payload,
    usage_value,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

_HTTP_CLIENT_ERROR = 400
_HTTP_SERVER_ERROR = 500
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_QUOTA_STATUSES = frozenset({401, 402, 403})


async def _complete_many_sequentially(
    complete: Callable[..., Awaitable[StructuredCompletion]],
    requests: tuple[BatchCompletionRequest, ...],
) -> tuple[BatchCompletionResult, ...]:
    """No hidden transport retry; production wraps each item in durable quota."""
    results = []
    for request in requests:
        try:
            completion = await complete(
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


class ChatCompletionsTransport(Protocol):
    """Narrow POST JSON boundary replaceable in tests."""

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """Return status, decoded JSON, and response headers."""
        ...


class HTTPXChatCompletionsTransport:
    """httpx implementation that never includes bodies in raised errors."""

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """POST JSON without reflecting URLs, keys, or bodies in errors."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    url,
                    json=dict(json_body),
                    headers=dict(headers),
                )
                try:
                    payload: object = response.json()
                except ValueError:
                    payload = {}
                return response.status_code, payload, dict(response.headers)
        except httpx.TimeoutException as error:
            raise ProviderRequestError(ProviderOutcome.TIMEOUT) from error
        except httpx.HTTPError as error:
            raise ProviderRequestError(ProviderOutcome.NETWORK) from error


class GroqChatCompletionsAdapter:
    """Exact Groq Chat Completions client for GPT-OSS 20B structured output."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: ChatCompletionsTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Store credentials in memory only."""
        self._api_key = api_key
        self._transport = transport or HTTPXChatCompletionsTransport()
        self._timeout_seconds = timeout_seconds

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
        schema_name: str,
        schema: dict[str, object],
        max_output_tokens: int,
    ) -> StructuredCompletion:
        """Call Groq once, retrying only a single transient timeout or 5xx."""
        if model != ALLOWED_GROQ_MODEL:
            raise ProviderRequestError(ProviderOutcome.SCHEMA)
        body = groq_chat_completion_body(
            model=model,
            messages=messages,
            schema_name=schema_name,
            schema=schema,
            max_output_tokens=max_output_tokens,
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        status, payload, response_headers = await self._post_with_retry(body, headers)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if status == _HTTP_TOO_MANY_REQUESTS:
            raise ProviderRequestError(
                ProviderOutcome.RATE_LIMITED, retry_at=_retry_after(response_headers)
            )
        if status in _HTTP_QUOTA_STATUSES:
            raise ProviderRequestError(ProviderOutcome.QUOTA)
        if _HTTP_CLIENT_ERROR <= status < _HTTP_SERVER_ERROR:
            raise ProviderRequestError(ProviderOutcome.REFUSAL)
        if status >= _HTTP_SERVER_ERROR:
            raise ProviderRequestError(ProviderOutcome.NETWORK, safe_retry=True)
        parsed = parse_completion_payload(payload)
        return StructuredCompletion(
            payload=parsed,
            token_input=usage_value(payload, "prompt_tokens"),
            token_output=usage_value(payload, "completion_tokens"),
            latency_ms=latency_ms,
            request_id=header_request_id(response_headers, payload),
        )

    async def _post_with_retry(
        self,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> tuple[int, object, Mapping[str, str]]:
        # Retry decisions belong to the durable reservation boundary.
        return await self._transport.post_json(
            GROQ_CHAT_COMPLETIONS_URL,
            json_body=body,
            headers=headers,
            timeout_seconds=self._timeout_seconds,
        )

    async def complete_many(
        self,
        requests: tuple[BatchCompletionRequest, ...],
    ) -> tuple[BatchCompletionResult, ...]:
        """Fall back to sequential chat completions when batch is unavailable."""
        return await _complete_many_sequentially(self.complete, requests)


class GroqAiProvider:
    """Groq provider: synchronous chat for interactive work, batch API for bulk."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: ChatCompletionsTransport | None = None,
        timeout_seconds: float = 30.0,
        batch_settings: GroqBatchSettings | None = None,
        use_batch_api: bool = True,
    ) -> None:
        """Store chat and batch adapters behind one port."""
        self._use_batch_api = use_batch_api
        self._chat = GroqChatCompletionsAdapter(
            api_key,
            transport=transport,
            timeout_seconds=timeout_seconds,
        )
        self._batch = GroqBatchCompletionsAdapter(
            api_key,
            timeout_seconds=timeout_seconds,
            settings=batch_settings,
        )

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
        schema_name: str,
        schema: dict[str, object],
        max_output_tokens: int,
    ) -> StructuredCompletion:
        """Return one synchronous completion for owner-interactive flows."""
        return await self._chat.complete(
            model=model,
            messages=messages,
            schema_name=schema_name,
            schema=schema,
            max_output_tokens=max_output_tokens,
        )

    async def complete_many(
        self,
        requests: tuple[BatchCompletionRequest, ...],
    ) -> tuple[BatchCompletionResult, ...]:
        """Use Groq Batch API whenever enabled; otherwise fall back sequentially."""
        if not requests:
            return ()
        if self._use_batch_api:
            return await self._batch.complete_many(requests)
        return await self._chat.complete_many(requests)


def _retry_after(headers: Mapping[str, str]) -> datetime | None:
    value = headers.get("retry-after") or headers.get("Retry-After")
    if value is None:
        return None
    try:
        return datetime.now(UTC) + timedelta(seconds=max(0, int(value)))
    except (ValueError, OverflowError):
        try:
            return parsedate_to_datetime(value).astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            return None
