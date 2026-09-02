"""Shared Groq Chat Completions helpers for sync and batch adapters."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from wef_backend.features.admin.application.ai_review import (
    ProviderOutcome,
    ProviderRequestError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_HTTP_CLIENT_ERROR = 400
_HTTP_SERVER_ERROR = 500
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_OK = 200
_HTTP_QUOTA_STATUSES = frozenset({401, 402, 403})


def groq_chat_completion_body(
    *,
    model: str,
    messages: tuple[dict[str, str], ...],
    schema_name: str,
    schema: dict[str, object],
    max_output_tokens: int,
) -> dict[str, object]:
    """Build one Groq Chat Completions JSON body with strict structured output."""
    return {
        "model": model,
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


def parse_completion_payload(payload: object) -> object:
    """Decode structured output from a Groq Chat Completions response body."""
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


def usage_value(payload: object, key: str) -> int | None:
    """Read token usage from a Groq response body."""
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if isinstance(value, int):
        return value
    return None


def header_request_id(headers: Mapping[str, str], payload: object) -> str | None:
    """Return a redacted provider request id from headers or response body."""
    for key, value in headers.items():
        if key.lower() == "x-request-id" and value:
            return value[:128]
    if isinstance(payload, dict):
        identifier = payload.get("id")
        if isinstance(identifier, str):
            return identifier[:128]
    return None


def http_outcome(status: int) -> ProviderOutcome:
    """Map HTTP status codes to provider outcomes."""
    if status == _HTTP_TOO_MANY_REQUESTS:
        return ProviderOutcome.RATE_LIMITED
    if status in _HTTP_QUOTA_STATUSES:
        return ProviderOutcome.QUOTA
    if _HTTP_CLIENT_ERROR <= status < _HTTP_SERVER_ERROR:
        return ProviderOutcome.REFUSAL
    return ProviderOutcome.NETWORK
