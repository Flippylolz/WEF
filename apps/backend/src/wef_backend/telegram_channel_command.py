"""Operator CLI: verify public Telegram channel identity and env credentials."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.features.ingestion.application.telegram_channel_verify import (
    verify_telegram_channel_access,
)
from wef_backend.features.ingestion.domain.telegram_channel import TelegramChannelIdentity
from wef_backend.features.ingestion.domain.telegram_secrets import (
    credentials_present,
    unwrap_secret,
)
from wef_backend.features.ingestion.infrastructure.public_http import (
    fetch_public_url_status,
)
from wef_backend.settings import load_settings
from wef_backend.telegram_credentials import secret_text


def _identity_from_settings() -> TelegramChannelIdentity:
    settings = load_settings()
    return TelegramChannelIdentity(
        username=settings.telegram_channel_username,
        channel_id=settings.telegram_channel_id,
        channel_title=settings.telegram_channel_title,
        message_link_template=settings.telegram_message_link_template,
    )


async def run() -> dict[str, object]:
    """Execute verification and return a JSON-serializable report."""
    settings = load_settings()
    api_hash = secret_text(settings.telegram_api_hash)
    session = secret_text(settings.telegram_session)
    if not session and settings.telegram_session_path is not None:
        path = settings.telegram_session_path
        session = unwrap_secret(path.read_text(encoding="utf-8")) if path.is_file() else None
    result = await verify_telegram_channel_access(
        _identity_from_settings(),
        credentials_ready=credentials_present(
            api_id=settings.telegram_api_id,
            api_hash=api_hash,
        ),
        session_ready=bool(session),
        get=fetch_public_url_status,
    )
    payload = asdict(result)
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
