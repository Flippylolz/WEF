"""Optional maintenance owner for bounded parser recovery and owner cohorts."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.composition import build_services
from wef_backend.features.admin.application.automatic_recovery import AutomaticRecovery
from wef_backend.features.admin.infrastructure.ai_enrichment_store import (
    SQLAlchemyOfferAiEnrichmentStore,
)
from wef_backend.features.admin.infrastructure.ingestion_ai_parse_store import (
    SQLAlchemyIngestionAiParseStore,
)
from wef_backend.features.admin.infrastructure.recovery_queue import SQLAlchemyRecoveryQueue
from wef_backend.features.ingestion.infrastructure.parse_issue_backfill import backfill_parse_issues

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.settings import Settings

logger = structlog.get_logger("wef.automatic_recovery")


async def maintain_automatic_recovery(
    settings: Settings,
    sessions: async_sessionmaker[AsyncSession],
    stop: asyncio.Event,
    live_ready: Callable[[], bool],
) -> None:
    """Stay disabled until explicit activation evidence; never block live ingestion."""
    services = None
    last_status = None
    try:
        while not stop.is_set():
            active = (
                settings.ai_recovery_enabled
                and settings.ai_recovery_activation_verified
                and settings.ai_curation_enabled
                and settings.groq_model == "openai/gpt-oss-20b"
                and settings.groq_zdr_verified
                and settings.groq_api_key is not None
                and isinstance(settings.ai_recovery_owner_id, UUID)
            )
            status = "disabled"
            owner = settings.ai_recovery_owner_id
            if active and isinstance(owner, UUID) and live_ready():
                if services is None:
                    services = build_services(replace_settings(settings))
                try:
                    async with sessions() as session:
                        authorized = await session.scalar(
                            text(
                                "SELECT id FROM users WHERE id=:owner "
                                "AND role='owner' AND is_active"
                            ),
                            {"owner": owner},
                        )
                except SQLAlchemyError:
                    authorized = None
                if authorized is None:
                    status = "activation_unavailable"
                else:
                    try:
                        await backfill_parse_issues(sessions, limit=10, batch_size=10)
                        queue = SQLAlchemyRecoveryQueue(sessions)
                        admin = services.admin
                        recovery = AutomaticRecovery(
                            queue,
                            admin.generate_ingestion_ai_parse,
                            admin.apply_ingestion_ai_parse,
                            SQLAlchemyIngestionAiParseStore(sessions),
                            admin.start_offer_enrichment,
                            admin.process_offer_enrichment,
                            SQLAlchemyOfferAiEnrichmentStore(sessions),
                        )
                        await recovery.tick(
                            owner,
                            datetime.now(UTC),
                            submit=True,
                            apply=settings.ai_recovery_auto_apply,
                        )
                        # Owner cohorts use the same ledger and resume across budget windows.
                        async with sessions() as session:
                            batch = await session.scalar(
                                text("""
                                SELECT b.id FROM offer_ai_enrichment_batches b
                                WHERE b.owner_user_id=:owner AND b.state IN ('queued','running')
                                  AND NOT EXISTS (SELECT 1 FROM ai_recovery_work w WHERE w.id=b.id)
                                ORDER BY b.created_at,b.id LIMIT 1
                            """),
                                {"owner": owner},
                            )
                        if batch is not None and live_ready():
                            await admin.process_offer_enrichment(
                                owner_id=owner, batch_id=batch, request_id=batch
                            )
                        status = "running"
                    except Exception:  # noqa: BLE001 - isolate optional maintenance, retain claims
                        # A failed claim/attempt survives for bounded reconciliation.
                        status = "recovery_failed"
            if status != last_status:
                logger.info("parser_recovery_status", status=status)
                last_status = status
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=60)
    finally:
        if services is not None:
            await services.close()


def replace_settings(settings: Settings) -> Settings:
    """Use only reviewed scalar families when automatic application is enabled."""
    return settings.model_copy(update={"groq_use_batch_api": False})
