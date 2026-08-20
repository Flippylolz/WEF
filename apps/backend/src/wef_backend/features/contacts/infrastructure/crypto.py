"""AES-GCM contact encryption and HMAC fingerprints."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from wef_backend.features.contacts.application.reveal import ContactCryptoUnavailableError
from wef_backend.features.contacts.domain.model import ContactKind  # noqa: TC001

_NONCE_BYTES: Final = 12
_KEY_BYTES: Final = 32
_HEX_KEY_LENGTH: Final = 64


def decode_secret_key(raw: str | None) -> bytes | None:
    """Decode a 32-byte key from hex or URL-safe base64, or return None."""
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    if len(candidate) == _HEX_KEY_LENGTH and all(
        ch in "0123456789abcdefABCDEF" for ch in candidate
    ):
        return bytes.fromhex(candidate)
    padded = candidate + "=" * (-len(candidate) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        message = "contact key must be 32-byte hex or url-safe base64"
        raise ContactCryptoUnavailableError(message) from error
    if len(decoded) != _KEY_BYTES:
        message = "contact key must decode to 32 bytes"
        raise ContactCryptoUnavailableError(message)
    return decoded


class AesGcmContactCipher:
    """Encrypt contacts with AES-GCM and fingerprint with HMAC-SHA256."""

    def __init__(
        self,
        *,
        encryption_key: bytes | None,
        hmac_key: bytes | None,
    ) -> None:
        """Configure keys; both must be present for availability."""
        self._encryption_key = encryption_key
        self._hmac_key = hmac_key
        self._aesgcm = AESGCM(encryption_key) if encryption_key is not None else None

    @property
    def available(self) -> bool:
        """Report whether both keys are configured."""
        return self._aesgcm is not None and self._hmac_key is not None

    def encrypt(self, plaintext: str) -> str:
        """Return nonce||ciphertext as URL-safe base64."""
        if self._aesgcm is None:
            message = "contact encryption key is unavailable"
            raise ContactCryptoUnavailableError(message)
        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt one persisted contact value."""
        if self._aesgcm is None:
            message = "contact encryption key is unavailable"
            raise ContactCryptoUnavailableError(message)
        try:
            raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
            nonce, payload = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
            plaintext = self._aesgcm.decrypt(nonce, payload, None)
        except (ValueError, UnicodeEncodeError) as error:
            message = "contact ciphertext is invalid"
            raise ContactCryptoUnavailableError(message) from error
        return plaintext.decode("utf-8")

    def fingerprint(self, *, kind: ContactKind, normalized_value: str) -> str:
        """Return a hex HMAC over kind and normalized value."""
        if self._hmac_key is None:
            message = "contact HMAC key is unavailable"
            raise ContactCryptoUnavailableError(message)
        material = f"{kind.value}:{normalized_value}".encode()
        return hmac.new(self._hmac_key, material, hashlib.sha256).hexdigest()
