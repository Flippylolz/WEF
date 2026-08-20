"""Unit tests for contact masking, crypto, and reveal authorization."""

from uuid import uuid4

import pytest

from tests.fakes import FakeContactCipher, FakeContactStore, FakeRateLimiter
from wef_backend.features.contacts.application.reveal import (
    ContactInput,
    RevealOfferContacts,
    build_contact_records,
)
from wef_backend.features.contacts.domain.model import (
    ContactKind,
    RevealOutcome,
    mask_contact_value,
    normalize_contact_value,
)
from wef_backend.features.contacts.infrastructure.crypto import (
    AesGcmContactCipher,
    decode_secret_key,
)


def test_mask_empty_and_short_values() -> None:
    """Short or empty contacts collapse to opaque fillers."""
    assert mask_contact_value(ContactKind.PHONE, "") == "••••"
    assert mask_contact_value(ContactKind.PHONE, "12") == "••••"
    assert mask_contact_value(ContactKind.TELEGRAM, "@a") == "@••••"
    assert normalize_contact_value(ContactKind.TELEGRAM, "Agent") == "@agent"


def test_mask_phone_and_telegram() -> None:
    """Public masks never echo the full contact value."""
    phone = mask_contact_value(ContactKind.PHONE, "+48123456789")
    handle = mask_contact_value(ContactKind.TELEGRAM, "@agent_warsaw")
    assert "+48123456789" not in phone
    assert phone.endswith("89")
    assert "@agent_warsaw" not in handle
    assert handle.startswith("@ag")


def test_aes_gcm_round_trip_and_fingerprint_stability() -> None:
    """AES-GCM decrypts and HMAC fingerprints stay stable for normalized values."""
    key = decode_secret_key("00" * 32)
    hmac_key = decode_secret_key("11" * 32)
    assert key is not None
    assert hmac_key is not None
    cipher = AesGcmContactCipher(encryption_key=key, hmac_key=hmac_key)
    ciphertext = cipher.encrypt("+48111222333")
    assert "+48111222333" not in ciphertext
    assert cipher.decrypt(ciphertext) == "+48111222333"
    left = cipher.fingerprint(
        kind=ContactKind.PHONE,
        normalized_value=normalize_contact_value(ContactKind.PHONE, "+48 111 222 333"),
    )
    right = cipher.fingerprint(
        kind=ContactKind.PHONE,
        normalized_value=normalize_contact_value(ContactKind.PHONE, "+48111222333"),
    )
    assert left == right


async def test_reveal_happy_path_and_idor() -> None:
    """Visible offers reveal; non-visible offers refuse without plaintext."""
    offer_id = uuid4()
    hidden_id = uuid4()
    cipher = FakeContactCipher()
    store = FakeContactStore(visible_offers={offer_id})
    records = build_contact_records(
        cipher,
        offer_id=offer_id,
        source_message_id=uuid4(),
        contacts=(ContactInput(kind=ContactKind.PHONE, value="+48123456789"),),
    )
    store.contacts[offer_id] = list(records)
    reveal = RevealOfferContacts(store, cipher, FakeRateLimiter())
    allowed = await reveal(
        user_id=uuid4(),
        offer_id=offer_id,
        request_id=uuid4(),
        must_change_password=False,
    )
    assert allowed.outcome is RevealOutcome.ALLOWED
    assert allowed.contacts[0].value == "+48123456789"
    denied = await reveal(
        user_id=uuid4(),
        offer_id=hidden_id,
        request_id=uuid4(),
        must_change_password=False,
    )
    assert denied.outcome is RevealOutcome.FORBIDDEN
    assert denied.not_found is True
    assert denied.contacts == ()


async def test_reveal_forced_password_and_rate_limit() -> None:
    """Forced password change and rate limits refuse without decryption."""
    offer_id = uuid4()
    cipher = FakeContactCipher()
    store = FakeContactStore(visible_offers={offer_id})
    user_id = uuid4()
    limiter = FakeRateLimiter(blocked={f"reveal:{user_id}"})
    reveal = RevealOfferContacts(store, cipher, limiter)
    forced = await reveal(
        user_id=user_id,
        offer_id=offer_id,
        request_id=uuid4(),
        must_change_password=True,
    )
    assert forced.outcome is RevealOutcome.FORBIDDEN
    limited = await reveal(
        user_id=user_id,
        offer_id=offer_id,
        request_id=uuid4(),
        must_change_password=False,
    )
    assert limited.outcome is RevealOutcome.RATE_LIMITED
    assert all("value" not in str(item) or "enc:" not in str(item) for item in store.audits)


async def test_reveal_unavailable_when_decrypt_fails() -> None:
    """Corrupt ciphertext fails closed as unavailable."""
    offer_id = uuid4()
    cipher = FakeContactCipher()
    store = FakeContactStore(visible_offers={offer_id})
    records = build_contact_records(
        cipher,
        offer_id=offer_id,
        source_message_id=None,
        contacts=(ContactInput(kind=ContactKind.PHONE, value="+48123456789"),),
    )
    broken = records[0]
    store.contacts[offer_id] = [
        type(broken)(
            id=broken.id,
            offer_id=broken.offer_id,
            source_message_id=broken.source_message_id,
            kind=broken.kind,
            value_ciphertext="not-enc",
            masked_value=broken.masked_value,
            fingerprint_hmac=broken.fingerprint_hmac,
            is_revealable=True,
        ),
    ]
    reveal = RevealOfferContacts(store, cipher, FakeRateLimiter())
    result = await reveal(
        user_id=uuid4(),
        offer_id=offer_id,
        request_id=uuid4(),
        must_change_password=False,
    )
    assert result.outcome is RevealOutcome.UNAVAILABLE


async def test_build_contact_records_requires_keys() -> None:
    """Missing crypto keys fail closed before persistence."""
    cipher = FakeContactCipher(available=False)
    with pytest.raises(Exception, match="unavailable"):
        build_contact_records(
            cipher,
            offer_id=uuid4(),
            source_message_id=None,
            contacts=(ContactInput(kind=ContactKind.TELEGRAM, value="@x"),),
        )


def test_decode_secret_key_rejects_bad_material() -> None:
    """Invalid key encodings fail closed."""
    assert decode_secret_key(None) is None
    assert decode_secret_key("   ") is None
    with pytest.raises(Exception, match="contact key"):
        decode_secret_key("not-a-key!!!")
    key = decode_secret_key("ee" * 32)
    assert key is not None
    cipher = AesGcmContactCipher(encryption_key=key, hmac_key=None)
    assert cipher.available is False
    with pytest.raises(Exception, match="unavailable"):
        cipher.encrypt("x")
