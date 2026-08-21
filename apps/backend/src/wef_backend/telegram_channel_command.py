"""Operator CLI: verify public Telegram channel identity and secret paths."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.features.ingestion.application.telegram_channel_verify import (
    verify_telegram_channel_access,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramChannelIdentity,
    TelegramWorkerSecretPaths,
)
from wef_backend.features.ingestion.infrastructure.public_http import (
    fetch_public_url_status,
)
from wef_backend.settings import load_settings


def _identity_from_settings() -> TelegramChannelIdentity:
    settings = load_settings()
    return TelegramChannelIdentity(
        username=settings.telegram_channel_username,
        channel_id=settings.telegram_channel_id,
        channel_title=settings.telegram_channel_title,
        message_link_template=settings.telegram_message_link_template,
    )


def _secret_paths_from_settings() -> TelegramWorkerSecretPaths:
    settings = load_settings()
    return TelegramWorkerSecretPaths(
        api_id_file=settings.telegram_api_id_file,
        api_hash_file=settings.telegram_api_hash_file,
        session_file=settings.telegram_session_file,
    )


async def run() -> dict[str, object]:
    """Execute verification and return a JSON-serializable report."""
    result = await verify_telegram_channel_access(
        _identity_from_settings(),
        _secret_paths_from_settings(),
        get=fetch_public_url_status,
    )
    payload = asdict(result)
    payload["secret_files"] = [asdict(item) for item in result.secret_files]
    payload["operating_owner"] = "dedicated_telegram_user_not_bot"
    return payload


def main() -> None:
    """Print a redacted JSON report; exit 2 when public identity fails."""
    try:
        payload = asyncio.run(run())
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram channel verification failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    if payload.get("status") == "public_unreachable":
        raise SystemExit(2)
