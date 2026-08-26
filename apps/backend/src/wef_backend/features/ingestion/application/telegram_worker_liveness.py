"""Listen-loop heartbeat for telegram-worker Compose healthchecks."""

from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    DEFAULT_HEARTBEAT_MAX_AGE,
    HEARTBEAT_INTERVAL_SECONDS,
    heartbeat_is_fresh,
    parse_heartbeat_timestamp,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import timedelta
    from pathlib import Path


def write_worker_heartbeat(path: Path, *, now: datetime | None = None) -> None:
    """Atomically write the current listen-loop timestamp."""
    current = (now or datetime.now(UTC)).astimezone(UTC)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(current.isoformat(), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def worker_liveness_ok(
    path: Path,
    *,
    now: datetime | None = None,
    max_age: timedelta = DEFAULT_HEARTBEAT_MAX_AGE,
) -> bool:
    """Return True when a fresh listen-loop heartbeat file is present."""
    if not path.is_file():
        return False
    try:
        written = parse_heartbeat_timestamp(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return heartbeat_is_fresh(written, now=now or datetime.now(UTC), max_age=max_age)


async def maintain_worker_heartbeat(
    path: Path,
    *,
    is_connected: Callable[[], bool],
    stop: asyncio.Event,
    interval: float = HEARTBEAT_INTERVAL_SECONDS,
) -> None:
    """Refresh the heartbeat while Telethon is connected; remove it on stop."""
    try:
        while not stop.is_set():
            if is_connected():
                with suppress(OSError):
                    write_worker_heartbeat(path)
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                continue
    finally:
        path.unlink(missing_ok=True)  # noqa: ASYNC240
