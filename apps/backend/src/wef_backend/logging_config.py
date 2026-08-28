"""Structlog configuration and request access logging helpers."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response

_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|authorization|cookie|api[_-]?key)\b\s*[:=]\s*\S+(?:\s+\S+)*",
)


class _SafeTelethonLogHandler(logging.Handler):
    """Bridge Telethon levels without rendering messages, args, or exceptions."""

    def emit(self, record: logging.LogRecord) -> None:
        structlog.get_logger("wef.telegram").warning(
            "telethon_runtime_diagnostic",
            category="TelethonRuntimeWarning",
            source_logger=record.name[:64],
            source_level=record.levelname,
        )


def scrub_log_value(value: object) -> object:
    """Remove credential-like substrings from log field values."""
    if isinstance(value, str):
        return _SECRET_PATTERN.sub(r"\1=***", value)
    if isinstance(value, dict):
        return {str(key): scrub_log_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_log_value(item) for item in value]
    return value


def scrub_event_dict(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that scrubs sensitive substrings from event fields."""
    return {key: scrub_log_value(value) for key, value in event_dict.items()}


def configure_logging(*, level: str = "info", json_logs: bool = True) -> None:
    """Configure process-wide structlog for WEF API processes."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        scrub_event_dict,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_safe_telethon_logging(*, level: str = "warning") -> None:
    """Install one privacy-safe Telethon bridge for this worker process."""
    telethon_logger = logging.getLogger("telethon")
    telethon_logger.handlers.clear()
    telethon_logger.addHandler(_SafeTelethonLogHandler())
    telethon_logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
    telethon_logger.propagate = False


def build_access_log_middleware(
    *,
    release_sha: str | None,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Return middleware that emits one redacted access log per request."""
    logger = structlog.get_logger("wef.access")

    async def access_log_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            release_sha=(release_sha or "")[:12] or None,
        )
        return response

    return access_log_middleware
