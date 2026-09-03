"""Fake-transport coverage for the Groq Chat Completions adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self, cast

import httpx
import pytest

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    ProviderOutcome,
    ProviderRequestError,
)
from wef_backend.features.admin.infrastructure.groq_common import (
    GROQ_CHAT_COMPLETIONS_URL,
    groq_chat_completion_body,
    header_request_id,
    http_outcome,
    parse_completion_payload,
    usage_value,
)
from wef_backend.features.admin.infrastructure.groq_provider import (
    GroqAiProvider,
    GroqChatCompletionsAdapter,
    HTTPXChatCompletionsTransport,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class ScriptedTransport:
    """Return scripted status/payload pairs or bounded provider errors."""

    responses: list[object]
    calls: list[dict[str, object]] = field(default_factory=list)

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        self.calls.append(
            {
                "url": url,
                "body": dict(json_body),
                "headers": dict(headers),
                "timeout": timeout_seconds,
            },
        )
        payload = self.responses.pop(0)
        if isinstance(payload, ProviderRequestError):
            raise payload
        if not isinstance(payload, tuple) or len(payload) != 3:
            message = "scripted transport payload must be a status tuple"
            raise AssertionError(message)
        status, body, headers = payload
        assert isinstance(status, int)
        return status, body, headers


def _completion(content: object) -> dict[str, object]:
    if isinstance(content, dict):
        message: dict[str, object] = {"parsed": content}
    else:
        message = {"content": content}
    return {
        "id": "chatcmpl-test",
        "choices": [{"message": message}],
        "usage": {"prompt_tokens": 40, "completion_tokens": 12},
    }


def _adapter(transport: ScriptedTransport) -> GroqChatCompletionsAdapter:
    return GroqChatCompletionsAdapter(
        "gsk_test_secret_value",
        transport=transport,
        timeout_seconds=12.0,
    )


async def test_adapter_sends_exact_model_and_strict_schema() -> None:
    """The request uses GPT-OSS 20B, low reasoning, no stream/tools, and strict JSON."""
    transport = ScriptedTransport(
        [
            (
                200,
                _completion({"verdict": "no_change", "fields": [], "warnings": []}),
                {"x-request-id": "req-1"},
            ),
        ],
    )
    result = await _adapter(transport).complete(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="place_review",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    call = transport.calls[0]
    body = call["body"]
    assert isinstance(body, dict)
    assert call["url"] == GROQ_CHAT_COMPLETIONS_URL
    assert body["model"] == ALLOWED_GROQ_MODEL
    assert body["stream"] is False
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 1500
    assert "tools" not in body
    format_block = body["response_format"]
    assert isinstance(format_block, dict)
    schema_block = format_block["json_schema"]
    assert isinstance(schema_block, dict)
    assert schema_block["strict"] is True
    assert schema_block["name"] == "place_review"
    headers = call["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer gsk_test_secret_value"
    assert result.payload == {"verdict": "no_change", "fields": [], "warnings": []}
    assert result.request_id == "req-1"
    assert result.token_input == 40


async def test_adapter_retries_timeout_and_5xx_once_only() -> None:
    """One retry is used for timeout or 5xx; 4xx never retries."""
    timeout_then_ok = ScriptedTransport(
        [
            ProviderRequestError(ProviderOutcome.TIMEOUT),
            (200, _completion('{"ok": true}'), {}),
        ],
    )
    parsed = await _adapter(timeout_then_ok).complete(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "x"},),
        schema_name="place_review",
        schema={},
        max_output_tokens=10,
    )
    assert parsed.payload == {"ok": True}
    assert len(timeout_then_ok.calls) == 2

    server_error = ScriptedTransport([(500, {}, {}), (200, _completion({"a": 1}), {})])
    recovered = await _adapter(server_error).complete(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "x"},),
        schema_name="place_review",
        schema={},
        max_output_tokens=10,
    )
    assert recovered.payload == {"a": 1}

    client_error = ScriptedTransport([(400, {"error": "secret-body"}, {})])
    with pytest.raises(ProviderRequestError) as refused:
        await _adapter(client_error).complete(
            model=ALLOWED_GROQ_MODEL,
            messages=({"role": "user", "content": "x"},),
            schema_name="place_review",
            schema={},
            max_output_tokens=10,
        )
    assert refused.value.outcome is ProviderOutcome.REFUSAL
    assert "secret-body" not in str(refused.value)
    assert len(client_error.calls) == 1


async def test_adapter_maps_quota_rate_limit_and_refusal() -> None:
    """HTTP statuses map to bounded outcomes without reflecting bodies."""
    cases = (
        (429, ProviderOutcome.RATE_LIMITED),
        (401, ProviderOutcome.QUOTA),
        (403, ProviderOutcome.QUOTA),
        (402, ProviderOutcome.QUOTA),
    )
    for status, expected in cases:
        transport = ScriptedTransport([(status, {"error": "do-not-log"}, {})])
        with pytest.raises(ProviderRequestError) as error:
            await _adapter(transport).complete(
                model=ALLOWED_GROQ_MODEL,
                messages=({"role": "user", "content": "x"},),
                schema_name="place_review",
                schema={},
                max_output_tokens=10,
            )
        assert error.value.outcome is expected
        assert "do-not-log" not in str(error.value)

    wrong_model = ScriptedTransport([])
    with pytest.raises(ProviderRequestError) as schema_error:
        await _adapter(wrong_model).complete(
            model="openai/gpt-oss-120b",
            messages=({"role": "user", "content": "x"},),
            schema_name="place_review",
            schema={},
            max_output_tokens=10,
        )
    assert schema_error.value.outcome is ProviderOutcome.SCHEMA
    assert wrong_model.calls == []


async def test_httpx_transport_maps_timeout_without_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real httpx wrapper converts timeouts without including request bodies."""

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> object:
            message = "slow"
            raise httpx.TimeoutException(message)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    with pytest.raises(ProviderRequestError) as error:
        await HTTPXChatCompletionsTransport().post_json(
            GROQ_CHAT_COMPLETIONS_URL,
            json_body={"prompt": "secret-source-text"},
            headers={"Authorization": "Bearer gsk_test_secret_value"},
            timeout_seconds=1.0,
        )
    assert error.value.outcome is ProviderOutcome.TIMEOUT
    assert "secret-source-text" not in str(error.value)
    assert "gsk_test_secret_value" not in str(error.value)


