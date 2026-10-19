"""Batch transport failures preserve outcomes and never fabricate provider results."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TYPE_CHECKING

import httpx
import pytest

from tests.test_groq_batch_provider import ScriptedBatchTransport, _request
from wef_backend.features.admin.application.ai_review import ProviderOutcome, ProviderRequestError
from wef_backend.features.admin.infrastructure.groq_batch_provider import (
    GroqBatchCompletionsAdapter,
    GroqBatchSettings,
    HTTPXBatchTransport,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


async def _send(
    transport: HTTPXBatchTransport, method: str
) -> tuple[int, object, Mapping[str, str]]:
    url = "https://provider.invalid/synthetic"
    headers = {"Authorization": "Bearer synthetic"}
    if method == "post_multipart":
        return await transport.post_multipart(
            url,
            headers=headers,
            data={"purpose": "batch"},
            files={"file": ("input.jsonl", b'{"synthetic":true}\n', "application/jsonl")},
            timeout_seconds=7.5,
        )
    if method == "post_json":
        return await transport.post_json(
            url,
            headers=headers,
            json_body={"synthetic": True},
            timeout_seconds=7.5,
        )
    if method == "get_json":
        return await transport.get_json(url, headers=headers, timeout_seconds=7.5)
    return await transport.get_bytes(url, headers=headers, timeout_seconds=7.5)


@pytest.mark.parametrize("method", ["post_multipart", "post_json", "get_json", "get_bytes"])
@pytest.mark.parametrize("mode", ["json", "not-json", "timeout", "network"])
async def test_httpx_batch_methods_preserve_wire_data_and_map_transport_failures(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    mode: str,
) -> None:
    requests: list[httpx.Request] = []
    clients: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        message = "synthetic private request"
        if mode == "timeout":
            raise httpx.ReadTimeout(message, request=request)
        if mode == "network":
            raise httpx.ConnectError(message, request=request)
        content = b'{"id":"synthetic-file"}' if mode == "json" else b"not-json"
        return httpx.Response(201, content=content, headers={"x-request-id": "synthetic-request"})

    def client(*, timeout: float) -> httpx.AsyncClient:
        assert timeout == 7.5
        instance = original(transport=httpx.MockTransport(handler), timeout=timeout)
        clients.append(instance)
        return instance

    monkeypatch.setattr(httpx, "AsyncClient", client)
    if mode in {"timeout", "network"}:
        with pytest.raises(ProviderRequestError) as caught:
            await _send(HTTPXBatchTransport(), method)
        assert caught.value.outcome is (
            ProviderOutcome.TIMEOUT if mode == "timeout" else ProviderOutcome.NETWORK
        )
        assert isinstance(caught.value.__cause__, httpx.HTTPError)
        assert "private request" not in str(caught.value)
    else:
        status, payload, headers = await _send(HTTPXBatchTransport(), method)
        assert status == 201
        assert headers["x-request-id"] == "synthetic-request"
        if method == "get_bytes":
            assert payload == (b'{"id":"synthetic-file"}' if mode == "json" else b"not-json")
        else:
            assert payload == ({"id": "synthetic-file"} if mode == "json" else {})
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "Bearer synthetic"
    if method == "post_multipart":
        assert b'filename="input.jsonl"' in requests[0].content
        assert b'{"synthetic":true}' in requests[0].content
    elif method == "post_json":
        assert json.loads(requests[0].content) == {"synthetic": True}
    assert len(clients) == 1
    assert clients[0].is_closed


async def test_disallowed_batch_model_never_submits_work() -> None:
    transport = ScriptedBatchTransport([])
    adapter = GroqBatchCompletionsAdapter("synthetic", transport=transport)
    with pytest.raises(ProviderRequestError) as caught:
        await adapter.complete_many((replace(_request("a"), model="unsupported-model"),))
    assert caught.value.outcome is ProviderOutcome.SCHEMA
    assert transport.calls == []


@pytest.mark.parametrize("upload", [(200, [], {}), (200, {"id": 7}, {})])
async def test_upload_requires_a_string_file_id_before_creating_a_batch(upload: object) -> None:
    transport = ScriptedBatchTransport([upload])
    adapter = GroqBatchCompletionsAdapter("synthetic", transport=transport)
    with pytest.raises(ProviderRequestError) as caught:
        await adapter.complete_many((_request("a"),))
    assert caught.value.outcome is ProviderOutcome.NETWORK
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([(200, {"id": "file"}, {}), (429, {}, {})], ProviderOutcome.RATE_LIMITED),
        (
            [(200, {"id": "file"}, {}), (200, {"id": "batch"}, {}), (500, {}, {})],
            ProviderOutcome.NETWORK,
        ),
        (
            [(200, {"id": "file"}, {}), (200, {"id": "batch"}, {}), (200, [], {})],
            ProviderOutcome.NETWORK,
        ),
        (
            [
                (200, {"id": "file"}, {}),
                (200, {"id": "batch"}, {}),
                (200, {"status": "completed", "output_file_id": "output"}, {}),
                (500, b"", {}),
            ],
            ProviderOutcome.NETWORK,
        ),
    ],
    ids=["create-refused", "poll-server-error", "poll-nonobject", "download-error"],
)
async def test_batch_stage_failures_preserve_provider_outcomes(
    responses: list[object],
    expected: ProviderOutcome,
) -> None:
    transport = ScriptedBatchTransport(responses.copy())
    adapter = GroqBatchCompletionsAdapter("synthetic", transport=transport)
    with pytest.raises(ProviderRequestError) as caught:
        await adapter.complete_many((_request("a"),))
    assert caught.value.outcome is expected
    assert transport.responses == []


@pytest.mark.parametrize("output_id", [None, 123])
async def test_completed_job_without_output_file_does_not_fabricate_completions(
    output_id: object,
) -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file"}, {}),
            (200, {"id": "batch"}, {}),
            (200, {"status": "completed", "output_file_id": output_id}, {}),
        ]
    )
    adapter = GroqBatchCompletionsAdapter("synthetic", transport=transport)
    results = await adapter.complete_many((_request("a"), _request("b")))
    assert [result.custom_id for result in results] == ["a", "b"]
    for result in results:
        assert result.completion is None
        assert result.error is not None
        assert result.error.outcome is ProviderOutcome.NETWORK
    assert len(transport.calls) == 3


async def test_batch_jsonl_skips_malformed_rows_and_preserves_request_order() -> None:
    lines = [
        "",
        "not-json",
        "[]",
        '{"custom_id":123}',
        json.dumps({"custom_id": "a", "response": None}),
        json.dumps({"custom_id": "b", "response": {"status_code": 200, "body": []}}),
        json.dumps(
            {
                "custom_id": "c",
                "response": {
                    "status_code": 200,
                    "body": {
                        "choices": [{"message": {"parsed": {"safe": True}}}],
                    },
                },
            }
        ),
    ]
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file"}, {}),
            (200, {"id": "batch"}, {}),
            (200, {"status": "completed", "output_file_id": "output"}, {}),
            (200, "\n".join(lines).encode(), {}),
        ]
    )
    adapter = GroqBatchCompletionsAdapter(
        "synthetic", transport=transport, settings=GroqBatchSettings(poll_interval_seconds=0)
    )
    results = await adapter.complete_many(
        tuple(_request(name) for name in ("c", "b", "a", "missing"))
    )
    assert [result.custom_id for result in results] == ["c", "b", "a", "missing"]
    assert results[0].completion is not None
    assert results[0].completion.payload == {"safe": True}
    expected = {
        "b": ProviderOutcome.NETWORK,
        "a": ProviderOutcome.SCHEMA,
        "missing": ProviderOutcome.SCHEMA,
    }
    for result in results[1:]:
        assert result.completion is None
        assert result.error is not None
        assert result.error.outcome is expected[result.custom_id]
