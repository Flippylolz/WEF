from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import Request, Response

from wef_backend.errors import RateLimitExceededError

_PUBLIC_READ_LIMITS: tuple[tuple[str, int, int], ...] = (
    ("/api/v1/map/locations", 120, 60),
    ("/api/v1/filter-facets", 60, 60),
    ("/api/v1/quick-filters", 60, 60),
    ("/api/v1/locations/", 90, 60),
    ("/api/v1/offers/", 90, 60),
)


class RateLimiter(Protocol):
    """Minimal throttle contract shared by production and test doubles."""

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Return whether one request is allowed inside the window."""


def _client_key(request: Request) -> str:
    host = request.client.host if request.client else "anonymous"
    return hashlib.sha256(host.encode()).hexdigest()[:16]


def _limit_for_path(path: str) -> tuple[str, int, int] | None:
    for prefix, limit, window in _PUBLIC_READ_LIMITS:
        if path == prefix or path.startswith(prefix):
            return prefix, limit, window
    return None


def build_public_rate_limit_middleware(
    limiter: RateLimiter,
) -> Callable[
    [Request, Callable[[Request], Awaitable[Response]]],
    Awaitable[Response],
]:
    """Return middleware that throttles bounded public catalog reads."""

    async def enforce_public_rate_limit(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        matched = _limit_for_path(request.url.path)
        if matched is not None:
            prefix, limit, window = matched
            key = f"{prefix}:{_client_key(request)}"
            if not limiter.allow(key, limit=limit, window_seconds=window):
                raise RateLimitExceededError
        return await call_next(request)

    return enforce_public_rate_limit
