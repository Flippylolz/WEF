"""Contact persistence and reveal against disposable PostGIS."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from geoalchemy2.elements import WKTElement
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.contacts.application.reveal import (
    ContactInput,
    PersistOfferContacts,
    RevealOfferContacts,
)
from wef_backend.features.contacts.domain.model import ContactKind, RevealOutcome
from wef_backend.features.contacts.infrastructure import (
    AesGcmContactCipher,
    SQLAlchemyContactStore,
    decode_secret_key,
)
from wef_backend.features.identity.infrastructure import MemoryRateLimiter
from wef_backend.features.identity.infrastructure.models import UserRow
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


async def test_contact_store_round_trip_and_audit() -> None:
    """Migrate, persist encrypted contacts, reveal, and audit without plaintext."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    encryption_key = decode_secret_key("cc" * 32)
    hmac_key = decode_secret_key("dd" * 32)
    assert encryption_key is not None
    assert hmac_key is not None
    cipher = AesGcmContactCipher(encryption_key=encryption_key, hmac_key=hmac_key)
    store = SQLAlchemyContactStore(database.session_factory)
    persist = PersistOfferContacts(store, cipher)
    reveal = RevealOfferContacts(store, cipher, MemoryRateLimiter())
    location_id = uuid4()
    offer_id = uuid4()
    user_id = uuid4()

    await _purge_contact_tables(TEST_DATABASE_URL)
    try:
        await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")
        async with database.session_factory.begin() as session:
            revision = await session.scalar(
                text("SELECT version_num FROM alembic_version"),
            )
            assert revision == EXPECTED_DATABASE_REVISION
            session.add(
                LocationRow(
                    id=location_id,
                    display_name="Contact Loc",
                    display_address="Addr",
                    normalized_address="addr",
                    normalized_address_hash=f"hash-{location_id}",
                    district="wola",
                    city="Warszawa",
                    country_code="PL",
                    point=WKTElement("POINT(21.0 52.2)", srid=4326),
                    precision="building",
                    confidence=Decimal("0.90"),
                    review_status="accepted",
                    out_of_scope=False,
                ),
            )
            session.add(
                OfferRow(
                    id=offer_id,
                    location_id=location_id,
                    content_type="unit",
                    market_type="primary",
                    visibility="visible",
                    published_at=datetime.now(UTC),
                    latest_source_at=datetime.now(UTC),
                    currency="PLN",
                    price_min_minor=100_000,
                    price_max_minor=100_000,
                    parking_included_in_price=False,
                    storage_included_in_price=False,
                    source_text_excerpt="excerpt",
                    source_text_public_masked="masked",
                    canonical_fingerprint=f"fp-{offer_id}",
                    parser_version="test",
                ),
            )
            session.add(
                UserRow(
                    id=user_id,
                    username_normalized="contactuser",
                    username_display="ContactUser",
                    hashed_password="hash",
                    role="user",
                    is_active=True,
                    must_change_password=False,
                ),
            )

        await persist(
            offer_id=offer_id,
            source_message_id=None,
            contacts=(
                ContactInput(kind=ContactKind.PHONE, value="+48123456789"),
                ContactInput(kind=ContactKind.TELEGRAM, value="@agent"),
            ),
        )
        rows = await store.list_revealable_for_offer(offer_id)
        assert len(rows) == 2
        assert all("+48123456789" not in row.value_ciphertext for row in rows)
        assert await store.offer_is_publicly_visible(offer_id) is True

        result = await reveal(
            user_id=user_id,
            offer_id=offer_id,
            request_id=uuid4(),
            must_change_password=False,
        )
        assert result.outcome is RevealOutcome.ALLOWED
        assert {item.value for item in result.contacts} == {"+48123456789", "@agent"}

        async with database.session_factory() as session:
            outcomes = [
                row[0]
                for row in await session.execute(
                    text("SELECT outcome FROM contact_reveals WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
            ]
            payloads = [
                row[0]
                for row in await session.execute(
                    text(
                        "SELECT value_ciphertext FROM contact_points WHERE offer_id = :offer_id",
                    ),
                    {"offer_id": offer_id},
                )
            ]
        assert outcomes == ["allowed"]
        assert all("+48123456789" not in payload for payload in payloads)
        assert all("@agent" not in payload for payload in payloads)

        unavailable = RevealOfferContacts(
            store,
            AesGcmContactCipher(encryption_key=None, hmac_key=None),
            MemoryRateLimiter(),
        )
        missing_keys = await unavailable(
            user_id=user_id,
            offer_id=offer_id,
            request_id=uuid4(),
            must_change_password=False,
        )
        assert missing_keys.outcome is RevealOutcome.UNAVAILABLE
    finally:
        await database.engine.dispose()


async def _purge_contact_tables(database_url: str) -> None:
    """Drop contact rows and related fixtures between integration runs."""
    database = create_database_resources(database_url)
    try:
        async with database.session_factory() as session:
            for table in (
                "contact_reveals",
                "contact_points",
                "auth_sessions",
                "favorite_locations",
                "users",
                "offers",
                "locations",
            ):
                exists = await session.scalar(
                    text(
                        "SELECT to_regclass(:name)",
                    ),
                    {"name": table},
                )
                if exists is not None:
                    await session.execute(text(f"DELETE FROM {table}"))  # noqa: S608
            await session.commit()
    finally:
        await database.engine.dispose()
