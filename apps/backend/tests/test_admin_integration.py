"""Integration coverage for admin audit persistence and account listing."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text

from wef_backend.database import create_database_resources
from wef_backend.features.admin.application.admin_ops import AdminAuditEvent, AdminOutcome
from wef_backend.features.admin.infrastructure.store import SQLAlchemyAdminAuditStore
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.infrastructure.models import UserRow
from wef_backend.features.identity.infrastructure.store import SQLAlchemyIdentityStore
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


async def test_admin_audit_store_and_account_listing() -> None:
    """Persist a redacted admin audit and list accounts through SQLAlchemy."""
    assert TEST_DATABASE_URL is not None
    settings = Settings(
        env="test",
        database_url=TEST_DATABASE_URL,
        alembic_config=Path("alembic.ini"),
    )
    database = create_database_resources(TEST_DATABASE_URL)
    identity = SQLAlchemyIdentityStore(database.session_factory)
    audits = SQLAlchemyAdminAuditStore(database.session_factory)
    owner_id = uuid4()
    user_id = uuid4()

    await asyncio.to_thread(command.upgrade, alembic_config(settings), "head")
    async with database.session_factory.begin() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == EXPECTED_DATABASE_REVISION
        await session.execute(text("DELETE FROM admin_audit_events"))
        await session.execute(text("DELETE FROM auth_sessions"))
        await session.execute(text("DELETE FROM users"))
        now = datetime.now(UTC)
        session.add(
            UserRow(
                id=owner_id,
                username_normalized="owner",
                username_display="owner",
                hashed_password="hash",
                role=UserRole.OWNER.value,
                is_active=True,
                must_change_password=False,
                created_at=now,
                updated_at=now,
            ),
        )
        session.add(
            UserRow(
                id=user_id,
                username_normalized="buyer",
                username_display="buyer",
                hashed_password="hash",
                role=UserRole.USER.value,
                is_active=True,
                must_change_password=False,
                created_at=now,
                updated_at=now,
            ),
        )

    await audits.record(
        AdminAuditEvent(
            id=uuid4(),
            owner_user_id=owner_id,
            target_user_id=user_id,
            target_type="user",
            target_id=str(user_id),
            action="disable_user",
            occurred_at=datetime.now(UTC),
            request_id=uuid4(),
            outcome=AdminOutcome.ALLOWED,
        ),
    )
    listed = await audits.list_recent(limit=10)
    assert len(listed) == 1
    assert listed[0].action == "disable_user"
    assert listed[0].outcome is AdminOutcome.ALLOWED

    accounts = await identity.list_accounts(limit=10)
    assert {account.id for account in accounts} == {owner_id, user_id}
    assert await identity.count_active_owners() == 1
