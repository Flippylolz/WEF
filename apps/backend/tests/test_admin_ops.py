"""Owner administration interactor tests."""

from dataclasses import replace
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAdminAuditStore,
    FakeClock,
    FakeHasher,
    FakeIdentityStore,
    FakeRevealAuditReader,
)
from wef_backend.features.admin.application.admin_ops import (
    AdminDeniedError,
    AdminOutcome,
    DisableUser,
    ForceResetUserPassword,
    ListAdminAccounts,
    ListAdminAudits,
    ListRevealAudits,
    ReactivateUser,
    RevealAuditSummary,
    RevokeUserSessions,
)
from wef_backend.features.identity.domain.model import UserRole


@pytest.mark.asyncio
async def test_disable_user_revokes_sessions_and_audits() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    clock = FakeClock()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    user = await store.create_account(
        username_normalized="buyer",
        username_display="buyer",
        hashed_password="hash",
        role=UserRole.USER,
        must_change_password=False,
    )
    await store.create_session(
        account_id=user.id,
        token_hash="token",
        expires_at=clock.now(),
    )
    disable = DisableUser(store, audits, clock)
    request_id = uuid4()
    await disable(owner_id=owner.id, target_user_id=user.id, request_id=request_id)

    refreshed = await store.find_account_by_id(user.id)
    assert refreshed is not None
    assert refreshed.is_active is False
    assert await store.revoke_all_sessions(user.id) == 0
    assert audits.events[-1].outcome is AdminOutcome.ALLOWED
    assert audits.events[-1].action == "disable_user"


@pytest.mark.asyncio
async def test_disable_owner_is_denied() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    disable = DisableUser(store, audits, FakeClock())
    with pytest.raises(AdminDeniedError):
        await disable(
            owner_id=owner.id,
            target_user_id=owner.id,
            request_id=uuid4(),
        )
    assert audits.events[-1].outcome is AdminOutcome.DENIED


@pytest.mark.asyncio
async def test_disable_missing_account_is_denied() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    with pytest.raises(AdminDeniedError):
        await DisableUser(store, audits, FakeClock())(
            owner_id=owner.id,
            target_user_id=uuid4(),
            request_id=uuid4(),
        )
    assert audits.events[-1].outcome is AdminOutcome.DENIED


@pytest.mark.asyncio
async def test_force_reset_sets_must_change_and_revokes() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    hasher = FakeHasher()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    user = await store.create_account(
        username_normalized="buyer",
        username_display="buyer",
        hashed_password="old",
        role=UserRole.USER,
        must_change_password=False,
    )
    reset = ForceResetUserPassword(store, audits, hasher, FakeClock())
    await reset(
        owner_id=owner.id,
        target_user_id=user.id,
        temporary_password="temporary12",
        request_id=uuid4(),
    )
    refreshed = await store.find_account_by_id(user.id)
    assert refreshed is not None
    assert refreshed.must_change_password is True
    assert refreshed.hashed_password == hasher.hash("temporary12")


@pytest.mark.asyncio
async def test_force_reset_rejects_weak_password_and_missing_target() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    reset = ForceResetUserPassword(store, audits, FakeHasher(), FakeClock())
    with pytest.raises(AdminDeniedError):
        await reset(
            owner_id=owner.id,
            target_user_id=uuid4(),
            temporary_password="short",
            request_id=uuid4(),
        )
    with pytest.raises(AdminDeniedError):
        await reset(
            owner_id=owner.id,
            target_user_id=uuid4(),
            temporary_password="temporary12",
            request_id=uuid4(),
        )
    assert audits.events[-1].action == "force_reset_password"
    assert audits.events[-1].outcome is AdminOutcome.DENIED


@pytest.mark.asyncio
async def test_list_accounts_omits_deleted() -> None:
    store = FakeIdentityStore()
    active = await store.create_account(
        username_normalized="buyer",
        username_display="buyer",
        hashed_password="hash",
        role=UserRole.USER,
        must_change_password=False,
    )
    deleted = await store.create_account(
        username_normalized="gone",
        username_display="gone",
        hashed_password="hash",
        role=UserRole.USER,
        must_change_password=False,
    )
    await store.update_account(
        replace(
            deleted,
            deleted_at=FakeClock().now(),
            is_active=False,
        ),
    )
    summaries = await ListAdminAccounts(store)()
    ids = {item.id for item in summaries}
    assert active.id in ids
    assert deleted.id not in ids


@pytest.mark.asyncio
async def test_force_reset_last_other_owner_is_denied() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    sole_owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    reset = ForceResetUserPassword(store, audits, FakeHasher(), FakeClock())
    with pytest.raises(AdminDeniedError):
        await reset(
            owner_id=uuid4(),
            target_user_id=sole_owner.id,
            temporary_password="temporary12",
            request_id=uuid4(),
        )
    assert audits.events[-1].outcome is AdminOutcome.DENIED
    assert audits.events[-1].action == "force_reset_password"


@pytest.mark.asyncio
async def test_reactivate_and_revoke_sessions() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    clock = FakeClock()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    user = await store.create_account(
        username_normalized="buyer",
        username_display="buyer",
        hashed_password="hash",
        role=UserRole.USER,
        must_change_password=False,
    )
    await DisableUser(store, audits, clock)(
        owner_id=owner.id,
        target_user_id=user.id,
        request_id=uuid4(),
    )
    await ReactivateUser(store, audits, clock)(
        owner_id=owner.id,
        target_user_id=user.id,
        request_id=uuid4(),
    )
    await store.create_session(
        account_id=user.id,
        token_hash="live",
        expires_at=clock.now(),
    )
    revoked = await RevokeUserSessions(store, audits)(
        owner_id=owner.id,
        target_user_id=user.id,
        request_id=uuid4(),
    )
    assert revoked == 1
    refreshed = await store.find_account_by_id(user.id)
    assert refreshed is not None
    assert refreshed.is_active is True


@pytest.mark.asyncio
async def test_reactivate_and_revoke_missing_targets_are_denied() -> None:
    store = FakeIdentityStore()
    audits = FakeAdminAuditStore()
    owner = await store.create_account(
        username_normalized="owner",
        username_display="owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        must_change_password=False,
    )
    missing = uuid4()
    with pytest.raises(AdminDeniedError):
        await ReactivateUser(store, audits, FakeClock())(
            owner_id=owner.id,
            target_user_id=missing,
            request_id=uuid4(),
        )
    with pytest.raises(AdminDeniedError):
        await RevokeUserSessions(store, audits)(
            owner_id=owner.id,
            target_user_id=missing,
            request_id=uuid4(),
        )
    assert all(event.outcome is AdminOutcome.DENIED for event in audits.events[-2:])


@pytest.mark.asyncio
async def test_list_audits_readers() -> None:
    audits = FakeAdminAuditStore()
    reveals = FakeRevealAuditReader(
        rows=[
            RevealAuditSummary(
                id=uuid4(),
                user_id=uuid4(),
                offer_id=uuid4(),
                outcome="allowed",
                revealed_at=FakeClock().now(),
                request_id=uuid4(),
            ),
        ],
    )
    listed_reveals = await ListRevealAudits(reveals)(limit=10)
    assert len(listed_reveals) == 1
    assert await ListAdminAudits(audits)() == ()
