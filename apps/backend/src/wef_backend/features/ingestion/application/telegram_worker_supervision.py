"""Fail-fast supervision for the Telegram worker's critical async stages."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    from collections.abc import Awaitable, Mapping


class CriticalWorkerTaskError(RuntimeError):
    """One required worker stage failed or exited unexpectedly."""

    def __init__(self, *, stage: str, category: str) -> None:
        """Retain one bounded stage and category for operator diagnostics."""
        self.stage = stage
        self.category = category
        super().__init__(f"critical worker stage failed: {stage} ({category})")


@dataclass(frozen=True, slots=True)
class CriticalWorkerTask:
    """Named awaitable that must not finish during normal worker operation."""

    stage: str
    awaitable: Awaitable[None]


async def _require_running(task: CriticalWorkerTask) -> None:
    try:
        await task.awaitable
    except asyncio.CancelledError:
        raise
    except Exception as error:
        raise CriticalWorkerTaskError(
            stage=task.stage,
            category=safe_error_category(error),
        ) from error
    raise CriticalWorkerTaskError(stage=task.stage, category="UnexpectedTaskExit")


async def supervise_worker_tasks(
    tasks: Mapping[str, Awaitable[None]],
    *,
    stop: asyncio.Event,
) -> None:
    """Cancel every sibling as soon as one critical stage fails or exits."""
    if not tasks:
        message = "at least one critical worker task is required"
        raise ValueError(message)
    running = [
        asyncio.create_task(
            _require_running(CriticalWorkerTask(stage=stage, awaitable=awaitable)),
            name=f"telegram-worker:{stage}",
        )
        for stage, awaitable in tasks.items()
    ]
    try:
        done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        winner = next(task for task in running if task in done)
        await winner
    finally:
        stop.set()
        for task in running:
            if not task.done():
                task.cancel()
        await asyncio.gather(*running, return_exceptions=True)


async def maintain_pending_reconciliation_slot(stop: asyncio.Event) -> None:
    """Hold the supervised T1 lifecycle slot without claiming reconciliation work."""
    await stop.wait()
