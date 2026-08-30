"""Identity interactor unit tests over in-memory fakes."""

from datetime import timedelta

import pytest

from tests.fakes import (
    FakeClock,
    FakeHasher,
    FakeIdentityStore,
    FakeRateLimiter,
    FakeTokens,
    build_identity_service,
)
from wef_backend.features.identity.application.identity import (
    AuthenticateAccount,
    BootstrapOwner,
    BootstrapOwnerError,
    InvalidCredentialsError,
    RegistrationDeclinedError,
)
from wef_backend.features.identity.domain.model import (
    Account,
    PasswordPolicyError,
    UserRole,
)
from wef_backend.features.identity.infrastructure.security import (
    MemoryRateLimiter,
    PwdlibPasswordHasher,
)


async def test_register_creates_user_role_account_with_normalized_username() -> None:
    """Registration normalizes the username and hashes the password."""
    store = FakeIdentityStore()
    service = build_identity_service(store=store)
    view = await service.register(username="  WarsawUser ", password="longenough123")
    assert view.username == "WarsawUser"
    account = store.accounts["warsawuser"]
    assert account.role is UserRole.USER
    assert account.hashed_password == "fakehash:longenough123"
    assert account.must_change_password is False


async def test_register_declines_duplicate_and_invalid_input() -> None:
    """Duplicate usernames and policy violations are declined."""
    store = FakeIdentityStore()
    service = build_identity_service(store=store)
    await service.register(username="warsaw", password="longenough123")
    with pytest.raises(RegistrationDeclinedError, match="username unavailable"):
        await service.register(username="WARSAW", password="otherlongenough")
    with pytest.raises(RegistrationDeclinedError, match="registration declined"):
        await service.register(username="no", password="longenough123")


async def test_authenticate_establishes_session_and_records_login() -> None:
    """Login returns a raw token while persisting only its hash."""
    store = FakeIdentityStore()
    tokens = FakeTokens()
    clock = FakeClock()
    service = build_identity_service(store=store, tokens=tokens, clock=clock)
    await service.register(username="warsaw", password="longenough123")
    result = await service.authenticate(
        username="WARSAW",
        password="longenough123",
    )
    assert result.account.username == "warsaw"
    assert result.raw_token == "raw-token-1"
    assert result.ttl_seconds == 3600
    assert result.expires_at == clock.now() + timedelta(seconds=3600)
    assert "hashed:raw-token-1" in store.sessions
    assert "raw-token-1" not in {str(key) for key in store.sessions}
    assert store.accounts["warsaw"].last_login_at == clock.now()


async def test_authenticate_failures_are_indistinguishable() -> None:
    """Unknown user, wrong password, and disabled account match exactly."""
    store = FakeIdentityStore()
    service = build_identity_service(store=store)
    await service.register(username="warsaw", password="longenough123")
    messages = set()
    for username, password in [
        ("ghost", "longenough123"),
        ("warsaw", "wrongpassword1"),
        ("nope", "nope"),
    ]:
        with pytest.raises(InvalidCredentialsError) as error:
            await service.authenticate(username=username, password=password)
        messages.add(str(error.value))
    assert messages == {"invalid credentials"}
    disabled = store.accounts["warsaw"]
    store.accounts["warsaw"] = Account(
        id=disabled.id,
        username_normalized=disabled.username_normalized,
        username_display=disabled.username_display,
        hashed_password=disabled.hashed_password,
        role=disabled.role,
        is_active=False,
        must_change_password=disabled.must_change_password,
        created_at=disabled.created_at,
        updated_at=disabled.updated_at,
        last_login_at=disabled.last_login_at,
        disabled_at=disabled.updated_at,
        deleted_at=None,
    )
    with pytest.raises(InvalidCredentialsError, match="invalid credentials"):
        await service.authenticate(username="warsaw", password="longenough123")


