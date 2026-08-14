"""Username and password policy unit tests."""

import datetime as dt
import uuid

import pytest

from wef_backend.features.identity.domain.model import (
    Account,
    AccountSession,
    UserRole,
    normalize_username,
    validate_password,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("WarsawUser", "warsawuser"),
        ("  trailing  ", "trailing"),
        ("user_2026", "user_2026"),
        ("a" * 64, "a" * 64),
    ],
)
def test_normalize_username_accepts_and_normalizes(value: str, expected: str) -> None:
    """Normalization strips, lowercases, and preserves allowed characters."""
    assert normalize_username(value) == expected


@pytest.mark.parametrize(
    "value",
    ["ab", "a" * 65, "spaces inside", "unicode-łódź", "colon:user", ""],
)
def test_normalize_username_rejects_unsafe_values(value: str) -> None:
    """Unsafe usernames are refused without reflecting the reason."""
    with pytest.raises(ValueError, match="username is invalid"):
        normalize_username(value)


def test_validate_password_accepts_bounded_input() -> None:
    """Length-bounded passwords are accepted regardless of composition."""
    validate_password("a" * 10)
    validate_password("a" * 256)


@pytest.mark.parametrize("value", ["a" * 9, "a" * 257, ""])
def test_validate_password_rejects_out_of_bounds(value: str) -> None:
    """Out-of-bounds passwords are refused."""
    with pytest.raises(ValueError, match="password is invalid"):
        validate_password(value)


def test_account_and_session_records_are_plain_data() -> None:
    """Domain records stay persistence-neutral value objects."""
    moment = dt.datetime(2026, 8, 14, tzinfo=dt.UTC)
    account_id = uuid.uuid4()
    account = Account(
        id=account_id,
        username_normalized="warsaw",
        username_display="Warsaw",
        hashed_password="fakehash:secret",
        role=UserRole.USER,
        is_active=True,
        must_change_password=False,
        created_at=moment,
        updated_at=moment,
        last_login_at=None,
        disabled_at=None,
        deleted_at=None,
    )
    session = AccountSession(
        id=uuid.uuid4(),
        account_id=account_id,
        token_hash="hashed-token",
        expires_at=moment,
        revoked_at=None,
        created_at=moment,
        last_used_at=None,
    )
    assert account.role is UserRole.USER
    assert session.token_hash == "hashed-token"
