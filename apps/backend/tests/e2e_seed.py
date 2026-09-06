"""Seed only the isolated E14 browser database with invented records and images."""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy import make_url, text

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.features.contacts.application.reveal import ContactInput, PersistOfferContacts
from wef_backend.features.contacts.domain.model import ContactKind
from wef_backend.features.contacts.infrastructure import (
    AesGcmContactCipher,
    SQLAlchemyContactStore,
    decode_secret_key,
)
from wef_backend.features.identity.application.identity import RegisterAccount
from wef_backend.features.identity.infrastructure import (
    PwdlibPasswordHasher,
    SQLAlchemyIdentityStore,
)
from wef_backend.settings import load_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

OFFER_ID = UUID("20000000-0000-4000-8000-000000000001")
PROFILES = ("chromium", "firefox", "webkit", "mobile-chrome", "mobile-safari")
# Reserved fictional NANP range, never an exported contact.
SYNTHETIC_CONTACT = "+12025550123"


async def seed() -> None:
    """Refuse any database except the disposable internal Compose target."""
    settings = load_settings()
    url = make_url(settings.database_url)
    if (
        settings.env != "test"
        or url.host != "db"
        or url.database != "wef_e2e"
        or url.username != "wef_e2e"
    ):
        message = "E2E seed requires the isolated test-only Compose database"
        raise RuntimeError(message)
    database = create_database_resources(settings.database_url)
    try:
        async with database.session_factory() as session:
            if await session.scalar(text("SELECT count(*) FROM users")) != 0:
                message = "E2E database is not fresh"
                raise RuntimeError(message)
        await SeedM1Catalog(
            SQLAlchemyCatalogSeedAdapter(database.session_factory), environment="test"
        )(*m1_fixture())
        register = RegisterAccount(
            SQLAlchemyIdentityStore(database.session_factory), PwdlibPasswordHasher()
        )
        for profile in PROFILES:
            account = await register(
                username=f"e2e_forced_{profile}", password=os.environ["WEF_E2E_PASSWORD"]
            )
            async with database.session_factory() as session, session.begin():
                await session.execute(
                    text("UPDATE users SET must_change_password = true WHERE id = :id"),
                    {"id": account.id},
                )
        cipher = AesGcmContactCipher(
            encryption_key=decode_secret_key(os.environ["WEF_CONTACT_ENCRYPTION_KEY"]),
            hmac_key=decode_secret_key(os.environ["WEF_CONTACT_HMAC_KEY"]),
        )
        await PersistOfferContacts(SQLAlchemyContactStore(database.session_factory), cipher)(
            offer_id=OFFER_ID,
            source_message_id=None,
            contacts=(ContactInput(kind=ContactKind.PHONE, value=SYNTHETIC_CONTACT),),
        )
        await seed_media(database.session_factory)
    finally:
        await database.engine.dispose()


async def seed_media(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create two invented images and a source/revision anchor for gallery joins."""
    # This helper receives the same typed SQLAlchemy factory as the production seed.
    channel, message, revision = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 8, 1, 10, tzinfo=UTC)
    public = Path("/e2e-public")
    await asyncio.to_thread(public.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread((public / "e2e-glyphs.pbf").write_bytes, b"\x0a\x00")
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO source_channels (id, platform, external_id, display_name) "
                "VALUES (:id, 'telegram', 'e2e-media', 'Synthetic browser media')"
            ),
            {"id": channel},
        )
        await session.execute(
            text(
                "INSERT INTO source_messages (id, source_channel_id, "
                "external_message_id, current_revision_id, message_type, published_at, "
                "text_original, entities_json, raw_payload_json, raw_checksum, "
                "ingested_at) VALUES (:id, :channel, 1, :revision, 'message', :now, "
                "'Synthetic browser image source', '[]', '{}', :checksum, :now)"
            ),
            {
                "id": message,
                "channel": channel,
                "revision": revision,
                "now": now,
                "checksum": "e" * 64,
            },
        )
        await session.execute(
            text(
                "INSERT INTO source_message_revisions (id, source_message_id, "
                "revision_number, captured_at, message_type, published_at, "
                "text_original, entities_json, raw_payload_json, raw_checksum) VALUES "
                "(:id, :message, 1, :now, 'message', :now, 'Synthetic browser image "
                "source', '[]', '{}', :checksum)"
            ),
            {"id": revision, "message": message, "now": now, "checksum": "e" * 64},
        )
        for index, color in enumerate(("#385f7a", "#ca854b")):
            content = BytesIO()
            Image.new("RGB", (160, 100), color).save(content, format="JPEG")
            payload = content.getvalue()
            key = f"e2e-{index}.jpg"
            await asyncio.to_thread((public / key).write_bytes, payload)
            checksum = hashlib.sha256(payload).hexdigest()
            original_id, public_id, asset_id = uuid4(), uuid4(), uuid4()
            for object_id, storage_class, object_key in [
                (original_id, "restricted_original", f"original/{key}"),
                (public_id, "public_derivative", key),
            ]:
                await session.execute(
                    text(
                        "INSERT INTO stored_media_objects (id, storage_backend, storage_key, "
                        "storage_class, checksum_sha256, mime_type, byte_size) VALUES (:id, "
                        "'local_filesystem', :key, :class, :checksum, 'image/jpeg', :size)"
                    ),
                    {
                        "id": object_id,
                        "key": object_key,
                        "class": storage_class,
                        "checksum": checksum,
                        "size": len(payload),
                    },
                )
            await session.execute(
                text(
                    "INSERT INTO media_assets (id, source_message_id, source_ordinal, "
                    "source_descriptor_json, stored_object_id, stored_object_storage_class,"
                    " media_type, mime_type, byte_size, width, height) VALUES (:id, "
                    ":message, :ordinal, '{}', :object, 'restricted_original', 'image', "
                    "'image/jpeg', :size, 160, 100)"
                ),
                {
                    "id": asset_id,
                    "message": message,
                    "ordinal": index,
                    "object": original_id,
                    "size": len(payload),
                },
            )
            for variant in ("thumbnail_webp_v1", "thumbnail_jpeg_v1"):
                await session.execute(
                    text(
                        "INSERT INTO media_derivatives (id, media_asset_id, stored_object_id, "
                        "stored_object_storage_class, variant, width, height) VALUES (:id, "
                        ":asset, :object, 'public_derivative', :variant, 160, 100)"
                    ),
                    {"id": uuid4(), "asset": asset_id, "object": public_id, "variant": variant},
                )
            await session.execute(
                text(
                    "INSERT INTO offer_media (offer_id, media_asset_id, position, "
                    "association_rule, association_confidence) VALUES (:offer, :asset, "
                    ":position, 'same_message', 1)"
                ),
                {"offer": OFFER_ID, "asset": asset_id, "position": index},
            )


if __name__ == "__main__":
    asyncio.run(seed())
