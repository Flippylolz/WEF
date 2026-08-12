"""FastAPI application factories."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError

from wef_backend.composition import AppServices, build_services
from wef_backend.errors import (
    QueryValidationError,
    query_validation_handler,
    request_validation_handler,
)
from wef_backend.features.catalog.interface import router as catalog_router
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
        title="Warsaw Estate Finder API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(estates_router)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(QueryValidationError, query_validation_handler)

    @app.middleware("http")
    async def attach_request_identity(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Attach one safe correlation identifier to every response."""
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    if services is not None:
        app.state.list_estates = services.list_estates
        app.state.query_map = services.query_map
        app.state.is_ready = services.is_ready

    return app


def create_app() -> FastAPI:
    """Create the runtime application through the composition root."""
    return create_http_app(build_services())
