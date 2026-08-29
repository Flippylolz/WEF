"""View-history migration and SQLAlchemy adapter checks against PostGIS."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.features.identity.application import RegisterAccount
from wef_backend.features.identity.infrastructure import (
    PwdlibPasswordHasher,
    SQLAlchemyIdentityStore,
    SQLAlchemyViewHistoryStore,
)
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


async def test_visit_and_offer_view_history_persist_idempotently() -> None:
    """Migrate, capture stable visit baselines, and aggregate public offer views."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    locations, offers = m1_fixture()
    location_ids = tuple(item.id for item in locations)
    offer_ids = tuple(item.id for item in offers)
    user_id: UUID | None = None

    try:
        await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")
        await SeedM1Catalog(
            SQLAlchemyCatalogSeedAdapter(database.session_factory),
            environment="test",
        )(locations, offers)
        identity_store = SQLAlchemyIdentityStore(database.session_factory)
        account = await RegisterAccount(identity_store, PwdlibPasswordHasher())(
            username=f"views-{uuid4().hex[:12]}",
            password="integrationpass1",
        )
        user_id = account.id
        store = SQLAlchemyViewHistoryStore(database.session_factory)
        first_id = uuid4()
        second_id = uuid4()
        first_at = datetime(2026, 8, 29, 8, 0, tzinfo=UTC)
        second_at = first_at + timedelta(hours=1)

        first = await store.start_visit(
            user_id=account.id,
            visit_id=first_id,
            started_at=first_at,
        )
        replay = await store.start_visit(
            user_id=account.id,
            visit_id=first_id,
            started_at=second_at,
        )
        second = await store.start_visit(
            user_id=account.id,
            visit_id=second_id,
            started_at=second_at,
        )
        viewed_once = await store.mark_offer_viewed(
            user_id=account.id,
            offer_id=offer_ids[0],
            viewed_at=first_at,
        )
        viewed_twice = await store.mark_offer_viewed(
            user_id=account.id,
            offer_id=offer_ids[0],
            viewed_at=second_at,
        )
        hidden = await store.mark_offer_viewed(
            user_id=account.id,
            offer_id=uuid4(),
            viewed_at=second_at,
        )
        history = await store.list_viewed_offers(account.id)

        assert first.previous_visit_at is None
        assert replay == first
        assert second.previous_visit_at == first.current_visit_at
        assert viewed_once is not None
        assert viewed_once.view_count == 1
        assert viewed_twice is not None
        assert viewed_twice.view_count == 2
        assert viewed_twice.first_viewed_at == viewed_once.first_viewed_at
        assert hidden is None
        assert history == (viewed_twice,)
        async with database.session_factory() as session:
            revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == EXPECTED_DATABASE_REVISION
    finally:
        async with database.engine.begin() as connection:
            if user_id is not None:
                await connection.execute(
                    text("DELETE FROM users WHERE id = :user_id"),
                    {"user_id": user_id},
                )
            await connection.execute(
                text("DELETE FROM offers WHERE id = ANY(:ids)"),
                {"ids": offer_ids},
            )
            await connection.execute(
                text("DELETE FROM locations WHERE id = ANY(:ids)"),
                {"ids": location_ids},
            )
        await database.engine.dispose()