async def test_resolve_session_enforces_expiry_and_revocation() -> None:
    """Expired, revoked, and unknown tokens resolve to None."""
    store = FakeIdentityStore()
    tokens = FakeTokens()
    clock = FakeClock()
    service = build_identity_service(store=store, tokens=tokens, clock=clock)
    await service.register(username="warsaw", password="longenough123")
    result = await service.authenticate(username="warsaw", password="longenough123")
    assert await service.resolve_session(result.raw_token) is not None
    clock.advance(3601)
    assert await service.resolve_session(result.raw_token) is None
    clock.advance(-3601)
    await service.logout(result.raw_token)
    assert await service.resolve_session(result.raw_token) is None
    assert await service.resolve_session("raw-token-999") is None
    assert await service.resolve_session("") is None
    assert await service.resolve_session("x" * 129) is None


async def test_logout_is_idempotent() -> None:
    """Repeated logout calls never raise."""
    service = build_identity_service()
    await service.logout("")
    await service.logout("raw-token-404")


async def test_change_password_verifies_rotates_and_revokes() -> None:
    """Password change verifies the current password and revokes sessions."""
    store = FakeIdentityStore()
    tokens = FakeTokens()
    service = build_identity_service(store=store, tokens=tokens)
    await service.register(username="warsaw", password="longenough123")
    first = await service.authenticate(username="warsaw", password="longenough123")
    second = await service.authenticate(username="warsaw", password="longenough123")
    account_id = store.accounts["warsaw"].id
    with pytest.raises(InvalidCredentialsError):
        await service.change_password(
            account_id=account_id,
            current_password="wrongpassword1",
            new_password="newlongenough456",
        )
    await service.change_password(
        account_id=account_id,
        current_password="longenough123",
        new_password="newlongenough456",
    )
    assert store.accounts["warsaw"].hashed_password == "fakehash:newlongenough456"
    assert store.accounts["warsaw"].must_change_password is False
    assert await service.resolve_session(first.raw_token) is None
    assert await service.resolve_session(second.raw_token) is None
    with pytest.raises(PasswordPolicyError):
        await service.change_password(
            account_id=account_id,
            current_password="newlongenough456",
            new_password="short",
        )
    fresh = await service.authenticate(
        username="warsaw",
        password="newlongenough456",
    )
    assert await service.resolve_session(fresh.raw_token) is not None


async def test_revoke_disable_and_delete_own_account() -> None:
    """Own-account mutations revoke sessions and mark lifecycle state."""
    store = FakeIdentityStore()
    service = build_identity_service(store=store)
    await service.register(username="warsaw", password="longenough123")
    result = await service.authenticate(username="warsaw", password="longenough123")
    account_id = store.accounts["warsaw"].id
    assert await service.resolve_session(result.raw_token) is not None
    await service.revoke_all_sessions(account_id)
    assert await service.resolve_session(result.raw_token) is None
    again = await service.authenticate(username="warsaw", password="longenough123")
    await service.disable_account(account_id)
    assert store.accounts["warsaw"].is_active is False
    assert store.accounts["warsaw"].disabled_at is not None
    assert await service.resolve_session(again.raw_token) is None
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(username="warsaw", password="longenough123")
    await service.register(username="second", password="longenough123")
    second_result = await service.authenticate(
        username="second",
        password="longenough123",
    )
    second_id = store.accounts["second"].id
    await service.delete_account(second_id)
    assert store.accounts["second"].deleted_at is not None
    assert await service.resolve_session(second_result.raw_token) is None
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(username="second", password="longenough123")


async def test_bootstrap_owner_is_one_time_and_forced_change() -> None:
    """Bootstrap creates one owner with forced change and never repeats."""
    store = FakeIdentityStore()
    bootstrap = BootstrapOwner(
        store,
        FakeHasher(),
        username="owner",
        password="ownerlongenough1",
    )
    view = await bootstrap()
    assert view.role is UserRole.OWNER
    assert view.must_change_password is True
    assert store.accounts["owner"].hashed_password == "fakehash:ownerlongenough1"
    with pytest.raises(BootstrapOwnerError, match="owner already exists"):
        await bootstrap()
    missing = BootstrapOwner(FakeIdentityStore(), FakeHasher(), username=None, password=None)
    with pytest.raises(BootstrapOwnerError, match="not provided"):
        await missing()
    invalid = BootstrapOwner(
        FakeIdentityStore(),
        FakeHasher(),
        username="x",
        password="ownerlongenough1",
    )
    with pytest.raises(BootstrapOwnerError, match="invalid"):
        await invalid()


