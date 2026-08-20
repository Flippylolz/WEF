"""HTTP contact reveal transport tests."""

from uuid import uuid4

from fastapi import status

from tests.fakes import (
    FakeContactStore,
    FakeRateLimiter,
    build_contact_service,
    build_identity_service,
)
from tests.test_api import create_test_app
from tests.test_identity_api import auth_client, register_and_login
from wef_backend.features.contacts.application.reveal import ContactInput, build_contact_records
from wef_backend.features.contacts.domain.model import ContactKind
from wef_backend.features.contacts.infrastructure.crypto import (
    AesGcmContactCipher,
    decode_secret_key,
)


async def test_reveal_requires_auth_and_returns_no_store() -> None:
    """Anonymous callers are rejected; success responses are no-store."""
    offer_id = uuid4()
    key = decode_secret_key("aa" * 32)
    hmac_key = decode_secret_key("bb" * 32)
    assert key is not None
    assert hmac_key is not None
    cipher = AesGcmContactCipher(encryption_key=key, hmac_key=hmac_key)
    store = FakeContactStore(visible_offers={offer_id})
    records = build_contact_records(
        cipher,
        offer_id=offer_id,
        source_message_id=uuid4(),
        contacts=(
            ContactInput(kind=ContactKind.PHONE, value="+48123456789"),
            ContactInput(kind=ContactKind.TELEGRAM, value="@agent"),
        ),
    )
    store.contacts[offer_id] = list(records)
    app = create_test_app()
    app.state.identity = build_identity_service()
    app.state.contacts = build_contact_service(store=store, cipher=cipher)

    async with auth_client(app) as client:
        anonymous = await client.post(
            f"/api/v1/offers/{offer_id}/contacts/reveal",
            json={},
        )
        await register_and_login(client)
        ok = await client.post(
            f"/api/v1/offers/{offer_id}/contacts/reveal",
            json={},
        )
        missing = await client.post(
            f"/api/v1/offers/{uuid4()}/contacts/reveal",
            json={},
        )

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert ok.status_code == status.HTTP_200_OK
    assert ok.headers["cache-control"] == "no-store, private"
    body = ok.json()
    assert {item["value"] for item in body["contacts"]} == {"+48123456789", "@agent"}
    assert "+48123456789" not in str(store.audits)
    assert missing.status_code == status.HTTP_404_NOT_FOUND


async def test_reveal_rate_limit_and_openapi_path() -> None:
    """Per-account rate limits return 429 and the path is exported."""
    offer_id = uuid4()
    store = FakeContactStore(visible_offers={offer_id})
    app = create_test_app()
    identity = build_identity_service()
    app.state.identity = identity
    app.state.contacts = build_contact_service(
        store=store,
        rate_limiter=FakeRateLimiter(),
    )

    async with auth_client(app) as client:
        token_user = await register_and_login(client, username="revealer")
        # Replace limiter after login so the key matches the resolved account.
        me = await client.get("/api/v1/auth/me")
        user_id = me.json()["id"]
        app.state.contacts = build_contact_service(
            store=store,
            rate_limiter=FakeRateLimiter(blocked={f"reveal:{user_id}"}),
        )
        limited = await client.post(
            f"/api/v1/offers/{offer_id}/contacts/reveal",
            json={},
            cookies={"wef_session": token_user},
        )

    assert limited.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    schema = create_test_app().openapi()
    assert "/api/v1/offers/{offer_id}/contacts/reveal" in schema["paths"]