async def test_httpx_transport_maps_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connect failures become NETWORK without reflecting secrets."""

    class _NetworkClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> object:
            message = "offline"
            raise httpx.ConnectError(message)

    monkeypatch.setattr(httpx, "AsyncClient", _NetworkClient)
    with pytest.raises(ProviderRequestError) as network:
        await HTTPXChatCompletionsTransport().post_json(
            GROQ_CHAT_COMPLETIONS_URL,
            json_body={"prompt": "secret-source-text"},
            headers={"Authorization": "Bearer gsk_test_secret_value"},
            timeout_seconds=1.0,
        )
    assert network.value.outcome is ProviderOutcome.NETWORK
    assert "secret-source-text" not in str(network.value)


async def test_httpx_transport_accepts_non_json_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-JSON responses are treated as an empty object."""

    class _Resp:
        status_code = 200

        def json(self) -> object:
            message = "bad json"
            raise ValueError(message)

        @property
        def headers(self) -> dict[str, str]:
            return {"X-Request-Id": "hdr-1"}

    class _JsonClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> _Resp:
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _JsonClient)
    status, payload, headers = await HTTPXChatCompletionsTransport().post_json(
        GROQ_CHAT_COMPLETIONS_URL,
        json_body={},
        headers={},
        timeout_seconds=1.0,
    )
    assert status == 200
    assert payload == {}
    assert headers["X-Request-Id"] == "hdr-1"


async def test_adapter_parse_failures_and_request_id_fallback() -> None:
    """Malformed completions map to schema/refusal without leaking bodies."""
    bad_payloads: tuple[tuple[object, ProviderOutcome], ...] = (
        ("not-a-dict", ProviderOutcome.SCHEMA),
        ({"choices": []}, ProviderOutcome.SCHEMA),
        ({"choices": ["x"]}, ProviderOutcome.SCHEMA),
        ({"choices": [{}]}, ProviderOutcome.SCHEMA),
        ({"choices": [{"message": {"refusal": "nope"}}]}, ProviderOutcome.REFUSAL),
        ({"choices": [{"message": {"content": "{"}}]}, ProviderOutcome.SCHEMA),
        ({"choices": [{"message": {"content": 1}}]}, ProviderOutcome.SCHEMA),
    )
    for payload, expected in bad_payloads:
        transport = ScriptedTransport([(200, payload, {})])
        with pytest.raises(ProviderRequestError) as error:
            await _adapter(transport).complete(
                model=ALLOWED_GROQ_MODEL,
                messages=({"role": "user", "content": "x"},),
                schema_name="place_review",
                schema={},
                max_output_tokens=10,
            )
        assert error.value.outcome is expected

    network = ScriptedTransport([ProviderRequestError(ProviderOutcome.NETWORK)])
    with pytest.raises(ProviderRequestError) as raised:
        await _adapter(network).complete(
            model=ALLOWED_GROQ_MODEL,
            messages=({"role": "user", "content": "x"},),
            schema_name="place_review",
            schema={},
            max_output_tokens=10,
        )
    assert raised.value.outcome is ProviderOutcome.NETWORK

    persistent_500 = ScriptedTransport([(500, {}, {}), (503, {}, {})])
    with pytest.raises(ProviderRequestError) as server:
        await _adapter(persistent_500).complete(
            model=ALLOWED_GROQ_MODEL,
            messages=({"role": "user", "content": "x"},),
            schema_name="place_review",
            schema={},
            max_output_tokens=10,
        )
    assert server.value.outcome is ProviderOutcome.NETWORK

    from_payload_id = ScriptedTransport(
        [(200, {"id": "cmpl-from-body", "choices": [{"message": {"parsed": {"ok": True}}}]}, {})],
    )
    parsed = await _adapter(from_payload_id).complete(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "x"},),
        schema_name="place_review",
        schema={},
        max_output_tokens=10,
    )
    assert parsed.request_id == "cmpl-from-body"
    assert parsed.token_input is None


