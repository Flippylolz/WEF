"""Public HTTP helper for Telegram t.me reachability probes."""

from __future__ import annotations

import httpx


async def fetch_public_url_status(url: str) -> int:
    """GET a public URL and return only the HTTP status code."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        return response.status_code
