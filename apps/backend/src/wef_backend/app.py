"""FastAPI application factories."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError

from wef_backend.composition import AppServices, build_services
from wef_backend.errors import (
    AuthProblemError,
    QueryValidationError,
    RateLimitExceededError,
    ResourceNotFoundError,
    auth_problem_handler,
    query_validation_handler,
    rate_limit_handler,
    request_validation_handler,
    resource_not_found_handler,
)
from wef_backend.features.admin.interface import build_admin
from wef_backend.features.catalog.interface import (
    facets_router,
    locations_router,
    offers_router,
)
from wef_backend.features.catalog.interface import router as catalog_router
from wef_backend.features.contacts.interface import contacts_router
from wef_backend.features.estates.interface import router as estates_router
from wef_backend.features.identity.interface import identity_router
from wef_backend.features.identity.interface.favorites_router import (
    router as favorites_router,
)
from wef_backend.health import router as health_router
from wef_backend.logging_config import build_access_log_middleware, configure_logging
from wef_backend.middleware.public_rate_limit import build_public_rate_limit_middleware
from wef_backend.settings import load_settings


def create_http_app(services: AppServices | None = None) -> FastAPI:
    """Create the transport app, optionally with explicitly supplied services."""
    settings = load_settings()
    configure_logging(
        level=settings.log_level,
        json_logs=settings.env == "production",
    )

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
    app.include_router(facets_router)
    app.include_router(locations_router)
    app.include_router(offers_router)
    app.include_router(estates_router)
    app.include_router(identity_router)
    app.include_router(favorites_router)
    app.include_router(contacts_router)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(QueryValidationError, query_validation_handler)
    app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)
    app.add_exception_handler(AuthProblemError, auth_problem_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_handler)

    if services is not None:
        app.middleware("http")(build_public_rate_limit_middleware(services.public_rate_limiter))
        app.state.list_estates = services.list_estates
        app.state.query_map = services.query_map
        app.state.query_facets = services.query_facets
        app.state.browse_location_offers = services.browse_location_offers
        app.state.get_offer_detail = services.get_offer_detail
        app.state.is_ready = services.is_ready
        app.state.identity = services.identity
        app.state.favorites = services.favorites
        app.state.contacts = services.contacts
        app.state.admin = services.admin
        app.state.auth_cookie_secure = services.auth_cookie_secure
        admin = build_admin(
            secret_key=services.admin_session_secret,
            identity=services.identity,
            admin=services.admin,
            cookie_secure=services.auth_cookie_secure,
        )
        admin.mount_to(app)

    app.middleware("http")(
        build_access_log_middleware(release_sha=settings.release_sha),
    )

    @app.middleware("http")
    async def attach_request_identity(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Attach one safe correlation identifier to every response."""
        request.state.request_id = uuid4()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=str(request.state.request_id),
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        if request.url.path.startswith("/admin"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def create_app() -> FastAPI:
    """Create the runtime application through the composition root."""
    return create_http_app(build_services())
