"""Explicit composition root for runtime services."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.database import create_database_resources
from wef_backend.features.estates.application import ListEstates
from wef_backend.features.estates.infrastructure import SQLAlchemyEstateQueryAdapter
from wef_backend.settings import Settings, load_settings

ReadyCheck = Callable[[], Awaitable[bool]]
ResourceCloser = Callable[[], Awaitable[None]]

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class AppServices:
    """Fully composed services placed on FastAPI app state."""

    list_estates: ListEstates
    is_ready: ReadyCheck
    close: ResourceCloser


def build_services(settings: Settings | None = None) -> AppServices:
    """Wire concrete adapters to inward-owned application contracts."""
    runtime_settings = settings or load_settings()
    database = create_database_resources(runtime_settings.database_url)
    estate_adapter = SQLAlchemyEstateQueryAdapter(database.session_factory)

    async def database_is_ready() -> bool:
        try:
            async with database.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            logger.warning("database_not_ready", error=str(error))
            return False
        return True

    return AppServices(
        list_estates=ListEstates(estate_adapter),
        is_ready=database_is_ready,
        close=database.engine.dispose,
    )
