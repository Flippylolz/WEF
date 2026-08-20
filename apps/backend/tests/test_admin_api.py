"""HTTP smoke tests for the owner Starlette Admin console."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from re import search

from httpx import ASGITransport, AsyncClient, Response

from tests.fakes import (
    FakeCatalogBrowse,
    FakeEstateQuery,
    FakeIdentityStore,
    FakeMapQuery,
    FakeOfferDetailQuery,
    always_ready,
    build_admin_service,
    build_contact_service,
    build_favorites_service,
    build_identity_service,
    close_nothing,
    empty_facet_snapshot,
)
from wef_backend.app import create_http_app
from wef_backend.composition import AppServices
from wef_backend.features.catalog.application import (
    BrowseLocationOffers,
    GetOfferDetail,
    QueryFacets,
    QueryMapLocations,
)
from wef_backend.features.estates.application import ListEstates
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure import MemoryRateLimiter


@asynccontextmanager
async def admin_client(
    *,
    store: FakeIdentityStore | None = None,
) -> AsyncIterator[tuple[AsyncClient, FakeIdentityStore]]:
    identity_store = store or FakeIdentityStore()
    services = AppServices(
        list_estates=ListEstates(FakeEstateQuery(records=())),
        query_map=QueryMapLocations(FakeMapQuery()),
        query_facets=QueryFacets(FakeCatalogBrowse(facets=empty_facet_snapshot())),
        browse_location_offers=BrowseLocationOffers(
            FakeCatalogBrowse(facets=empty_facet_snapshot()),
        ),
        get_offer_detail=GetOfferDetail(FakeOfferDetailQuery()),
        is_ready=always_ready,
        close=close_nothing,
        identity=build_identity_service(store=identity_store),
        favorites=build_favorites_service(),
        contacts=build_contact_service(),
        admin=build_admin_service(store=identity_store),
        auth_cookie_secure=False,
        admin_session_secret="test-admin-session-secret",
        public_rate_limiter=MemoryRateLimiter(),
    )
    app = create_http_app(services)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client, identity_store


def _csrf_from_html(html: str) -> str:
    match = search(
        r'name=["\']csrftoken["\']\s+value=["\']([^"\']+)["\']',
        html,
    )
    assert match is not None
    return match.group(1)


async def _login_with_csrf(
    client: AsyncClient,
    *,
    username: str,
    password: str,
) -> Response:
    login_page = await client.get("/admin/login")
    assert login_page.status_code == 200
    return await client.post(
        "/admin/login",
        data={
            "username": username,
            "password": password,
            "csrftoken": _csrf_from_html(login_page.text),
        },
        follow_redirects=False,
    )


async def _owner_session(client: AsyncClient, store: FakeIdentityStore) -> None:
    await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="fakehash:longenough123",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    login = await _login_with_csrf(
        client,
        username="owner",
        password="longenough123",
    )
    assert login.status_code in {302, 303}


async def test_admin_login_requires_owner_role() -> None:
    async with admin_client() as (client, store):
        await store.create_account(
            username_normalized="buyer",
            username_display="buyer",
            hashed_password="fakehash:longenough123",
            role=UserRole.USER,
            must_change_password=False,
        )
        response = await _login_with_csrf(
            client,
            username="buyer",
            password="longenough123",
        )
        assert response.status_code in {400, 422}
        protected = await client.get("/admin/users", follow_redirects=False)
        assert protected.status_code in {302, 303, 401, 403}


async def test_owner_can_open_admin_users_after_login() -> None:
    async with admin_client() as (client, store):
        await _owner_session(client, store)
        users = await client.get("/admin/users")
        assert users.status_code == 200
        assert "Cache-Control" in users.headers
        assert "no-store" in users.headers["Cache-Control"]
        assert b"owner" in users.content
        assert b"fakehash" not in users.content
        assert b"csrftoken" in users.content


async def test_admin_mutation_requires_csrf() -> None:
    async with admin_client() as (client, store):
        await _owner_session(client, store)
        user = await store.create_account(
            username_normalized="buyer",
            username_display="buyer",
            hashed_password="fakehash:longenough123",
            role=UserRole.USER,
            must_change_password=False,
        )
        denied = await client.post(
            "/admin/users/disable",
            data={"user_id": str(user.id)},
            follow_redirects=False,
        )
        assert denied.status_code == 403
        assert "CSRF" in denied.text


async def test_admin_mutation_rejects_cross_origin() -> None:
    async with admin_client() as (client, store):
        await _owner_session(client, store)
        users = await client.get("/admin/users")
        csrf = _csrf_from_html(users.text)
        user = await store.create_account(
            username_normalized="buyer",
            username_display="buyer",
            hashed_password="fakehash:longenough123",
            role=UserRole.USER,
            must_change_password=False,
        )
        denied = await client.post(
            "/admin/users/disable",
            data={"user_id": str(user.id), "csrftoken": csrf},
            headers={"Origin": "https://evil.example"},
            follow_redirects=False,
        )
        assert denied.status_code == 403
        assert "Origin" in denied.text


async def test_owner_disable_action_writes_audit_and_omits_secrets() -> None:
    async with admin_client() as (client, store):
        await _owner_session(client, store)
        user = await store.create_account(
            username_normalized="buyer",
            username_display="buyer",
            hashed_password="fakehash:longenough123",
            role=UserRole.USER,
            must_change_password=False,
        )
        users = await client.get("/admin/users")
        csrf = _csrf_from_html(users.text)
        response = await client.post(
            "/admin/users/disable",
            data={"user_id": str(user.id), "csrftoken": csrf},
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}
        refreshed = await store.find_account_by_id(user.id)
        assert refreshed is not None
        assert refreshed.is_active is False
        audits = await client.get("/admin/admin-audits")
        assert audits.status_code == 200
        assert b"disable_user" in audits.content
        assert b"fakehash" not in audits.content
