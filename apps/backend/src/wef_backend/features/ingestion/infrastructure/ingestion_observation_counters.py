"""Transaction-local observation counters with an explicit instrumentation start."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def record_observation(session: AsyncSession, channel: str, name: str) -> None:
    """Increment an observation only if its owning archive transaction commits."""
    await session.execute(
        text(
            "INSERT INTO ingestion_observation_counters(channel,name,value) VALUES "
            "(:channel,:name,1) ON CONFLICT(channel,name) DO UPDATE SET "
            "value=ingestion_observation_counters.value+1"
        ),
        {"channel": channel, "name": name},
    )
