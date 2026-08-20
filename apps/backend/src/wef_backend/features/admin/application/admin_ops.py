"""Owner administration application interactors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

from wef_backend.features.identity.domain.model import (
    Account,
    UserRole,
    validate_password,
)

if TYPE_CHECKING:
    from wef_backend.features.identity.application.identity import (
        Clock,
        IdentityStore,
        PasswordHasher,
    )


class AdminDeniedError(PermissionError):
    """Raised when an owner action is refused."""


class AdminOutcome(StrEnum):
    """Minimized admin audit outcomes."""

    ALLOWED = "allowed"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AdminAuditEvent:
    """Redacted owner-administration audit row."""

    id: UUID
    owner_user_id: UUID
    target_user_id: UUID | None
    target_type: str | None
    target_id: str | None
    action: str
    occurred_at: datetime
    request_id: UUID
    outcome: AdminOutcome


@dataclass(frozen=True, slots=True)
class AdminAccountSummary:
    """Safe account projection for owner listing (no hash/token)."""

    id: UUID
    username: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None
    disabled_at: datetime | None


@dataclass(frozen=True, slots=True)
class RevealAuditSummary:
    """Minimized contact-reveal audit projection for owners."""

    id: UUID
    user_id: UUID
    offer_id: UUID
    outcome: str
    revealed_at: datetime
    request_id: UUID


class AdminAuditStore(Protocol):
    """Persistence for redacted admin audit events."""

    async def record(self, event: AdminAuditEvent) -> None:
        """Persist one redacted admin audit event."""
        ...

    async def list_recent(self, *, limit: int = 100) -> tuple[AdminAuditEvent, ...]:
        """Return recent admin audits newest-first."""
        ...


class RevealAuditReader(Protocol):
    """Read-only access to minimized contact reveal audits."""

    async def list_recent(self, *, limit: int = 100) -> tuple[RevealAuditSummary, ...]:
        """Return recent reveal audits newest-first."""
        ...


def _summary(account: Account) -> AdminAccountSummary:
    """Project one account without hash or token material."""
    return AdminAccountSummary(
        id=account.id,
        username=account.username_display,
        role=account.role,
        is_active=account.is_active,
        must_change_password=account.must_change_password,
        created_at=account.created_at,
        last_login_at=account.last_login_at,
        disabled_at=account.disabled_at,
    )


class ListAdminAccounts:
    """List accounts for the owner console without sensitive fields."""

    def __init__(self, store: IdentityStore) -> None:
        """Initialize the collaborator."""
        self._store = store

    async def __call__(self, *, limit: int = 100) -> tuple[AdminAccountSummary, ...]:
        """Execute the owner administration use case."""
        accounts = await self._store.list_accounts(limit=limit)
        return tuple(_summary(account) for account in accounts)


class DisableUser:
    """Disable a non-owner account and revoke its sessions."""

    def __init__(
        self,
        store: IdentityStore,
        audits: AdminAuditStore,
        clock: Clock,
    ) -> None:
        """Initialize the collaborator."""
        self._store = store
        self._audits = audits
        self._clock = clock

    async def __call__(
        self,
        *,
        owner_id: UUID,
        target_user_id: UUID,
        request_id: UUID,
    ) -> None:
        """Execute the owner administration use case."""
        target = await self._store.find_account_by_id(target_user_id)
        if target is None or target.deleted_at is not None:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "disable_user",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            msg = "account not found"
            raise AdminDeniedError(msg)
        if target.role is UserRole.OWNER:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "disable_user",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            msg = "cannot disable an owner account"
            raise AdminDeniedError(msg)
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=target.id,
                username_normalized=target.username_normalized,
                username_display=target.username_display,
                hashed_password=target.hashed_password,
                role=target.role,
                is_active=False,
                must_change_password=target.must_change_password,
                created_at=target.created_at,
                updated_at=now,
                last_login_at=target.last_login_at,
                disabled_at=now,
                deleted_at=target.deleted_at,
            ),
        )
        await self._store.revoke_all_sessions(target_user_id)
        await self._audits.record(
            _event(
                owner_id,
                target_user_id,
                "disable_user",
                request_id,
                AdminOutcome.ALLOWED,
            ),
        )


class ReactivateUser:
    """Reactivate a previously disabled non-deleted account."""

    def __init__(
        self,
        store: IdentityStore,
        audits: AdminAuditStore,
        clock: Clock,
    ) -> None:
        """Initialize the collaborator."""
        self._store = store
        self._audits = audits
        self._clock = clock

    async def __call__(
        self,
        *,
        owner_id: UUID,
        target_user_id: UUID,
        request_id: UUID,
    ) -> None:
        """Execute the owner administration use case."""
        target = await self._store.find_account_by_id(target_user_id)
        if target is None or target.deleted_at is not None:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "reactivate_user",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            msg = "account not found"
            raise AdminDeniedError(msg)
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=target.id,
                username_normalized=target.username_normalized,
                username_display=target.username_display,
                hashed_password=target.hashed_password,
                role=target.role,
                is_active=True,
                must_change_password=target.must_change_password,
                created_at=target.created_at,
                updated_at=now,
                last_login_at=target.last_login_at,
                disabled_at=None,
                deleted_at=target.deleted_at,
            ),
        )
        await self._audits.record(
            _event(
                owner_id,
                target_user_id,
                "reactivate_user",
                request_id,
                AdminOutcome.ALLOWED,
            ),
        )


class RevokeUserSessions:
    """Revoke every live session for one account."""

    def __init__(self, store: IdentityStore, audits: AdminAuditStore) -> None:
        """Initialize the collaborator."""
        self._store = store
        self._audits = audits

    async def __call__(
        self,
        *,
        owner_id: UUID,
        target_user_id: UUID,
        request_id: UUID,
    ) -> int:
        """Execute the owner administration use case."""
        target = await self._store.find_account_by_id(target_user_id)
        if target is None:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "revoke_user_sessions",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            msg = "account not found"
            raise AdminDeniedError(msg)
        revoked = await self._store.revoke_all_sessions(target_user_id)
        await self._audits.record(
            _event(
                owner_id,
                target_user_id,
                "revoke_user_sessions",
                request_id,
                AdminOutcome.ALLOWED,
            ),
        )
        return revoked


class ForceResetUserPassword:
    """Set a temporary password and require change on next login."""

    def __init__(
        self,
        store: IdentityStore,
        audits: AdminAuditStore,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        """Initialize the collaborator."""
        self._store = store
        self._audits = audits
        self._hasher = hasher
        self._clock = clock

    async def __call__(
        self,
        *,
        owner_id: UUID,
        target_user_id: UUID,
        temporary_password: str,
        request_id: UUID,
    ) -> None:
        """Execute the owner administration use case."""
        try:
            validate_password(temporary_password)
        except ValueError as error:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "force_reset_password",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            raise AdminDeniedError(str(error)) from error
        target = await self._store.find_account_by_id(target_user_id)
        if target is None or target.deleted_at is not None:
            await self._audits.record(
                _event(
                    owner_id,
                    target_user_id,
                    "force_reset_password",
                    request_id,
                    AdminOutcome.DENIED,
                ),
            )
            msg = "account not found"
            raise AdminDeniedError(msg)
        if target.role is UserRole.OWNER and target.id != owner_id:
            active_owners = await self._store.count_active_owners()
            if active_owners <= 1:
                await self._audits.record(
                    _event(
                        owner_id,
                        target_user_id,
                        "force_reset_password",
                        request_id,
                        AdminOutcome.DENIED,
                    ),
                )
                msg = "cannot reset the last owner without self-service"
                raise AdminDeniedError(msg)
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=target.id,
                username_normalized=target.username_normalized,
                username_display=target.username_display,
                hashed_password=self._hasher.hash(temporary_password),
                role=target.role,
                is_active=target.is_active,
                must_change_password=True,
                created_at=target.created_at,
                updated_at=now,
                last_login_at=target.last_login_at,
                disabled_at=target.disabled_at,
                deleted_at=target.deleted_at,
            ),
        )
        await self._store.revoke_all_sessions(target_user_id)
        await self._audits.record(
            _event(
                owner_id,
                target_user_id,
                "force_reset_password",
                request_id,
                AdminOutcome.ALLOWED,
            ),
        )


class ListRevealAudits:
    """List minimized contact reveal audits for owners."""

    def __init__(self, reader: RevealAuditReader) -> None:
        """Initialize the collaborator."""
        self._reader = reader

    async def __call__(self, *, limit: int = 100) -> tuple[RevealAuditSummary, ...]:
        """Execute the owner administration use case."""
        return await self._reader.list_recent(limit=limit)


class ListAdminAudits:
    """List redacted admin audit events."""

    def __init__(self, audits: AdminAuditStore) -> None:
        """Initialize the collaborator."""
        self._audits = audits

    async def __call__(self, *, limit: int = 100) -> tuple[AdminAuditEvent, ...]:
        """Execute the owner administration use case."""
        return await self._audits.list_recent(limit=limit)


@dataclass(frozen=True, slots=True)
class AdminService:
    """Owner-console interactors placed on application state."""

    list_accounts: ListAdminAccounts
    disable_user: DisableUser
    reactivate_user: ReactivateUser
    revoke_user_sessions: RevokeUserSessions
    force_reset_password: ForceResetUserPassword
    list_reveal_audits: ListRevealAudits
    list_admin_audits: ListAdminAudits


def _event(
    owner_id: UUID,
    target_user_id: UUID | None,
    action: str,
    request_id: UUID,
    outcome: AdminOutcome,
) -> AdminAuditEvent:
    return AdminAuditEvent(
        id=uuid4(),
        owner_user_id=owner_id,
        target_user_id=target_user_id,
        target_type="user" if target_user_id is not None else None,
        target_id=str(target_user_id) if target_user_id is not None else None,
        action=action,
        occurred_at=datetime.now(UTC),
        request_id=request_id,
        outcome=outcome,
    )
