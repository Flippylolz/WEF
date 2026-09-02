"""Unit tests for the deployment contact cipher factory."""

from wef_backend.composition import build_contact_cipher
from wef_backend.settings import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "env": "test",
        "database_url": "postgresql+asyncpg://localhost/test",
        "contact_encryption_key": None,
        "contact_hmac_key": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_build_contact_cipher_available_with_configured_keys() -> None:
    """Hex deployment keys produce a usable cipher."""
    key = "ab" * 32
    hmac_key = "cd" * 32
    cipher = build_contact_cipher(
        _settings(contact_encryption_key=key, contact_hmac_key=hmac_key),
    )
    assert cipher.available
    token = cipher.encrypt("+48600100200")
    assert cipher.decrypt(token) == "+48600100200"


def test_build_contact_cipher_unavailable_without_keys() -> None:
    """Missing deployment keys produce an unavailable cipher."""
    cipher = build_contact_cipher(_settings())
    assert not cipher.available
