"""Lazy SQLAlchemy asyncio resource construction."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True, slots=True)
class DatabaseResources:
    """Database resources created without opening a connection."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


def create_database_resources(database_url: str) -> DatabaseResources:
    """Create a lazy engine and its typed async session factory."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return DatabaseResources(
        engine=engine,
        session_factory=async_sessionmaker(engine, expire_on_commit=False),
    )
