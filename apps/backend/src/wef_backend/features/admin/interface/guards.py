"""HTTP guards for the owner administration console."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp

    from wef_backend.features.identity.application.identity import IdentityService

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_MUTATION_RATE_LIMIT = 60
_MUTATION_RATE_WINDOW_SECONDS = 60


class AdminMutationGuardMiddleware(BaseHTTPMiddleware):
    """Reject cross-origin and abusive admin mutations before views run."""

    def __init__(self, app: ASGIApp, *, identity: IdentityService) -> None:
        """Initialize the collaborator."""
        super().__init__(app)
        self._identity = identity

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Apply origin and rate-limit checks on mutating admin requests."""
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        expected = f"{request.url.scheme}://{request.url.netloc}"
        origin = request.headers.get("origin")
        if origin is not None and origin.rstrip("/") != expected.rstrip("/"):
            return PlainTextResponse("Origin rejected", status_code=403)

        referer = request.headers.get("referer")
        if origin is None and referer is not None:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin.rstrip("/") != expected.rstrip("/"):
                return PlainTextResponse("Origin rejected", status_code=403)

        host = request.client.host if request.client is not None else "unknown"
        key = f"admin-mutation:{host}"
        if not self._identity.rate_limiter.allow(
            key,
            limit=_MUTATION_RATE_LIMIT,
            window_seconds=_MUTATION_RATE_WINDOW_SECONDS,
        ):
            return PlainTextResponse("Too many requests", status_code=429)

        return await call_next(request)
