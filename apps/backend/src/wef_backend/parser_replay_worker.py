"""Optional accepted-parser maintenance in the existing live worker lifecycle."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from wef_backend.features.ingestion.application.parser_replay import replay_populations
from wef_backend.features.ingestion.infrastructure.parser_replay import SQLAlchemyParserReplay

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.settings import Settings

logger = structlog.get_logger("wef.parser_replay")


async def maintain_parser_replay(
    settings: Settings,
    sessions: async_sessionmaker[AsyncSession],
    stop: asyncio.Event,
    live_ready: Callable[[], bool],
) -> None:
    """Keep scheduling/application independently paused and yield to live ingestion."""
    replay = SQLAlchemyParserReplay(sessions)
    previous: dict[str, int] | str | None = None
    while not stop.is_set():
        if settings.parser_replay_enabled and live_ready():
            try:
                await replay.tick(
                    datetime.now(UTC),
                    apply=settings.parser_replay_auto_apply,
                    live_ready=live_ready,
                )
                counts = await replay.counts()
                if counts != previous:
                    logger.info(
                        "parser_replay_progress", **replay_populations(counts), states=counts
                    )
                    previous = counts
            except Exception:  # noqa: BLE001 - optional maintenance must not kill ingestion
                if previous != "failed":
                    logger.warning("parser_replay_unavailable")
                    previous = "failed"
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=60)
