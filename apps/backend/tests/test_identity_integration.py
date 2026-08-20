"""Identity persistence and migration checks against disposable PostGIS."""

import asyncio
import json
import os
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend import owner_command
from wef_backend.database import create_database_resources
from wef_backend.features.identity.application.identity import (
    AuthenticateAccount,
    BootstrapOwner,
    ChangeAccountPassword,
    InvalidCredentialsError,
    RegisterAccount,
    RegistrationDeclinedError,
    ResolveSession,
)
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure import (
    PwdlibPasswordHasher,
    SecretsTokenService,
    SQLAlchemyIdentityStore,
    SystemClock,
)
from wef_backend.migration import EXPECTED_DATABASE_REVISION, alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        TEST_DATABASE_URL is None,
        reason="TEST_DATABASE_URL is not configured",
    ),
]


async def test_identity_migration_creates_schema_and_flows() -> None:
    """Migrate to head, persist accounts/sessions, and exercise revocation."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIdentityStore(database.session_factory)
    hasher = PwdlibPasswordHasher()
    tokens = SecretsTokenService()
    clock = SystemClock()
    register = RegisterAccount(store, hasher)
    authenticate = AuthenticateAccount(
        store,
        hasher,
        tokens,
        clock,
        session_ttl_seconds=3600,
    )
    resolve = ResolveSession(store, tokens, clock)
    change_password = ChangeAccountPassword(store, hasher, clock)

    await _purge_identity_tables(TEST_DATABASE_URL)

    try:
        await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")
        async with database.session_factory() as session:
            revision = await session.scalar(
                text("SELECT version_num FROM alembic_version"),
            )
            columns = {
                row[0]
                for row in await session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'users'",
                    ),
                )
            }
        assert revision == EXPECTED_DATABASE_REVISION
        assert {"username_normalized", "hashed_password", "role", "deleted_at"} <= columns

        account = await register(
            username="IntegrationUser",
            password="integrationpass1",
        )
        assert account.role is UserRole.USER
        with pytest.raises(RegistrationDeclinedError, match="username unavailable"):
            await register(
                username="integrationuser",
                password="anotherpass1234",
            )

        login = await authenticate(
            username="integrationuser",
            password="integrationpass1",
        )
        assert await resolve(login.raw_token) is not None
        assert await resolve("not-a-real-token") is None

        second = await authenticate(
            username="integrationuser",
            password="integrationpass1",
        )
        await change_password(
            account_id=account.id,
            current_password="integrationpass1",
            new_password="rotatedpass12345",
        )
        assert await resolve(login.raw_token) is None
        assert await resolve(second.raw_token) is None
        with pytest.raises(InvalidCredentialsError):
            await authenticate(
                username="integrationuser",
                password="integrationpass1",
            )
        rotated = await authenticate(
            username="integrationuser",
            password="rotatedpass12345",
        )
        assert await resolve(rotated.raw_token) is not None

        bootstrap = BootstrapOwner(
            store,
            hasher,
            username="root",
            password="ownerlongenough1",
        )
        owner = await bootstrap()
        assert owner.must_change_password is True
    finally:
        await database.engine.dispose()


async def test_auth_sessions_table_constraints() -> None:
    """Token hashes are unique and cascade with their account."""
    assert TEST_DATABASE_URL is not None
    database = create_database_resources(TEST_DATABASE_URL)
    store = SQLAlchemyIdentityStore(database.session_factory)
    hasher = PwdlibPasswordHasher()

    try:
        register = RegisterAccount(store, hasher)
        account = await register(username="cascade", password="cascadepass123")
        await store.create_session(
            account_id=account.id,
            token_hash="hash-cascade-1",
            expires_at=SystemClock().now(),
        )
        revoked = await store.revoke_all_sessions(account.id)
        assert revoked == 1
        revoked_again = await store.revoke_all_sessions(account.id)
        assert revoked_again == 0
        async with database.session_factory() as session:
            await session.execute(
                text("DELETE FROM users WHERE username_normalized = 'cascade'"),
            )
            await session.commit()
            remaining = await session.scalar(
                text(
                    "SELECT count(*) FROM auth_sessions WHERE token_hash = 'hash-cascade-1'",
                ),
            )
        assert remaining == 0
    finally:
        await database.engine.dispose()


async def _purge_identity_tables(database_url: str) -> None:
    """Remove identity rows from the disposable test database when present."""
    database = create_database_resources(database_url)
    try:
        async with database.session_factory() as session:
            exists = await session.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'users')"
                ),
            )
            if not exists:
                return
            await session.execute(text("DELETE FROM admin_audit_events"))
            await session.execute(text("DELETE FROM auth_sessions"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
    finally:
        await database.engine.dispose()


def test_owner_command_entry_points(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The bootstrap command refuses missing credentials and is idempotent."""
    assert TEST_DATABASE_URL is not None
    monkeypatch.setenv("WEF_DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("WEF_ENV", "test")
    monkeypatch.delenv("WEF_BOOTSTRAP_OWNER_USERNAME", raising=False)
    monkeypatch.delenv("WEF_BOOTSTRAP_OWNER_PASSWORD", raising=False)
    asyncio.run(_purge_identity_tables(TEST_DATABASE_URL))

    with pytest.raises(SystemExit) as missing:
        owner_command.main()
    assert missing.value.code == 2

    monkeypatch.setenv("WEF_BOOTSTRAP_OWNER_USERNAME", "commandowner")
    monkeypatch.setenv("WEF_BOOTSTRAP_OWNER_PASSWORD", "commandsecret123")
    assert owner_command.main() == 0
    first = json.loads(capsys.readouterr().out)
    assert first["bootstrapped"] is True
    assert first["username"] == "commandowner"

    monkeypatch.setenv("WEF_BOOTSTRAP_OWNER_USERNAME", "secondowner")
    monkeypatch.setenv("WEF_BOOTSTRAP_OWNER_PASSWORD", "commandsecret456")
    assert owner_command.main() == 0
    repeat = json.loads(capsys.readouterr().out)
    assert repeat == {
        "bootstrapped": False,
        "reason": "owner_already_exists",
    }
