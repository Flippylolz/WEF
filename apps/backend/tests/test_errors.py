"""Coverage for shared HTTP problem handlers."""

from __future__ import annotations

from uuid import uuid4

import pytest
from starlette.requests import Request

from wef_backend.errors import rate_limit_handler


@pytest.mark.asyncio
async def test_rate_limit_handler_returns_bounded_problem() -> None:
    """Public read throttling maps to one RFC 9457-style response."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/offers",
        "headers": [],
        "query_string": b"",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
    }
    request = Request(scope)
    request.state.request_id = uuid4()
    response = await rate_limit_handler(request, Exception("throttled"))
    assert response.status_code == 429
    payload = response.body.decode()
    assert "rate_limited" in payload
    assert "Try again later." in payload
