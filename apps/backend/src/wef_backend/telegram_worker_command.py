"""Telegram worker: authorize, persist string session, listen for channel events."""

from __future__ import annotations

import asyncio
import sys
from contextlib import suppress
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.application.raw_archive import RawEventDrainer
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEventProcessor,
)
from wef_backend.features.ingestion.application.telegram_live import verify_channel_entity
from wef_backend.features.ingestion.application.telegram_reconciliation import (
    TelegramCheckpointReconciler,
    TelegramCheckpointStore,
    TelegramReconciliationRequest,
    maintain_checkpoint_reconciliation,
    read_durable_telegram_checkpoint,
)
from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    WorkerRuntimeState,
    maintain_worker_heartbeat,
)
from wef_backend.features.ingestion.application.telegram_worker_supervision import (
    CriticalWorkerTaskError,
    supervise_worker_tasks,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramChannelIdentity,
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramLoginCodeError,
    TelegramSecretError,
    persist_telegram_session,
)
from wef_backend.features.ingestion.infrastructure.persistence_adapter import (
    SQLAlchemyIngestionPersistence,
)
from wef_backend.features.ingestion.infrastructure.raw_event_archive import (
    SQLAlchemyRawEventArchive,
)
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import TelethonLiveClient
from wef_backend.logging_config import configure_logging, configure_safe_telethon_logging
from wef_backend.settings import Settings, load_settings
from wef_backend.telegram_credentials import secret_text, secrets_from_settings

logger = structlog.get_logger("wef.telegram_worker")

_DRAIN_INTERVAL_SECONDS = 5.0


def _log_stage_failure(*, stage: str, category: str) -> None:
    """Emit one allowlisted failure without attaching exception information."""
    logger.error(
        "telegram_worker_stage_failed",
        stage=stage,
        category=category,
    )


async def _maintain_raw_archive_drain(
    drainer: RawEventDrainer,
    state: WorkerRuntimeState,
    stop: asyncio.Event,
    release_sha: str | None,
    processing_lock: asyncio.Lock,
) -> None:
    """Repeat bounded archive drains until the worker stops."""
    while not stop.is_set():
        with suppress(asyncio.CancelledError):
            drained = await drainer.drain_once(
                release_sha=release_sha,
                processing_lock=processing_lock,
            )
            if drained:
                state.last_event_committed_at = datetime.now(UTC)
                logger.info(
                    "telegram_raw_archive_drained",
                    stage="raw_archive",
                    events=drained,
                )
        await asyncio.sleep(_DRAIN_INTERVAL_SECONDS)