async def test_dummy_hash_verification_equalizes_unknown_username() -> None:
    """Unknown usernames still perform one hash verification."""
    base = FakeHasher()
    verified: list[str] = []

    class SpyHasher(FakeHasher):
        def verify(self, password: str, hashed: str) -> bool:
            """Record the hash under verification."""
            verified.append(hashed)
            return base.verify(password, hashed)

    store = FakeIdentityStore()
    authenticate = AuthenticateAccount(
        store,
        SpyHasher(),
        FakeTokens(),
        FakeClock(),
        session_ttl_seconds=60,
    )
    with pytest.raises(InvalidCredentialsError):
        await authenticate(username="ghost", password="longenough123")
    assert verified == [AuthenticateAccount._DUMMY_HASH]  # noqa: SLF001


async def test_unknown_username_with_real_hasher_stays_invalid() -> None:
    """A real hasher verifies the dummy hash instead of crashing on it."""
    store = FakeIdentityStore()
    authenticate = AuthenticateAccount(
        store,
        PwdlibPasswordHasher(),
        FakeTokens(),
        FakeClock(),
        session_ttl_seconds=60,
    )
    with pytest.raises(InvalidCredentialsError, match="invalid credentials"):
        await authenticate(username="ghost", password="longenough123")


async def test_unidentifiable_stored_hash_stays_invalid() -> None:
    """A corrupt stored hash degrades to invalid credentials, not an error."""
    hasher = PwdlibPasswordHasher()
    store = FakeIdentityStore()
    await store.create_account(
        username_normalized="corrupt",
        username_display="corrupt",
        hashed_password="$argon2id$v=19$m=19456,t=2,p=1$",
        role=UserRole.USER,
        must_change_password=False,
    )
    authenticate = AuthenticateAccount(
        store,
        hasher,
        FakeTokens(),
        FakeClock(),
        session_ttl_seconds=60,
    )
    with pytest.raises(InvalidCredentialsError, match="invalid credentials"):
        await authenticate(username="corrupt", password="longenough123")


async def test_real_hasher_accepts_correct_password() -> None:
    """The end-to-end hashing path logs a real account in."""
    hasher = PwdlibPasswordHasher()
    store = FakeIdentityStore()
    await store.create_account(
        username_normalized="realuser",
        username_display="realuser",
        hashed_password=hasher.hash("longenough123"),
        role=UserRole.USER,
        must_change_password=False,
    )
    authenticate = AuthenticateAccount(
        store,
        hasher,
        FakeTokens(),
        FakeClock(),
        session_ttl_seconds=60,
    )
    result = await authenticate(username="realuser", password="longenough123")
    assert result.account.username == "realuser"


def test_memory_rate_limiter_enforces_windows() -> None:
    """The bounded in-memory limiter allows limits then refuses."""
    limiter = MemoryRateLimiter()
    assert all(limiter.allow("login:h:u", limit=2, window_seconds=60) for _ in range(2))
    assert not limiter.allow("login:h:u", limit=2, window_seconds=60)
    assert limiter.allow("login:h:other", limit=2, window_seconds=60)


def test_fake_rate_limiter_scripting() -> None:
    """The scripted limiter blocks exactly the scripted keys."""
    limiter = FakeRateLimiter(blocked={"register:h:abuse"})
    assert limiter.allow("register:h:abuse", limit=1, window_seconds=1) is False
    assert limiter.allow("register:h:ok", limit=1, window_seconds=1) is True
