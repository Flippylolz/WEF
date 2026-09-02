"""Groq Batch API adapter for multi-request Chat Completions workloads."""

from __future__ import annotations

import asyncio
import io
import json
import time
from dataclasses import dataclass
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
from wef_backend.features.admin.infrastructure.groq_common import (
    _HTTP_CLIENT_ERROR,
    _HTTP_OK,
    groq_chat_completion_body,
    header_request_id,
    http_outcome,
    parse_completion_payload,
    usage_value,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

GROQ_FILES_URL = "https://api.groq.com/openai/v1/files"
GROQ_BATCHES_URL = "https://api.groq.com/openai/v1/batches"
_BATCH_TERMINAL = frozenset({"completed", "failed", "cancelled", "expired"})


class BatchTransport(Protocol):
    """Replaceable boundary for Groq file upload, batch, and download calls."""

    async def post_multipart(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        data: Mapping[str, str],
        files: Mapping[str, tuple[str, bytes, str]],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """POST multipart form data."""
        ...

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """POST JSON."""
        ...

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """GET JSON."""
        ...

    async def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, bytes, Mapping[str, str]]:
        """GET raw bytes."""
        ...


class HTTPXBatchTransport:
    """httpx transport for Groq batch endpoints."""

    async def post_multipart(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        data: Mapping[str, str],
        files: Mapping[str, tuple[str, bytes, str]],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """POST multipart form data."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers=dict(headers),
                    data=dict(data),
                    files={
                        key: (name, io.BytesIO(content), content_type)
                        for key, (name, content, content_type) in files.items()
                    },
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

    async def post_json(
        self,
        url: str,
        *,
        json_body: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """POST JSON."""
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

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, object, Mapping[str, str]]:
        """GET JSON."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=dict(headers))
                try:
                    payload: object = response.json()
                except ValueError:
                    payload = {}
                return response.status_code, payload, dict(response.headers)
        except httpx.TimeoutException as error:
            raise ProviderRequestError(ProviderOutcome.TIMEOUT) from error
        except httpx.HTTPError as error:
            raise ProviderRequestError(ProviderOutcome.NETWORK) from error

    async def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, bytes, Mapping[str, str]]:
        """GET raw bytes."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=dict(headers))
                return response.status_code, response.content, dict(response.headers)
        except httpx.TimeoutException as error:
            raise ProviderRequestError(ProviderOutcome.TIMEOUT) from error
        except httpx.HTTPError as error:
            raise ProviderRequestError(ProviderOutcome.NETWORK) from error


@dataclass(frozen=True, slots=True)
class GroqBatchSettings:
    """Polling and sizing defaults for Groq Batch jobs."""

    completion_window: str = "24h"
    poll_interval_seconds: float = 2.0
    max_wait_seconds: float = 3600.0


class GroqBatchCompletionsAdapter:
    """Submit Chat Completions work through Groq's Batch API."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: BatchTransport | None = None,
        timeout_seconds: float = 30.0,
        settings: GroqBatchSettings | None = None,
    ) -> None:
        """Store credentials in memory only."""
        self._api_key = api_key
        self._transport = transport or HTTPXBatchTransport()
        self._timeout_seconds = timeout_seconds
        self._settings = settings or GroqBatchSettings()

    async def complete_many(
        self,
        requests: tuple[BatchCompletionRequest, ...],
    ) -> tuple[BatchCompletionResult, ...]:
        """Run one Groq batch job and return results keyed by custom_id order."""
        if not requests:
            return ()
        for request in requests:
            if request.model != ALLOWED_GROQ_MODEL:
                raise ProviderRequestError(ProviderOutcome.SCHEMA)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        jsonl = _encode_batch_input(requests)
        file_id = await self._upload_batch_file(headers=headers, jsonl=jsonl)
        batch_id = await self._create_batch(headers=headers, input_file_id=file_id)
        output_file_id = await self._wait_for_output(
            headers=headers,
            batch_id=batch_id,
        )
        if output_file_id is None:
            return tuple(
                BatchCompletionResult(
                    custom_id=request.custom_id,
                    completion=None,
                    error=ProviderRequestError(ProviderOutcome.NETWORK),
                )
                for request in requests
            )
        raw = await self._download_file(headers=headers, file_id=output_file_id)
        return _parse_batch_output(requests, raw)

    async def _upload_batch_file(self, *, headers: Mapping[str, str], jsonl: bytes) -> str:
        status, payload, _headers = await self._transport.post_multipart(
            GROQ_FILES_URL,
            headers=headers,
            data={"purpose": "batch"},
            files={"file": ("batch-input.jsonl", jsonl, "application/jsonl")},
            timeout_seconds=self._timeout_seconds,
        )
        file_id = _json_id(payload, status)
        if file_id is None:
            raise ProviderRequestError(http_outcome(status))
        return file_id

    async def _create_batch(self, *, headers: Mapping[str, str], input_file_id: str) -> str:
        status, payload, _headers = await self._transport.post_json(
            GROQ_BATCHES_URL,
            json_body={
                "input_file_id": input_file_id,
                "endpoint": "/v1/chat/completions",
                "completion_window": self._settings.completion_window,
            },
            headers=headers,
            timeout_seconds=self._timeout_seconds,
        )
        batch_id = _json_id(payload, status)
        if batch_id is None:
            raise ProviderRequestError(http_outcome(status))
        return batch_id

    async def _wait_for_output(
        self,
        *,
        headers: Mapping[str, str],
        batch_id: str,
    ) -> str | None:
        deadline = time.monotonic() + self._settings.max_wait_seconds
        while time.monotonic() < deadline:
            status, payload, _headers = await self._transport.get_json(
                f"{GROQ_BATCHES_URL}/{batch_id}",
                headers=headers,
                timeout_seconds=self._timeout_seconds,
            )
            if status >= _HTTP_CLIENT_ERROR or not isinstance(payload, dict):
                raise ProviderRequestError(http_outcome(status))
            batch_status = payload.get("status")
            if batch_status in _BATCH_TERMINAL:
                if batch_status != "completed":
                    return None
                output_file_id = payload.get("output_file_id")
                return None if not isinstance(output_file_id, str) else output_file_id
            await asyncio.sleep(self._settings.poll_interval_seconds)
        raise ProviderRequestError(ProviderOutcome.TIMEOUT)

    async def _download_file(self, *, headers: Mapping[str, str], file_id: str) -> bytes:
        status, payload, _headers = await self._transport.get_bytes(
            f"{GROQ_FILES_URL}/{file_id}/content",
            headers=headers,
            timeout_seconds=self._timeout_seconds,
        )
        if status >= _HTTP_CLIENT_ERROR:
            raise ProviderRequestError(http_outcome(status))
        return payload


