"""HTTP tests for authenticated visits and viewed-offer history."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from tests.fakes import (
    FakeClock,
    FakeViewHistoryStore,
    build_identity_service,
    build_view_history_service,
)
from tests.test_api import create_test_app
from tests.test_identity_api import register_and_login

_JSON_HEADERS = {"Content-Type": "application/json"}


def view_history_app(
    store: FakeViewHistoryStore | None = None,
    clock: FakeClock | None = None,
) -> FastAPI:
    """Build one app with deterministic account view history."""
    app = create_test_app()
    app.state.identity = build_identity_service()
    app.state.view_history = build_view_history_service(store, clock)
    app.state.auth_cookie_secure = False
    return app


@asynccontextmanager
async def view_history_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Exercise one view-history app with lifespan management."""
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client


async def test_view_history_requires_authentication() -> None:
    """Reject visit, list, and viewed-offer mutations without a session."""
    visit_id = UUID("30000000-0000-4000-8000-000000000001")
    offer_id = UUID("20000000-0000-4000-8000-000000000001")
    async with view_history_client(view_history_app()) as client:
        visit = await client.put(
            f"/api/v1/view-history/visits/{visit_id}",
            headers=_JSON_HEADERS,
        )
        viewed = await client.put(
            f"/api/v1/view-history/offers/{offer_id}",
            headers=_JSON_HEADERS,
        )
        listed = await client.get("/api/v1/view-history/offers")
    assert visit.status_code == status.HTTP_401_UNAUTHORIZED
    assert viewed.status_code == status.HTTP_401_UNAUTHORIZED
    assert listed.status_code == status.HTTP_401_UNAUTHORIZED


async def test_account_visit_baseline_is_cross_session_and_idempotent() -> None:
    """Capture the prior authenticated visit and keep it stable on replay."""
    clock = FakeClock(moment=datetime(2026, 8, 29, 8, 0, tzinfo=UTC))
    first_id = UUID("30000000-0000-4000-8000-000000000001")
    second_id = UUID("30000000-0000-4000-8000-000000000002")
    async with view_history_client(view_history_app(clock=clock)) as client:
        await register_and_login(client)
        first = await client.put(
            f"/api/v1/view-history/visits/{first_id}",
            headers=_JSON_HEADERS,
        )
        clock.advance(3600)
        replay = await client.put(
            f"/api/v1/view-history/visits/{first_id}",
            headers=_JSON_HEADERS,
        )
        second = await client.put(
            f"/api/v1/view-history/visits/{second_id}",
            headers=_JSON_HEADERS,
        )
    assert first.status_code == status.HTTP_200_OK
    assert first.headers["cache-control"] == "no-store, private"
    assert first.json()["previous_visit_at"] is None
    assert replay.json() == first.json()
    assert second.json()["previous_visit_at"] == first.json()["current_visit_at"]


async def test_mark_and_list_viewed_public_offers() -> None:
    """Aggregate repeated public-offer views and hide non-public identifiers."""
    offer_id = UUID("20000000-0000-4000-8000-000000000001")
    missing_id = UUID("20000000-0000-4000-8000-000000000099")
    store = FakeViewHistoryStore(public_offers={offer_id})
    clock = FakeClock(moment=datetime(2026, 8, 29, 8, 0, tzinfo=UTC))
    async with view_history_client(view_history_app(store, clock)) as client:
        await register_and_login(client)
        first = await client.put(
            f"/api/v1/view-history/offers/{offer_id}",
            headers=_JSON_HEADERS,
        )
        clock.advance(30)
        second = await client.put(
            f"/api/v1/view-history/offers/{offer_id}",
            headers=_JSON_HEADERS,
        )
        missing = await client.put(
            f"/api/v1/view-history/offers/{missing_id}",
            headers=_JSON_HEADERS,
        )
        listed = await client.get("/api/v1/view-history/offers")
    assert first.status_code == status.HTTP_200_OK
    assert first.json()["view_count"] == 1
    assert second.json()["view_count"] == 2
    assert second.json()["first_viewed_at"] == first.json()["first_viewed_at"]
    assert second.json()["last_viewed_at"] != first.json()["last_viewed_at"]
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert listed.headers["cache-control"] == "no-store, private"
    assert listed.json()["items"] == [second.json()]
