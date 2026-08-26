"""Composition-root helper: map Settings into Telegram worker secrets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramWorkerSecrets,
    load_telegram_worker_secrets,
    unwrap_secret,
)

if TYPE_CHECKING:
    from wef_backend.settings import Settings


def secret_text(value: object | None) -> str | None:
    """Return stripped secret text without logging it."""
    if value is None:
        return None
    getter = getattr(value, "get_secret_value", None)
    text = getter() if callable(getter) else str(value)
    return unwrap_secret(text)


def secrets_from_settings(settings: Settings) -> TelegramWorkerSecrets:
    """Build worker secrets from environment-backed settings."""
    return load_telegram_worker_secrets(
        api_id=settings.telegram_api_id,
        api_hash=secret_text(settings.telegram_api_hash),
        session=secret_text(settings.telegram_session),
        session_path=settings.telegram_session_path,
    )
