"""HTTP identity transport tests with explicit app-state doubles."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from tests.fakes import (
    FakeIdentityStore,
    FakeRateLimiter,
    build_identity_service,
)
from tests.test_api import create_test_app
from wef_backend.features.identity.infrastructure.security import PwdlibPasswordHasher


def identity_app(
    rate_limiter: FakeRateLimiter | None = None,
    *,
    secure_cookies: bool = False,
) -> FastAPI:
    """Build one app with a fake-backed identity service."""
    app = create_test_app()
    app.state.identity = build_identity_service(rate_limiter=rate_limiter)
    app.state.auth_cookie_secure = secure_cookies
    return app


@asynccontextmanager
async def auth_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Exercise an ASGI app while explicitly managing its lifespan."""
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client


async def register_and_login(
    client: AsyncClient,
    username: str = "warsaw",
    password: str = "longenough123",
) -> str:
    """Register then log in, returning the raw session cookie value."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == status.HTTP_200_OK
    return str(login.cookies["wef_session"])


async def test_register_login_me_happy_path() -> None:
    """Register, log in, and view the minimal account projection."""
    async with auth_client(identity_app()) as client:
        register = await client.post(
            "/api/v1/auth/register",
            json={"username": "WarsawUser", "password": "longenough123"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsawuser", "password": "longenough123"},
        )
        me = await client.get("/api/v1/auth/me")

    assert register.status_code == status.HTTP_201_CREATED
    payload = register.json()
    assert payload["username"] == "WarsawUser"
    assert payload["role"] == "user"
    assert payload["must_change_password"] is False
    assert set(payload) == {
        "id",
        "username",
        "role",
        "must_change_password",
        "created_at",
        "last_login_at",
    }
    assert login.status_code == status.HTTP_200_OK
    assert login.json()["id"] == payload["id"]
    cookie_header = login.headers["set-cookie"]
    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()
    assert "wef_session=" in cookie_header
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["username"] == "WarsawUser"


async def test_login_responses_never_leak_credentials_or_tokens() -> None:
    """Tokens, passwords, and hashes never appear in public responses."""
    async with auth_client(identity_app()) as client:
        token = await register_and_login(client)
        ok = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "longenough123"},
        )
        bad = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "wrongpassword1"},
        )
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "longenough123"},
        )
        client.cookies.clear()
        unauthorized_me = await client.get("/api/v1/auth/me")

    for response in (ok, bad, unknown, unauthorized_me):
        assert "longenough123" not in response.text
        assert "fakehash" not in response.text
        assert token not in response.text
    assert bad.status_code == unknown.status_code == status.HTTP_401_UNAUTHORIZED

    def redacted(body: dict[str, object]) -> dict[str, object]:
        return {k: v for k, v in body.items() if k not in {"request_id", "instance"}}

    assert redacted(bad.json()) == redacted(unknown.json())
    assert bad.json()["code"] == "invalid_credentials"
    assert unauthorized_me.status_code == status.HTTP_401_UNAUTHORIZED
    assert unauthorized_me.json()["code"] == "not_authenticated"


async def test_login_unknown_username_with_real_hasher_is_invalid_not_error() -> None:
    """Unknown usernames stay a 401 problem even with the production hasher."""
    app = identity_app()
    app.state.identity = build_identity_service(hasher=PwdlibPasswordHasher())
    async with auth_client(app) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "longenough123"},
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "invalid_credentials"


async def test_register_duplicate_username_is_reported_unavailable() -> None:
    """Registration reports unavailability without other account state."""
    async with auth_client(identity_app()) as client:
        first = await client.post(
            "/api/v1/auth/register",
            json={"username": "warsaw", "password": "longenough123"},
        )
        second = await client.post(
            "/api/v1/auth/register",
            json={"username": "WARSAW", "password": "otherlongenough"},
        )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["code"] == "username_unavailable"


async def test_logout_revokes_session_and_clears_cookie() -> None:
    """Logout revokes the session so the cookie stops working."""
    async with auth_client(identity_app()) as client:
        await register_and_login(client)
        logout = await client.post("/api/v1/auth/logout", json={})
        me_after = await client.get("/api/v1/auth/me")

    assert logout.status_code == status.HTTP_204_NO_CONTENT
    assert "Max-Age=0" in logout.headers.get("set-cookie", "")
    assert me_after.status_code == status.HTTP_401_UNAUTHORIZED


async def test_password_change_revokes_all_sessions() -> None:
    """A changed password invalidates existing sessions."""
    async with auth_client(identity_app()) as client:
        await register_and_login(client)
        changed = await client.post(
            "/api/v1/auth/password",
            json={
                "current_password": "longenough123",
                "new_password": "newlongenough456",
            },
        )
        me_after = await client.get("/api/v1/auth/me")
        relogin = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "newlongenough456"},
        )

    assert changed.status_code == status.HTTP_204_NO_CONTENT
    assert me_after.status_code == status.HTTP_401_UNAUTHORIZED
    assert relogin.status_code == status.HTTP_200_OK


async def test_revoke_all_disable_and_delete_own_account() -> None:
    """Own-account mutations revoke the session immediately."""
    async with auth_client(identity_app()) as client:
        await register_and_login(client, username="revoker")
        revoke_all = await client.post("/api/v1/auth/sessions/revoke-all", json={})
        assert revoke_all.status_code == status.HTTP_204_NO_CONTENT

        await register_and_login(client, username="disabler")
        disable = await client.post("/api/v1/auth/account/disable", json={})
        disabled_login = await client.post(
            "/api/v1/auth/login",
            json={"username": "disabler", "password": "longenough123"},
        )
        assert disable.status_code == status.HTTP_204_NO_CONTENT
        assert disabled_login.status_code == status.HTTP_401_UNAUTHORIZED

        await register_and_login(client, username="deleter")
        delete = await client.post("/api/v1/auth/account/delete", json={})
        assert delete.status_code == status.HTTP_204_NO_CONTENT


async def test_cross_origin_and_non_json_mutations_are_rejected() -> None:
    """Origin and content-type guards refuse unsafe mutations."""
    async with auth_client(identity_app()) as client:
        cross_origin = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "longenough123"},
            headers={"Origin": "https://evil.example"},
        )
        form_login = await client.post(
            "/api/v1/auth/login",
            content="username=warsaw&password=longenough123",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        same_origin = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "longenough123"},
            headers={"Origin": "http://testserver"},
        )

    assert cross_origin.status_code == status.HTTP_403_FORBIDDEN
    assert cross_origin.json()["code"] == "origin_rejected"
    assert form_login.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert same_origin.status_code in (
        status.HTTP_200_OK,
        status.HTTP_401_UNAUTHORIZED,
    )


async def test_rate_limited_auth_returns_generic_throttle() -> None:
    """Blocked clients receive one bounded throttle problem."""
    blocked = FakeRateLimiter(blocked=set())
    async with auth_client(identity_app(rate_limiter=blocked)) as client:
        await register_and_login(client, username="limited")
        blocked.blocked.add("login:127.0.0.1:limited")
        throttled = await client.post(
            "/api/v1/auth/login",
            json={"username": "limited", "password": "longenough123"},
        )

    assert throttled.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert throttled.json()["code"] == "rate_limited"
    assert "longenough123" not in throttled.text


async def test_production_cookies_are_secure() -> None:
    """Production configuration sets the Secure cookie flag."""
    async with auth_client(identity_app(secure_cookies=True)) as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "warsaw", "password": "longenough123"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "warsaw", "password": "longenough123"},
        )

    assert login.status_code == status.HTTP_200_OK
    assert "secure" in login.headers["set-cookie"].lower()


async def test_identity_service_absence_refuses_safely() -> None:
    """A missing identity service yields one bounded problem."""
    app = create_test_app()
    del app.state.identity
    async with auth_client(app) as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "identity_unavailable"


async def test_auth_paths_present_in_offline_schema() -> None:
    """Auth operations appear in the deterministic offline schema."""
    schema = identity_app().openapi()
    paths = schema["paths"]
    assert paths["/api/v1/auth/register"]["post"]["operationId"] == "registerAccount"
    assert paths["/api/v1/auth/login"]["post"]["operationId"] == "loginAccount"
    assert paths["/api/v1/auth/logout"]["post"]["operationId"] == "logoutAccount"
    assert paths["/api/v1/auth/me"]["get"]["operationId"] == "getOwnAccount"
    assert paths["/api/v1/auth/password"]["post"]["operationId"] == "changeOwnPassword"


def test_fake_identity_store_sessions_are_hash_keyed() -> None:
    """The fake store keys sessions by token hash, never raw tokens."""
    store = FakeIdentityStore()
    assert "hashed:raw-token-1" not in store.sessions
