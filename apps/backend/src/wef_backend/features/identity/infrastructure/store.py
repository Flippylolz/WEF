"""SQLAlchemy persistence for accounts and opaque sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, update

from wef_backend.features.identity.application.identity import IdentityStore
from wef_backend.features.identity.domain.model import (
    Account,
    AccountSession,
    UserRole,
)
from wef_backend.features.identity.infrastructure.models import SessionRow, UserRow

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _to_account(row: UserRow) -> Account:
    """Map one persisted row to the domain record."""
    return Account(
        id=row.id,
        username_normalized=row.username_normalized,
        username_display=row.username_display,
        hashed_password=row.hashed_password,
        role=UserRole(row.role),
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_login_at=row.last_login_at,
        disabled_at=row.disabled_at,
        deleted_at=row.deleted_at,
    )


def _to_session(row: SessionRow) -> AccountSession:
    """Map one persisted row to the domain session record."""
    return AccountSession(
        id=row.id,
        account_id=row.user_id,
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
    )


class SQLAlchemyIdentityStore(IdentityStore):
    """IdentityStore implementation over the shared async session factory."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def owner_exists(self) -> bool:
        """Report whether any owner account exists."""
        async with self._session_factory() as session:
            owner_id = await session.scalar(
                select(UserRow.id)
                .where(
                    UserRow.role == UserRole.OWNER.value,
                    UserRow.deleted_at.is_(None),
                )
                .limit(1),
            )
            return owner_id is not None

    async def username_exists(self, username_normalized: str) -> bool:
        """Report whether the normalized username is already taken."""
        async with self._session_factory() as session:
            found = await session.scalar(
                select(UserRow.id)
                .where(UserRow.username_normalized == username_normalized)
                .limit(1),
            )
            return found is not None

    async def create_account(
        self,
        *,
        username_normalized: str,
        username_display: str,
        hashed_password: str,
        role: UserRole,
        must_change_password: bool,
    ) -> Account:
        """Insert one account row and return the domain record."""
        row = UserRow(
            id=uuid4(),
            username_normalized=username_normalized,
            username_display=username_display,
            hashed_password=hashed_password,
            role=role.value,
            is_active=True,
            must_change_password=must_change_password,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_account(row)

    async def find_account_by_username(self, username_normalized: str) -> Account | None:
        """Return the account owning the normalized username."""
        async with self._session_factory() as session:
            row = await session.scalar(
                select(UserRow).where(UserRow.username_normalized == username_normalized).limit(1),
            )
            return None if row is None else _to_account(row)

    async def find_account_by_id(self, account_id: UUID) -> Account | None:
        """Return the account with the given identifier."""
        async with self._session_factory() as session:
            row = await session.scalar(
                select(UserRow).where(UserRow.id == account_id).limit(1),
            )
            return None if row is None else _to_account(row)

    async def list_accounts(self, *, limit: int = 100) -> tuple[Account, ...]:
        """Return recent non-deleted accounts for owner administration."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(UserRow)
                    .where(UserRow.deleted_at.is_(None))
                    .order_by(UserRow.created_at.desc())
                    .limit(limit),
                )
            ).all()
        return tuple(_to_account(row) for row in rows)

    async def count_active_owners(self) -> int:
        """Count active, non-deleted owner accounts."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(UserRow.id).where(
                        UserRow.role == UserRole.OWNER.value,
                        UserRow.is_active.is_(True),
                        UserRow.deleted_at.is_(None),
                    ),
                )
            ).all()
        return len(rows)

    async def update_account(self, account: Account) -> None:
        """Persist mutable account fields including password state."""
        async with self._session_factory() as session:
            await session.execute(
                update(UserRow)
                .where(UserRow.id == account.id)
                .values(
                    hashed_password=account.hashed_password,
                    is_active=account.is_active,
                    must_change_password=account.must_change_password,
                    last_login_at=account.last_login_at,
                    disabled_at=account.disabled_at,
                    deleted_at=account.deleted_at,
                    updated_at=account.updated_at,
                ),
            )
            await session.commit()

    async def create_session(
        self,
        *,
        account_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Insert one opaque session token hash."""
        async with self._session_factory() as session:
            session.add(
                SessionRow(
                    id=uuid4(),
                    user_id=account_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                ),
            )
            await session.commit()

    async def find_session_by_token_hash(self, token_hash: str) -> AccountSession | None:
        """Return the session owning the token hash."""
        async with self._session_factory() as session:
            row = await session.scalar(
                select(SessionRow).where(SessionRow.token_hash == token_hash).limit(1),
            )
            return None if row is None else _to_session(row)

    async def revoke_session(self, session_id: UUID) -> None:
        """Revoke exactly one session."""
        async with self._session_factory() as session:
            await session.execute(
                update(SessionRow)
                .where(
                    SessionRow.id == session_id,
                    SessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(UTC)),
            )
            await session.commit()

    async def revoke_all_sessions(self, account_id: UUID) -> int:
        """Revoke every live session of one account and return the count."""
        async with self._session_factory() as session:
            result = cast(
                "CursorResult[Any]",
                await session.execute(
                    update(SessionRow)
                    .where(
                        SessionRow.user_id == account_id,
                        SessionRow.revoked_at.is_(None),
                    )
                    .values(revoked_at=datetime.now(UTC)),
                ),
            )
            await session.commit()
            return int(result.rowcount or 0)