def _encode_batch_input(requests: tuple[BatchCompletionRequest, ...]) -> bytes:
    lines: list[str] = []
    for request in requests:
        line = {
            "custom_id": request.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": groq_chat_completion_body(
                model=request.model,
                messages=request.messages,
                schema_name=request.schema_name,
                schema=request.schema,
                max_output_tokens=request.max_output_tokens,
            ),
        }
        lines.append(json.dumps(line, ensure_ascii=False, separators=(",", ":")))
    return ("\n".join(lines) + "\n").encode()


def _parse_batch_output(  # noqa: C901
    requests: tuple[BatchCompletionRequest, ...],
    raw: bytes,
) -> tuple[BatchCompletionResult, ...]:
    by_custom_id: dict[str, BatchCompletionResult] = {}
    for line in raw.decode().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        custom_id = row.get("custom_id")
        if not isinstance(custom_id, str):
            continue
        error = row.get("error")
        if error is not None:
            by_custom_id[custom_id] = BatchCompletionResult(
                custom_id=custom_id,
                completion=None,
                error=ProviderRequestError(ProviderOutcome.REFUSAL),
            )
            continue
        response = row.get("response")
        if not isinstance(response, dict):
            by_custom_id[custom_id] = BatchCompletionResult(
                custom_id=custom_id,
                completion=None,
                error=ProviderRequestError(ProviderOutcome.SCHEMA),
            )
            continue
        status_code = response.get("status_code")
        body = response.get("body")
        if status_code != _HTTP_OK or not isinstance(body, dict):
            by_custom_id[custom_id] = BatchCompletionResult(
                custom_id=custom_id,
                completion=None,
                error=ProviderRequestError(http_outcome(int(status_code or 500))),
            )
            continue
        try:
            parsed = parse_completion_payload(body)
        except ProviderRequestError as provider_error:
            by_custom_id[custom_id] = BatchCompletionResult(
                custom_id=custom_id,
                completion=None,
                error=provider_error,
            )
            continue
        by_custom_id[custom_id] = BatchCompletionResult(
            custom_id=custom_id,
            completion=StructuredCompletion(
                payload=parsed,
                token_input=usage_value(body, "prompt_tokens"),
                token_output=usage_value(body, "completion_tokens"),
                latency_ms=0,
                request_id=header_request_id({}, body),
            ),
            error=None,
        )
    results: list[BatchCompletionResult] = []
    for request in requests:
        found = by_custom_id.get(request.custom_id)
        if found is None:
            results.append(
                BatchCompletionResult(
                    custom_id=request.custom_id,
                    completion=None,
                    error=ProviderRequestError(ProviderOutcome.SCHEMA),
                ),
            )
        else:
            results.append(found)
    return tuple(results)


def _json_id(payload: object, status: int) -> str | None:
    if status >= _HTTP_CLIENT_ERROR or not isinstance(payload, dict):
        return None
    identifier = payload.get("id")
    return None if not isinstance(identifier, str) else identifier
