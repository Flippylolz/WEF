"""HTTP adapters preserve unavailable, throttled and refused outcome semantics."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.exceptions import LoginFailed

from tests.fakes import FakeRateLimiter, build_identity_service
from tests.test_api import create_test_app
from tests.test_identity_api import auth_client, identity_app, register_and_login
from wef_backend.features.admin.interface.auth import OwnerAuthProvider
from wef_backend.features.admin.interface.guards import AdminMutationGuardMiddleware
from wef_backend.features.catalog.interface.presenter import _required_coordinate
from wef_backend.features.contacts.application.reveal import RevealResult
from wef_backend.features.contacts.domain.model import RevealOutcome
from wef_backend.features.identity.application.identity import InvalidCredentialsError
from wef_backend.features.identity.domain.model import PasswordPolicyError, UserRole


def _request(*, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/admin/action",
            "server": ("testserver", 443),
            "headers": headers or [],
            "session": {},
        }
    )


@pytest.mark.parametrize("mode", ["throttled", "non_owner", "password_change"])
async def test_admin_authentication_refuses_disallowed_owner_sessions(mode: str) -> None:
    identity = MagicMock()
    account = MagicMock(
        role=UserRole.USER if mode == "non_owner" else UserRole.OWNER,
        must_change_password=mode == "password_change",
    )
    identity.rate_limiter.allow.return_value = mode != "throttled"
    identity.authenticate = AsyncMock(return_value=MagicMock(account=account))
    identity.resolve_session = AsyncMock(return_value=account)
    provider = OwnerAuthProvider(identity, MagicMock(), cookie_secure=True)
    with pytest.raises(LoginFailed):
        await provider.login(
            "synthetic", "synthetic password", remember_me=False, request=_request()
        )
    if mode == "throttled":
        identity.authenticate.assert_not_awaited()
    else:
        assert await provider.authenticate(_request()) is None


@pytest.mark.parametrize("mode", ["same_referer", "unknown_client", "throttled"])
async def test_admin_mutation_origin_and_rate_controls_without_client_address(mode: str) -> None:
    identity = MagicMock()
    identity.rate_limiter.allow.return_value = mode != "throttled"
    middleware = AdminMutationGuardMiddleware(MagicMock(), identity=identity)
    request = _request(
        headers=[(b"referer", b"https://testserver/admin/")] if mode == "same_referer" else [],
    )
    next_handler = AsyncMock(return_value=Response(status_code=204))
    response = await middleware.dispatch(request, next_handler)
    assert response.status_code == (429 if mode == "throttled" else 204)
    assert next_handler.await_count == int(mode != "throttled")
    assert identity.rate_limiter.allow.call_args.args == ("admin-mutation:unknown",)


@pytest.mark.parametrize(
    ("service", "path", "method"),
    [
        ("favorites", "/api/v1/favorites", "GET"),
        ("contacts", "/api/v1/offers/{id}/contacts/reveal", "POST"),
        ("view_history", "/api/v1/view-history/offers", "GET"),
    ],
)
async def test_authenticated_requests_refuse_absent_optional_service(
    service: str,
    path: str,
    method: str,
) -> None:
    app = create_test_app()
    app.state.identity = build_identity_service()
    setattr(app.state, service, None)
    async with auth_client(app) as client:
        await register_and_login(client)
        response = await client.request(
            method, path.format(id=uuid4()), json={} if method == "POST" else None
        )
    assert response.status_code == 503
    assert response.json()["code"] == f"{service}_unavailable"


async def test_favorite_unknown_location_is_not_found() -> None:
    app = identity_app()
    app.state.favorites = MagicMock(add_favorite=AsyncMock(return_value=False))
    async with auth_client(app) as client:
        await register_and_login(client)
        response = await client.put(f"/api/v1/favorites/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (RevealOutcome.UNAVAILABLE, 503),
        (RevealOutcome.FORBIDDEN, 403),
    ],
)
async def test_contact_reveal_refusals_keep_empty_private_response(
    outcome: RevealOutcome, status: int
) -> None:
    app = identity_app()
    app.state.contacts = MagicMock(reveal=AsyncMock(return_value=RevealResult(outcome)))
    async with auth_client(app) as client:
        await register_and_login(client)
        response = await client.post(f"/api/v1/offers/{uuid4()}/contacts/reveal", json={})
    assert response.status_code == status
    assert "contacts" not in response.json()


async def test_registration_throttle_rejects_before_creating_account() -> None:
    app = identity_app(FakeRateLimiter(blocked={"register:127.0.0.1:synthetic"}))
    async with auth_client(app) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "synthetic", "password": "longenough123"},
        )
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (InvalidCredentialsError, 401),
        (PasswordPolicyError, 422),
        (None, 429),
    ],
)
async def test_password_change_maps_typed_refusals_and_throttle(
    failure: type[Exception] | None,
    status: int,
) -> None:
    app = identity_app()
    async with auth_client(app) as client:
        await register_and_login(client)
        me = await client.get("/api/v1/auth/me")
        change = AsyncMock(side_effect=failure() if failure else None)
        app.state.identity = replace(
            app.state.identity,
            change_password=change,
            rate_limiter=FakeRateLimiter(
                blocked={f"password:127.0.0.1:{me.json()['id']}"} if failure is None else set(),
            ),
        )
        response = await client.post(
            "/api/v1/auth/password",
            json={"current_password": "longenough123", "new_password": "different1234"},
        )
    assert response.status_code == status
    assert change.await_count == int(failure is not None)


async def test_quick_filter_endpoint_presents_server_presets_and_cache_policy() -> None:
    async with auth_client(create_test_app()) as client:
        response = await client.get("/api/v1/quick-filters")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60"
    assert response.json()["items"]


def test_presenter_refuses_missing_mapped_coordinate() -> None:
    with pytest.raises(ValueError, match="missing a coordinate"):
        _required_coordinate(None)
