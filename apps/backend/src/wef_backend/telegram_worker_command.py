"""Telegram worker entrypoint: fail closed unless activation + secrets are present."""

from __future__ import annotations

import asyncio
import os
import sys

from wef_backend.features.ingestion.application.telegram_live import verify_channel_entity
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramSecretError,
    load_telegram_worker_secrets,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    ACTIVATION_ENV,
    LIVE_LOOP_ENV,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import TelethonLiveClient
from wef_backend.settings import load_settings


async def _probe_authorized_session() -> None:
    """Connect only to prove the session; continuous loop stays explicitly gated."""
    settings = load_settings()
    secrets = load_telegram_worker_secrets(
        api_id_file=settings.telegram_api_id_file,
        api_hash_file=settings.telegram_api_hash_file,
        session_file=settings.telegram_session_file,
    )
    client = TelethonLiveClient(secrets)
    await client.connect()
    try:
        identity = default_live_channel_identity()
        entity = await client.resolve_channel(identity.username)
        verify_channel_entity(identity, entity)
    finally:
        await client.disconnect()


def main() -> None:
    """Refuse to run unless activation gate and secrets are both present."""
    if os.environ.get(ACTIVATION_ENV) != "1":
        sys.stderr.write(
            f"telegram-worker activation gate closed ({ACTIVATION_ENV}!=1); "
            "Compose profile remains disabled by default\n",
        )
        raise SystemExit(2)
    try:
        asyncio.run(_probe_authorized_session())
    except TelegramSecretError:
        sys.stderr.write("Telegram worker secrets unavailable or invalid\n")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram worker failed during authorized session probe\n")
        raise SystemExit(2) from None
    if os.environ.get(LIVE_LOOP_ENV) != "1":
        sys.stdout.write(
            "telegram-worker session probe succeeded; "
            f"continuous live loop remains gated ({LIVE_LOOP_ENV}!=1)\n",
        )
        raise SystemExit(0)
    sys.stderr.write(
        "continuous live loop is not enabled in this revision; "
        "leave LIVE_LOOP unset until owner activation evidence is recorded\n",
    )
    raise SystemExit(2)
