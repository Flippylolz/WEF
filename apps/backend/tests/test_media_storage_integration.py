"""Media migration, replay, deduplication, and class-constraint integration tests."""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from PIL import Image
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from wef_backend.database import DatabaseResources, create_database_resources
from wef_backend.features.catalog.application import SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.features.ingestion.application.media_storage import MediaWorkItem, ProcessMedia
from wef_backend.features.ingestion.domain.media_grouping import MediaAssociationRule
from wef_backend.features.ingestion.domain.model import MediaDescriptor, MediaKind
from wef_backend.features.ingestion.infrastructure.media_filesystem import LocalMediaStorage
from wef_backend.features.ingestion.infrastructure.media_repository import SQLAlchemyMediaRepository
from wef_backend.migration import alembic_config
from wef_backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is not configured"),
]


def _settings() -> Settings:
    assert TEST_DATABASE_URL is not None
    return Settings(env="test", database_url=TEST_DATABASE_URL, alembic_config=Path("alembic.ini"))


async def _prepare() -> tuple[DatabaseResources, UUID, UUID, UUID]:
    """Upgrade, clear media/source rows, seed an offer, and create one source revision."""
    assert TEST_DATABASE_URL is not None
    await asyncio.to_thread(command.upgrade, alembic_config(_settings()), "head")
    database = create_database_resources(TEST_DATABASE_URL)
    async with database.session_factory() as session:
        for statement in (
            "DELETE FROM offer_media",
            "DELETE FROM media_derivative_attempts",
            "DELETE FROM media_derivatives",
            "DELETE FROM media_disposition_attempts",
            "DELETE FROM media_assets",
            "DELETE FROM stored_media_objects",
            "DELETE FROM offer_field_origins",
            "DELETE FROM offer_ai_field_events",
            "DELETE FROM offer_ai_enrichment_items",
            "DELETE FROM offer_ai_enrichment_batches",
            "DELETE FROM place_ai_review_runs",
            "DELETE FROM offer_sources",
            "DELETE FROM offers",
            "DELETE FROM developments",
            "UPDATE source_messages SET current_revision_id = NULL",
            "DELETE FROM source_message_revisions",
            "DELETE FROM source_messages",
            "DELETE FROM ingest_runs",
            "DELETE FROM source_channels",
            "DELETE FROM locations",
        ):
            await session.execute(text(statement))
        await session.commit()
    locations, offers = m1_fixture()
    await SeedM1Catalog(SQLAlchemyCatalogSeedAdapter(database.session_factory), environment="test")(
        locations,
        offers,
    )
    channel_id, message_id, revision_id = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 8, 15, 6, 30, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO source_channels "
                "(id, platform, external_id, display_name) "
                "VALUES (:id, 'telegram', 'media-test', 'Synthetic media test')"
            ),
            {"id": channel_id},
        )
        await session.execute(
            text(
                "INSERT INTO source_messages "
                "(id, source_channel_id, external_message_id, current_revision_id, message_type, "
                "published_at, text_original, entities_json, raw_payload_json, raw_checksum, "
                "ingested_at) VALUES (:id, :channel, 1, :revision, 'message', :now, '', "
                "'[]', '{}', :checksum, :now)"
            ),
            {
                "id": message_id,
                "channel": channel_id,
                "revision": revision_id,
                "now": now,
                "checksum": "a" * 64,
            },
        )
        await session.execute(
            text(
                "INSERT INTO source_message_revisions "
                "(id, source_message_id, revision_number, captured_at, message_type, published_at, "
                "text_original, entities_json, raw_payload_json, raw_checksum) "
                "VALUES (:id, :message, 1, :now, 'message', :now, '', '[]', '{}', :checksum)"
            ),
            {
                "id": revision_id,
                "message": message_id,
                "now": now,
                "checksum": "a" * 64,
            },
        )
    return database, message_id, revision_id, offers[0].id


def _write_image(path: Path, color: str = "red") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color).save(path, format="JPEG")


def _item(message_id: UUID, revision_id: UUID, offer_id: UUID, ordinal: int) -> MediaWorkItem:
    return MediaWorkItem(
        source_message_id=message_id,
        source_message_revision_id=revision_id,
        source_ordinal=ordinal,
        descriptor=MediaDescriptor(
            kind=MediaKind.PHOTO,
            path="photos/synthetic.jpg",
            mime_type="image/jpeg",
        ),
        association_version="e2-media-v1",
        offer_id=offer_id,
        association_rule=MediaAssociationRule.EXPLICIT_GROUP,
        association_confidence=0.95,
    )


