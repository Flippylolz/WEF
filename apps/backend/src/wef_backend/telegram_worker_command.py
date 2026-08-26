"""Telegram worker: authorize, persist string session, listen for channel events."""

from __future__ import annotations

import asyncio
import sys
from contextlib import suppress

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEventProcessor,
)
from wef_backend.features.ingestion.application.telegram_live import verify_channel_entity
from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    maintain_worker_heartbeat,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
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
from wef_backend.features.ingestion.infrastructure.telethon_client import TelethonLiveClient
from wef_backend.settings import load_settings
from wef_backend.telegram_credentials import secret_text, secrets_from_settings


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
        queue = LiveEventQueue()
        client.subscribe_channel(identity.username, queue)
        processor = LiveTelegramEventProcessor(store=store, client=client)
        stop_heartbeat = asyncio.Event()
        heartbeat = asyncio.create_task(
            maintain_worker_heartbeat(
                settings.telegram_heartbeat_path,
                is_connected=client.is_connected,
                stop=stop_heartbeat,
            ),
        )

        async def consume() -> None:
            while True:
                event = await queue.get()
                if event is None:
                    return
                await processor(
                    identity=identity,
                    events=(event,),
                    release_sha=settings.release_sha,
                    manage_connection=False,
                )

        consumer = asyncio.create_task(consume())
        try:
            await client.run_until_disconnected()
        finally:
            stop_heartbeat.set()
            await heartbeat
            await queue.close()
            await consumer
    finally:
        await client.disconnect()
        await engine.dispose()


def main() -> None:
    """Run the live Telegram worker; fail closed when credentials are missing."""
    try:
        asyncio.run(run_telegram_worker())
    except TelegramLoginCodeError:
        sys.stderr.write(
            "Telegram login code sent; set WEF_TELEGRAM_LOGIN_CODE and restart\n",
        )
        raise SystemExit(3) from None
    except TelegramSecretError:
        sys.stderr.write("Telegram worker secrets unavailable or invalid\n")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram worker failed\n")
        raise SystemExit(2) from None
