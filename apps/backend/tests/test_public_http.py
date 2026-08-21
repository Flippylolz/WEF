"""Unit coverage for the public HTTP status helper."""

from __future__ import annotations

from typing import Self

import httpx
import pytest

from wef_backend.features.ingestion.infrastructure import public_http


@pytest.mark.asyncio
async def test_fetch_public_url_status_returns_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        status_code = 200

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str) -> _Resp:
            assert url.startswith("https://")
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    assert await public_http.fetch_public_url_status("https://t.me/example/1") == 200
