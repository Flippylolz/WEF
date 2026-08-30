"""Groq Chat Completions adapter using existing httpx only."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Protocol

import httpx

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_HTTP_CLIENT_ERROR = 400
_HTTP_SERVER_ERROR = 500
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_QUOTA_STATUSES = frozenset({401, 402, 403})
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


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
        body: dict[str, object] = {
            "model": ALLOWED_GROQ_MODEL,
            "messages": list(messages),
            "temperature": 0,
            "stream": False,
            "reasoning_effort": "low",
            "max_completion_tokens": max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        status, payload, response_headers = await self._post_with_retry(body, headers)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if status == _HTTP_TOO_MANY_REQUESTS:
            raise ProviderRequestError(ProviderOutcome.RATE_LIMITED)
        if status in _HTTP_QUOTA_STATUSES:
            raise ProviderRequestError(ProviderOutcome.QUOTA)
        if _HTTP_CLIENT_ERROR <= status < _HTTP_SERVER_ERROR:
            raise ProviderRequestError(ProviderOutcome.REFUSAL)
        if status >= _HTTP_SERVER_ERROR:
            raise ProviderRequestError(ProviderOutcome.NETWORK)
        parsed = _parse_completion_payload(payload)
        return StructuredCompletion(
            payload=parsed,
            token_input=_usage_value(payload, "prompt_tokens"),
            token_output=_usage_value(payload, "completion_tokens"),
            latency_ms=latency_ms,
            request_id=_header_request_id(response_headers, payload),
        )

    async def _post_with_retry(
        self,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> tuple[int, object, Mapping[str, str]]:
        try:
            status, payload, response_headers = await self._transport.post_json(
                GROQ_CHAT_COMPLETIONS_URL,
                json_body=body,
                headers=headers,
                timeout_seconds=self._timeout_seconds,
            )
        except ProviderRequestError as error:
            if error.outcome is not ProviderOutcome.TIMEOUT:
                raise
            status, payload, response_headers = await self._transport.post_json(
                GROQ_CHAT_COMPLETIONS_URL,
                json_body=body,
                headers=headers,
                timeout_seconds=self._timeout_seconds,
            )
        if status >= _HTTP_SERVER_ERROR:
            status, payload, response_headers = await self._transport.post_json(
                GROQ_CHAT_COMPLETIONS_URL,
                json_body=body,
                headers=headers,
                timeout_seconds=self._timeout_seconds,
            )
        return status, payload, response_headers


def _parse_completion_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        raise ProviderRequestError(ProviderOutcome.SCHEMA)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderRequestError(ProviderOutcome.SCHEMA)
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderRequestError(ProviderOutcome.SCHEMA)
    message = first.get("message")
    if not isinstance(message, dict):
        raise ProviderRequestError(ProviderOutcome.SCHEMA)
    if message.get("refusal"):
        raise ProviderRequestError(ProviderOutcome.REFUSAL)
    content = message.get("content")
    parsed = message.get("parsed")
    if isinstance(parsed, dict):
        return parsed
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as error:
            raise ProviderRequestError(ProviderOutcome.SCHEMA) from error
        return decoded
    raise ProviderRequestError(ProviderOutcome.SCHEMA)


def _usage_value(payload: object, key: str) -> int | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if isinstance(value, int):
        return value
    return None


def _header_request_id(headers: Mapping[str, str], payload: object) -> str | None:
    for key, value in headers.items():
        if key.lower() == "x-request-id" and value:
            return value[:128]
    if isinstance(payload, dict):
        identifier = payload.get("id")
        if isinstance(identifier, str):
            return identifier[:128]
    return None