def test_groq_chat_completion_body_uses_strict_schema() -> None:
    body = groq_chat_completion_body(
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    assert body["reasoning_effort"] == "low"
    response_format = cast("dict[str, object]", body["response_format"])
    json_schema = cast("dict[str, object]", response_format["json_schema"])
    assert json_schema["strict"] is True


def test_http_outcome_maps_status_codes() -> None:
    assert http_outcome(429) is ProviderOutcome.RATE_LIMITED
    assert http_outcome(403) is ProviderOutcome.QUOTA
    assert http_outcome(422) is ProviderOutcome.REFUSAL
    assert http_outcome(503) is ProviderOutcome.NETWORK


def test_parse_completion_payload_accepts_content_json() -> None:
    parsed = parse_completion_payload(
        {"choices": [{"message": {"content": '{"ok": true}'}}]},
    )
    assert parsed == {"ok": True}


def test_usage_value_returns_none_for_missing_usage() -> None:
    assert usage_value({}, "prompt_tokens") is None
    assert usage_value({"usage": {}}, "prompt_tokens") is None
    assert usage_value("not-a-dict", "prompt_tokens") is None
    assert usage_value({"usage": {"prompt_tokens": "40"}}, "prompt_tokens") is None
    assert usage_value({"usage": {"prompt_tokens": 40}}, "prompt_tokens") == 40


def test_header_request_id_prefers_response_header() -> None:
    assert header_request_id({"X-Request-Id": "req-from-header"}, {}) == "req-from-header"
    assert header_request_id({}, {"id": "req-from-body"}) == "req-from-body"
    assert header_request_id({"x-request-id": ""}, {"id": "req-from-body"}) == "req-from-body"
    assert header_request_id({}, {"id": 123}) is None
    assert header_request_id({}, {}) is None
    assert header_request_id({}, "not-a-dict") is None


async def test_groq_ai_provider_complete_many_without_batch_api() -> None:
    transport = ScriptedTransport([(200, _completion({"ok": True}), {})])
    provider = GroqAiProvider("gsk_test_secret_value", transport=transport, use_batch_api=False)
    request = BatchCompletionRequest(
        custom_id="a",
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    results = await provider.complete_many((request,))
    assert len(results) == 1
    assert results[0].error is None
    assert results[0].completion is not None
    assert results[0].completion.payload == {"ok": True}


async def test_chat_adapter_complete_many_falls_back_sequentially() -> None:
    transport = ScriptedTransport([(200, _completion({"ok": True}), {})])
    adapter = GroqChatCompletionsAdapter("gsk_test_secret_value", transport=transport)
    request = BatchCompletionRequest(
        custom_id="a",
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    results = await adapter.complete_many((request,))
    assert results[0].completion is not None


async def test_chat_adapter_complete_many_records_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(
        "wef_backend.features.admin.infrastructure.groq_provider.asyncio.sleep",
        _fake_sleep,
    )
    transport = ScriptedTransport([(429, {}, {}), (429, {}, {}), (429, {}, {}), (429, {}, {})])
    adapter = GroqChatCompletionsAdapter("gsk_test_secret_value", transport=transport)
    request = BatchCompletionRequest(
        custom_id="a",
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    results = await adapter.complete_many((request,))
    assert results[0].completion is None
    assert results[0].error is not None
    assert results[0].error.outcome is ProviderOutcome.RATE_LIMITED
    # Initial attempt plus three backoff retries.
    assert len(transport.calls) == 4


async def test_chat_adapter_complete_many_retries_rate_limit_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        "wef_backend.features.admin.infrastructure.groq_provider.asyncio.sleep",
        _fake_sleep,
    )
    transport = ScriptedTransport(
        [
            (429, {}, {}),
            (200, _completion({"ok": True}), {}),
        ],
    )
    adapter = GroqChatCompletionsAdapter("gsk_test_secret_value", transport=transport)
    request = BatchCompletionRequest(
        custom_id="a",
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )
    results = await adapter.complete_many((request,))
    assert results[0].error is None
    assert results[0].completion is not None
    assert results[0].completion.payload == {"ok": True}
    assert sleeps == [2.0]
    assert len(transport.calls) == 2
