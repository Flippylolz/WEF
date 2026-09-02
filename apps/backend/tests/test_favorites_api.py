"""HTTP tests for starred locations."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from tests.fakes import (
    FakeFavoriteStore,
    build_favorites_service,
    build_identity_service,
)
from tests.test_api import create_test_app
from tests.test_identity_api import register_and_login


def favorites_app(store: FakeFavoriteStore | None = None) -> FastAPI:
    """Build one app with fake favorites."""
    app = create_test_app()
    app.state.identity = build_identity_service()
    favorite_store = store or FakeFavoriteStore()
    app.state.favorites = build_favorites_service(favorite_store)
    app.state.auth_cookie_secure = False
    return app


@asynccontextmanager
async def favorite_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Exercise one favorites-enabled app while managing its lifespan."""
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client


async def test_favorites_require_authentication() -> None:
    """Reject favorites routes when no session cookie is present."""
    location_id = UUID("10000000-0000-4000-8000-000000000001")
    async with favorite_client(favorites_app()) as client:
        listed = await client.get("/api/v1/favorites")
        added = await client.put(f"/api/v1/favorites/{location_id}")
    assert listed.status_code == status.HTTP_401_UNAUTHORIZED
    assert added.status_code == status.HTTP_401_UNAUTHORIZED


async def test_add_list_and_remove_favorite() -> None:
    """Star, list, and unstar one public location for a signed-in account."""
    store = FakeFavoriteStore()
    location_id = UUID("10000000-0000-4000-8000-000000000001")
    store.public_locations.add(location_id)
    async with favorite_client(favorites_app(store)) as client:
        await register_and_login(client)
        added = await client.put(f"/api/v1/favorites/{location_id}")
        listed = await client.get("/api/v1/favorites")
        removed = await client.delete(f"/api/v1/favorites/{location_id}")
        empty = await client.get("/api/v1/favorites")
    assert added.status_code == status.HTTP_204_NO_CONTENT
    assert listed.status_code == status.HTTP_200_OK
    assert listed.headers["Cache-Control"] == "no-store, private"
    assert listed.json()["items"][0]["location_id"] == str(location_id)
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert empty.json()["items"] == []
