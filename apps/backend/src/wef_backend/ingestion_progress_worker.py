"""Independent bounded sampling; a monitoring outage cannot stop canonical landing."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

import structlog

from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

if TYPE_CHECKING:
    from wef_backend.features.ingestion.infrastructure.ingestion_progress_store import (
        SQLAlchemyIngestionProgressStore,
    )

logger = structlog.get_logger("wef.ingestion_progress")


async def maintain_ingestion_progress(
    store: SQLAlchemyIngestionProgressStore, stop: asyncio.Event
) -> None:
    """Use existing privacy-safe structured logging only for episode transitions."""
    failed = False
    while not stop.is_set():
        try:
            events = await asyncio.wait_for(store.sample(), timeout=10)
            for event in events:
                logger.warning("ingestion_progress_incident", **event)
            if failed:
                logger.info("ingestion_progress_sampling_recovered")
            failed = False
        except Exception as error:  # noqa: BLE001 — monitor failure must not stop ingestion
            if not failed:
                logger.error(  # noqa: TRY400 — raw exceptions may contain source details
                    "ingestion_progress_sampling_unavailable", category=safe_error_category(error)
                )
            failed = True
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=60)
