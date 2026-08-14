"""Pseudonymous account and session domain model."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 64
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 256

_USERNAME_INVALID = "username is invalid"
_CREDENTIAL_INPUT_INVALID = "password is invalid"
_USERNAME_ALLOWED = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
)


class UserRole(StrEnum):
    """Fixed application authorization roles."""

    USER = "user"
    OWNER = "owner"


class UsernamePolicyError(ValueError):
    """Raised when a username cannot be accepted or normalized."""


class PasswordPolicyError(ValueError):
    """Raised when a password cannot be accepted."""


def normalize_username(value: str) -> str:
    """Validate and normalize one self-selected pseudonymous username."""
    candidate = value.strip().lower()
    if not USERNAME_MIN_LENGTH <= len(candidate) <= USERNAME_MAX_LENGTH:
        raise UsernamePolicyError(_USERNAME_INVALID)
    if not _USERNAME_ALLOWED.issuperset(candidate):
        raise UsernamePolicyError(_USERNAME_INVALID)
    return candidate


def validate_password(value: str) -> None:
    """Enforce bounded server-side password input length."""
    if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(_CREDENTIAL_INPUT_INVALID)


@dataclass(frozen=True, slots=True)
class Account:
    """Persistence-neutral pseudonymous account record."""

    id: UUID
    username_normalized: str
    username_display: str
    hashed_password: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    disabled_at: datetime | None
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class AccountSession:
    """Opaque server-side session record without raw tokens."""

    id: UUID
    account_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None
