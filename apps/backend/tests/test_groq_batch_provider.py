"""Fake-transport coverage for the Groq Batch API adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    BatchCompletionRequest,
    ProviderOutcome,
    ProviderRequestError,
)
from wef_backend.features.admin.infrastructure.groq_batch_provider import (
    GROQ_BATCHES_URL,
    GROQ_FILES_URL,
    GroqBatchCompletionsAdapter,
    GroqBatchSettings,
)
from wef_backend.features.admin.infrastructure.groq_provider import GroqAiProvider


@dataclass
class ScriptedBatchTransport:
    """Script upload, batch create, poll, and download responses."""

    responses: list[object]
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def post_multipart(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        data: Mapping[str, str],
        files: Mapping[str, tuple[str, bytes, str]],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        del headers, data, files, timeout_seconds
        self.calls.append(("POST", url))
        payload = self.responses.pop(0)
        if isinstance(payload, ProviderRequestError):
            raise payload
        assert isinstance(payload, tuple)
        status, body, response_headers = payload
        return status, body, response_headers

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        del json_body, headers, timeout_seconds
        self.calls.append(("POST", url))
        payload = self.responses.pop(0)
        if isinstance(payload, ProviderRequestError):
            raise payload
        assert isinstance(payload, tuple)
        status, body, response_headers = payload
        return status, body, response_headers

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        del headers, timeout_seconds
        self.calls.append(("GET", url))
        payload = self.responses.pop(0)
        if isinstance(payload, ProviderRequestError):
            raise payload
        assert isinstance(payload, tuple)
        status, body, response_headers = payload
        return status, body, response_headers

    async def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, bytes, Mapping[str, str]]:
        del headers, timeout_seconds
        self.calls.append(("GET", url))
        payload = self.responses.pop(0)
        if isinstance(payload, ProviderRequestError):
            raise payload
        assert isinstance(payload, tuple)
        status, body, response_headers = payload
        assert isinstance(body, bytes)
        return status, body, response_headers


def _request(custom_id: str) -> BatchCompletionRequest:
    return BatchCompletionRequest(
        custom_id=custom_id,
        model=ALLOWED_GROQ_MODEL,
        messages=({"role": "user", "content": "hello"},),
        schema_name="ingestion_ai_parse",
        schema={"type": "object"},
        max_output_tokens=1500,
    )


async def test_complete_many_returns_empty_for_no_requests() -> None:
    adapter = GroqBatchCompletionsAdapter("gsk_test", transport=ScriptedBatchTransport([]))
    assert await adapter.complete_many(()) == ()


async def test_complete_many_uploads_one_batch_job_and_parses_output() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "completed", "output_file_id": "file_out"}, {}),
            (
                200,
                (
                    b'{"custom_id":"a","response":{"status_code":200,"body":'
                    b'{"choices":[{"message":{"parsed":{"verdict":"not_a_listing","fields":[],"warnings":[]}}}],'
                    b'"usage":{"prompt_tokens":1,"completion_tokens":2},"id":"chatcmpl-1"}},"error":null}\n'
                ),
                {},
            ),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=1.0),
    )
    results = await adapter.complete_many((_request("a"),))
    assert len(results) == 1
    assert results[0].custom_id == "a"
    assert results[0].error is None
    assert results[0].completion is not None
    assert transport.calls[0] == ("POST", GROQ_FILES_URL)
    assert transport.calls[1] == ("POST", GROQ_BATCHES_URL)
    assert transport.calls[3] == ("GET", f"{GROQ_FILES_URL}/file_out/content")


async def test_complete_many_returns_errors_when_batch_job_fails() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "failed"}, {}),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=1.0),
    )
    results = await adapter.complete_many((_request("a"),))
    assert len(results) == 1
    assert results[0].completion is None
    assert results[0].error is not None


async def test_complete_many_raises_when_upload_fails() -> None:
    transport = ScriptedBatchTransport([(400, {"error": "bad file"}, {})])
    adapter = GroqBatchCompletionsAdapter("gsk_test", transport=transport)
    with pytest.raises(ProviderRequestError):
        await adapter.complete_many((_request("a"),))


async def test_complete_many_marks_missing_custom_id_as_schema_error() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "completed", "output_file_id": "file_out"}, {}),
            (
                200,
                b'{"custom_id":"other","response":{"status_code":200,"body":{}},"error":null}\n',
                {},
            ),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=1.0),
    )
    results = await adapter.complete_many((_request("a"),))
    assert results[0].error is not None
    assert results[0].completion is None


async def test_complete_many_parses_provider_error_rows() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "completed", "output_file_id": "file_out"}, {}),
            (200, b'{"custom_id":"a","response":null,"error":{"message":"nope"}}\n', {}),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=1.0),
    )
    results = await adapter.complete_many((_request("a"),))
    assert results[0].error is not None
    assert results[0].completion is None


async def test_groq_ai_provider_delegates_complete_many_to_batch_api() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "completed", "output_file_id": "file_out"}, {}),
            (
                200,
                (
                    b'{"custom_id":"a","response":{"status_code":200,"body":'
                    b'{"choices":[{"message":{"parsed":{"ok":true}}}],'
                    b'"usage":{"prompt_tokens":1,"completion_tokens":2},"id":"chatcmpl-1"}},"error":null}\n'
                ),
                {},
            ),
        ],
    )
    provider = GroqAiProvider(
        "gsk_test",
        use_batch_api=True,
    )
    provider._batch._transport = transport  # noqa: SLF001
    provider._batch._settings = GroqBatchSettings(  # noqa: SLF001
        poll_interval_seconds=0.01,
        max_wait_seconds=1.0,
    )
    results = await provider.complete_many((_request("a"),))
    assert results[0].completion is not None
    assert results[0].completion.payload == {"ok": True}


async def test_complete_many_raises_when_batch_poll_times_out() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "in_progress"}, {}),
            (200, {"status": "in_progress"}, {}),
            (200, {"status": "in_progress"}, {}),
            (200, {"status": "in_progress"}, {}),
            (200, {"status": "in_progress"}, {}),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=0.05),
    )
    with pytest.raises(ProviderRequestError) as error:
        await adapter.complete_many((_request("a"),))
    assert error.value.outcome is ProviderOutcome.TIMEOUT


async def test_complete_many_maps_non_200_batch_responses() -> None:
    transport = ScriptedBatchTransport(
        [
            (200, {"id": "file_123"}, {}),
            (200, {"id": "batch_456"}, {}),
            (200, {"status": "completed", "output_file_id": "file_out"}, {}),
            (
                200,
                b'{"custom_id":"a","response":{"status_code":429,"body":{}},"error":null}\n',
                {},
            ),
        ],
    )
    adapter = GroqBatchCompletionsAdapter(
        "gsk_test",
        transport=transport,
        settings=GroqBatchSettings(poll_interval_seconds=0.01, max_wait_seconds=1.0),
    )
    results = await adapter.complete_many((_request("a"),))
    assert results[0].error is not None
    assert results[0].error.outcome is ProviderOutcome.RATE_LIMITED