async def test_media_replay_class_scoped_dedup_and_explicit_group(tmp_path: Path) -> None:
    """Objects dedupe by class while ordinals, attempts, and E2 association survive."""
    database, message_id, revision_id, offer_id = await _prepare()
    source = tmp_path / "source/photos/synthetic.jpg"
    _write_image(source)
    filesystem = LocalMediaStorage(
        tmp_path / "source",
        tmp_path / "originals",
        tmp_path / "public",
    )
    process = ProcessMedia(filesystem, SQLAlchemyMediaRepository(database.session_factory))
    first = await process(_item(message_id, revision_id, offer_id, 0))
    replay = await process(_item(message_id, revision_id, offer_id, 0))
    second_ordinal = await process(_item(message_id, revision_id, offer_id, 1))
    assert not first.replayed
    assert replay.replayed
    assert not second_ordinal.replayed

    async with database.session_factory() as session:
        counts = (
            await session.execute(
                text(
                    "SELECT (SELECT count(*) FROM stored_media_objects), "
                    "(SELECT count(*) FROM media_assets), "
                    "(SELECT count(*) FROM media_disposition_attempts), "
                    "(SELECT count(*) FROM media_derivatives), "
                    "(SELECT count(*) FROM media_derivative_attempts), "
                    "(SELECT count(*) FROM offer_media)"
                ),
            )
        ).one()
        objects = (
            await session.execute(
                text(
                    "SELECT storage_class, count(*) FROM stored_media_objects "
                    "GROUP BY storage_class ORDER BY storage_class"
                ),
            )
        ).all()
        associations = (
            await session.execute(
                text(
                    "SELECT position, association_rule, association_confidence "
                    "FROM offer_media ORDER BY position"
                ),
            )
        ).all()
        ordinals = (
            (
                await session.execute(
                    text("SELECT source_ordinal FROM media_assets ORDER BY source_ordinal"),
                )
            )
            .scalars()
            .all()
        )
    assert tuple(counts) == (3, 2, 2, 4, 4, 2)
    assert [(str(row[0]), int(row[1])) for row in objects] == [
        ("public_derivative", 2),
        ("restricted_original", 1),
    ]
    assert ordinals == [0, 1]
    assert [row.position for row in associations] == [0, 1]
    assert all(row.association_rule == "explicit_group" for row in associations)
    await database.engine.dispose()


async def test_changed_bytes_and_unread_transition_append_attempts(tmp_path: Path) -> None:
    """Unread-to-readable and readable replacement identities never reuse stale attempts."""
    database, message_id, revision_id, offer_id = await _prepare()
    filesystem = LocalMediaStorage(
        tmp_path / "source",
        tmp_path / "originals",
        tmp_path / "public",
    )
    filesystem.source_root.mkdir()
    repository = SQLAlchemyMediaRepository(database.session_factory)
    process = ProcessMedia(filesystem, repository)
    item = _item(message_id, revision_id, offer_id, 0)
    missing = await process(item)
    assert missing.observation.observed_checksum_sha256 is None
    source = filesystem.source_root / item.descriptor.path
    _write_image(source, "red")
    readable = await process(item)
    _write_image(source, "blue")
    replaced = await process(item)
    assert readable.observation.content_identity != replaced.observation.content_identity
    async with database.session_factory() as session:
        attempts = (
            await session.execute(
                text(
                    "SELECT observation_status, content_identity FROM media_disposition_attempts "
                    "ORDER BY attempted_at, id"
                ),
            )
        ).all()
        asset_count = await session.scalar(text("SELECT count(*) FROM media_assets"))
    assert len(attempts) == 3
    assert attempts[0].content_identity == "unread:missing"
    assert {row.observation_status for row in attempts[1:]} == {"read_observed"}
    assert asset_count == 1
    await database.engine.dispose()


async def test_database_rejects_cross_class_asset_reference() -> None:
    """A logical source asset cannot reference a public derivative object."""
    database, message_id, _, _ = await _prepare()
    object_id, asset_id = uuid4(), uuid4()
    async with database.session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO stored_media_objects "
                "(id, storage_backend, storage_key, storage_class, checksum_sha256, mime_type, "
                "byte_size) VALUES (:id, 'local_filesystem', :key, 'public_derivative', "
                ":checksum, 'image/webp', 1)"
            ),
            {"id": object_id, "key": "opaque/public", "checksum": "c" * 64},
        )
        await session.commit()
        statement = text(
            "INSERT INTO media_assets "
            "(id, source_message_id, source_ordinal, source_descriptor_json, "
            "stored_object_id, stored_object_storage_class, media_type, mime_type, byte_size) "
            "VALUES (:id, :message, 0, '{}', :object, 'public_derivative', "
            "'image', 'image/webp', 1)"
        )
        with pytest.raises(IntegrityError):
            await session.execute(
                statement,
                {"id": asset_id, "message": message_id, "object": object_id},
            )
        await session.rollback()
    await database.engine.dispose()
