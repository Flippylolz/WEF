"""Release integration-test database resources before their event loop closes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from wef_backend import database

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


@pytest.fixture(autouse=True)
async def close_test_database_resources(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Own engines created by test applications even when a lifespan was not entered."""
    engines: list[AsyncEngine] = []
    sessions: list[AsyncSession] = []
    initialize: Callable[..., None] = AsyncSession.__init__

    def tracked_session(session: AsyncSession, *args: object, **kwargs: object) -> None:
        initialize(session, *args, **kwargs)
        sessions.append(session)

    monkeypatch.setattr(AsyncSession, "__init__", tracked_session)
    create = create_async_engine

    def tracked_engine(url: str, *, pool_pre_ping: bool) -> AsyncEngine:
        engine = create(url, pool_pre_ping=pool_pre_ping)
        engines.append(engine)
        return engine

    dispose = AsyncEngine.dispose

    async def dispose_after_sessions(engine: AsyncEngine, *, close: bool = True) -> None:
        # Test helpers may dispose a pool before exiting retained ORM sessions.
        # Release sessions first so disposal cannot detach still-open connections.
        for session in sessions:
            if session.bind is engine:
                await session.close()
        await dispose(engine, close=close)

    monkeypatch.setattr(AsyncEngine, "dispose", dispose_after_sessions)
    monkeypatch.setattr(database, "create_async_engine", tracked_engine)
    yield
    for session in sessions:
        await session.close()
    for engine in engines:
        await engine.dispose()
