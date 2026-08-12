"""FastAPI application factories."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from wef_backend.composition import AppServices, build_services
from wef_backend.features.estates.interface import router as estates_router
from wef_backend.health import router as health_router


def create_http_app(services: AppServices | None = None) -> FastAPI:
    """Create the transport app, optionally with explicitly supplied services."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if services is not None:
            await services.close()

    app = FastAPI(
        title="WEF synthetic backend proof",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(estates_router)

    if services is not None:
        app.state.list_estates = services.list_estates
        app.state.is_ready = services.is_ready

    return app


def create_app() -> FastAPI:
    """Create the runtime application through the composition root."""
    return create_http_app(build_services())