async def _run_connected_worker(  # noqa: PLR0913
    *,
    settings: Settings,
    identity: TelegramChannelIdentity,
    client: TelethonLiveClient,
    store: SQLAlchemyIngestionPersistence,
    archive: SQLAlchemyRawEventArchive,
    checkpoint_store: TelegramCheckpointStore,
) -> None:
    """Subscribe and supervise every critical stage after authorization."""
    state = WorkerRuntimeState(release_sha=settings.release_sha)
    stop = asyncio.Event()
    queue = LiveEventQueue()
    client.subscribe_channel(identity.username, queue)
    processor = LiveTelegramEventProcessor(store=store, client=client, archive=archive)
    processing_lock = asyncio.Lock()
    drainer = RawEventDrainer(
        archive=archive,
        processor=processor,
        identity=identity,
        checkpoint_store=checkpoint_store,
    )
    reconciler = TelegramCheckpointReconciler(
        store=checkpoint_store,
        client=client,
        processor=processor,
        processing_lock=processing_lock,
    )
    logger.info(
        "telegram_worker_started",
        stage="startup",
        release_sha=(settings.release_sha or "")[:12] or None,
    )

    async def consume() -> None:
        state.consumer_running = True
        try:
            while True:
                event = await queue.get()
                if event is None:
                    return
                state.last_event_received_at = event.received_at
                async with processing_lock:
                    checkpoint = await read_durable_telegram_checkpoint(
                        checkpoint_store,
                        channel_external_id=identity.channel_id,
                    )
                    result = await processor(
                        identity=identity,
                        events=(event,),
                        resume_after_external_id=checkpoint,
                        release_sha=settings.release_sha,
                        manage_connection=False,
                    )
                state.local_checkpoint_external_id = result.checkpoint_external_message_id
                state.last_event_committed_at = datetime.now(UTC)
                state.last_error_category = None
                logger.info(
                    "telegram_event_committed",
                    stage="consumer",
                    event_kind=event.kind.value,
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            _log_stage_failure(stage="consumer", category=state.record_failure(error))
            raise
        finally:
            state.consumer_running = False

    async def transport() -> None:
        state.transport_connected = True
        try:
            await client.run_until_disconnected()
        finally:
            state.transport_connected = False

    try:
        await supervise_worker_tasks(
            {
                "transport": transport(),
                "consumer": consume(),
                "raw_archive_drain": _maintain_raw_archive_drain(
                    drainer, state, stop, settings.release_sha, processing_lock
                ),
                "health": maintain_worker_heartbeat(
                    settings.telegram_heartbeat_path,
                    is_connected=client.is_connected,
                    stop=stop,
                    state=state,
                    runtime_health_path=settings.telegram_runtime_health_path,
                ),
                "reconciliation": maintain_checkpoint_reconciliation(
                    reconciler,
                    TelegramReconciliationRequest(
                        identity=identity,
                        overlap=settings.telegram_reconciliation_overlap,
                        batch_size=settings.telegram_reconciliation_batch_size,
                        max_messages=settings.telegram_reconciliation_max_messages,
                        release_sha=settings.release_sha,
                    ),
                    state=state,
                    stop=stop,
                    interval=settings.telegram_reconciliation_interval_seconds,
                ),
            },
            stop=stop,
        )
    finally:
        stop.set()
        await queue.close()


async def run_telegram_worker() -> None:
    """Authorize, persist the string session, and listen until disconnected."""
    settings = load_settings()
    secrets = secrets_from_settings(settings)
    identity = default_live_channel_identity()
    phone = secret_text(settings.telegram_phone)
    login_code = secret_text(settings.telegram_login_code)
    password = secret_text(settings.telegram_2fa_password)
    client = TelethonLiveClient(secrets)
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SQLAlchemyIngestionPersistence(session_factory)
    checkpoint_store = SQLAlchemyTelegramWorkerStatusStore(session_factory)
    await client.connect()
    try:
        session_string = await client.ensure_authorized(
            phone=phone,
            login_code=login_code,
            password=password,
        )
        with suppress(OSError):
            persist_telegram_session(
                session_string,
                session_path=settings.telegram_session_path,
                env_file=settings.telegram_env_file,
            )
        entity = await client.resolve_channel(identity.username)
        verify_channel_entity(identity, entity)
        await _run_connected_worker(
            settings=settings,
            identity=identity,
            client=client,
            store=store,
            archive=SQLAlchemyRawEventArchive(session_factory),
            checkpoint_store=checkpoint_store,
        )
    finally:
        await client.disconnect()
        await engine.dispose()


def main() -> None:
    """Run the live Telegram worker; fail closed when credentials are missing."""
    settings = load_settings()
    configure_logging(level=settings.log_level, json_logs=settings.env == "production")
    configure_safe_telethon_logging(level=settings.log_level)
    try:
        asyncio.run(run_telegram_worker())
    except TelegramLoginCodeError:
        logger.warning(
            "telegram_worker_authentication_pending",
            stage="authorization",
            category="TelegramLoginCodeError",
        )
        sys.stderr.write(
            "Telegram login code sent; set WEF_TELEGRAM_LOGIN_CODE and restart\n",
        )
        raise SystemExit(3) from None
    except TelegramSecretError:
        _log_stage_failure(
            stage="authorization",
            category="TelegramSecretError",
        )
        sys.stderr.write("Telegram worker secrets unavailable or invalid\n")
        raise SystemExit(2) from None
    except CriticalWorkerTaskError as error:
        _log_stage_failure(
            stage=error.stage,
            category=error.category,
        )
        sys.stderr.write("Telegram worker failed\n")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        _log_stage_failure(
            stage="startup_or_shutdown",
            category="UnexpectedError",
        )
        sys.stderr.write("Telegram worker failed\n")
        raise SystemExit(2) from None
