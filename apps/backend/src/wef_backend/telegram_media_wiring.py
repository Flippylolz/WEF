"""Wire live Telegram media processing at the composition root."""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003 — used at runtime for filesystem roots
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.live_media import LiveMediaPipeline
from wef_backend.features.ingestion.application.media_grouping import StatefulMediaGrouper
from wef_backend.features.ingestion.application.media_recovery import MediaRecoveryRunner
from wef_backend.features.ingestion.application.media_storage import ProcessMedia
from wef_backend.features.ingestion.domain.media_storage import MediaLimits
from wef_backend.features.ingestion.infrastructure.complete_import_repository import (
    SQLAlchemyCompleteImportRepository,
)
from wef_backend.features.ingestion.infrastructure.media_filesystem import LocalMediaStorage
from wef_backend.features.ingestion.infrastructure.media_recovery_execution import (
    RecoverStoredMedia,
)
from wef_backend.features.ingestion.infrastructure.media_recovery_store import (
    SQLAlchemyMediaRecoveryStore,
)
from wef_backend.features.ingestion.infrastructure.media_repository import SQLAlchemyMediaRepository
from wef_backend.features.ingestion.infrastructure.telethon_live_media import (
    LiveMediaDownloadLimits,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.application.media_recovery import MediaSourcePort
    from wef_backend.settings import Settings


def live_media_download_limits(
    *,
    max_bytes: int,
    timeout_seconds: float,
) -> LiveMediaDownloadLimits:
    """Build bounded download policy from explicit limits."""
    return LiveMediaDownloadLimits(
        max_bytes=max_bytes,
        timeout_seconds=timeout_seconds,
    )


def build_live_media_pipeline(  # noqa: PLR0913
    session_factory: async_sessionmaker[AsyncSession],
    *,
    source_root: Path,
    originals_root: Path,
    derivatives_root: Path,
    media_max_bytes: int,
    media_max_pixels: int,
    concurrency: int,
    grouper: StatefulMediaGrouper | None = None,
) -> LiveMediaPipeline:
    """Wire the shared media processor for live Telegram ingestion."""
    source_root.mkdir(parents=True, exist_ok=True)
    processor = ProcessMedia(
        filesystem=LocalMediaStorage(
            source_root=source_root,
            originals_root=originals_root,
            derivatives_root=derivatives_root,
            limits=MediaLimits(
                max_bytes=media_max_bytes,
                max_pixels=media_max_pixels,
            ),
        ),
        repository=SQLAlchemyMediaRepository(session_factory),
        persistence_lock=asyncio.Lock(),
    )
    return LiveMediaPipeline(
        processor=processor,
        anchors=SQLAlchemyCompleteImportRepository(session_factory),
        grouper=grouper or StatefulMediaGrouper(),
        concurrency=concurrency,
    )


def build_media_recovery(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    settings: Settings,
    source: MediaSourcePort,
    channel_external_id: str,
) -> MediaRecoveryRunner:
    """Compose independent recovery using the existing storage and staging limits."""
    filesystem = LocalMediaStorage(
        source_root=settings.telegram_media_temp_path,
        originals_root=settings.restricted_originals_path,
        derivatives_root=settings.public_derivatives_path,
        limits=MediaLimits(
            max_bytes=settings.media_max_bytes, max_pixels=settings.media_max_pixels
        ),
    )
    return MediaRecoveryRunner(
        SQLAlchemyMediaRecoveryStore(session_factory, channel_external_id),
        RecoverStoredMedia(session_factory, filesystem, source),
    )
