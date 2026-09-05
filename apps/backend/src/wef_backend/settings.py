"""Runtime settings loaded only by the composition root."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID  # noqa: TC003 - Pydantic resolves annotations at runtime

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_dotenv_files() -> None:
    """Load repo-root/.cwd .env for operator CLIs; skip under pytest."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
    except ImportError:
        return
    candidates: list[Path] = [Path.cwd() / ".env"]
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "AGENTS.md").is_file():
            candidates.append(parent / ".env")
            break
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not candidate.is_file():
            continue
        seen.add(resolved)
        load_dotenv(candidate, override=False)


class Settings(BaseSettings):
    """Environment-backed runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="WEF_",
        extra="ignore",
        frozen=True,
        env_ignore_empty=True,
    )

    database_url: str = "postgresql+asyncpg://localhost/wef_proof"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "info"
    env: Literal["development", "test", "production"] = "development"
    alembic_config: Path = Path("alembic.ini")
    source_path: Path = Path("/source")
    historical_export_filename: str = "result.json"
    historical_channel_id: str = "2180077318"
    historical_channel_type: str = "public_channel"
    historical_channel_name: str | None = "El Estate | Покупка Варшава"
    # Live Telegram worker identity (non-secret) plus env-backed credentials.
    telegram_channel_username: str = "elestate_warszawa"
    telegram_channel_id: str = "2180077318"
    telegram_channel_title: str = "El Estate | Покупка Варшава"
    telegram_message_link_template: str = "https://t.me/elestate_warszawa/{message_id}"
    telegram_api_id: int | None = None
    telegram_api_hash: SecretStr | None = None
    telegram_session: SecretStr | None = None
    telegram_phone: str | None = None
    telegram_login_code: SecretStr | None = None
    telegram_2fa_password: SecretStr | None = None
    telegram_session_path: Path | None = None
    telegram_env_file: Path | None = None
    telegram_heartbeat_path: Path = Path("/tmp/wef-telegram-worker.live")  # noqa: S108
    telegram_runtime_health_path: Path = Path(
        "/tmp/wef-telegram-worker.health.json",  # noqa: S108
    )
    telegram_reconciliation_interval_seconds: float = Field(default=60.0, ge=10, le=3600)
    telegram_reconciliation_batch_size: int = Field(default=100, ge=1, le=100)
    telegram_reconciliation_max_messages: int = Field(default=500, ge=1, le=500)
    telegram_reconciliation_overlap: int = Field(default=20, ge=0, le=100)
    telegram_media_temp_path: Path = Path("/tmp/wef-telegram-media")  # noqa: S108
    telegram_media_download_timeout_seconds: float = Field(default=120.0, ge=1, le=600)
    telegram_media_download_concurrency: int = Field(default=2, ge=1, le=8)
    telegram_recurring_geocode_interval_seconds: float = Field(default=60.0, ge=10, le=3600)
    telegram_recurring_geocode_batch_size: int = Field(default=10, ge=1, le=100)
    ingestion_report_path: Path = Path("/app/media/reports/e2-dry-run")
    geoapify_api_key: SecretStr | None = None
    geoapify_requests_per_second: Decimal = Field(default=Decimal(4), gt=0, le=5)
    geoapify_daily_quota: int = Field(default=2_700, ge=1, le=3_000)
    geoapify_account_identity: str = Field(default="default", min_length=1, max_length=64)
    restricted_originals_path: Path = Path("/app/media/originals")
    public_derivatives_path: Path = Path("/app/media/public")
    media_max_bytes: int = Field(default=52_428_800, ge=1)
    media_max_pixels: int = Field(default=40_000_000, ge=1)
    allow_synthetic_seed: bool = False
    session_ttl_seconds: int = Field(default=43_200, ge=60, le=2_592_000)
    bootstrap_owner_username: str | None = None
    bootstrap_owner_password: str | None = None
    contact_encryption_key: SecretStr | None = None
    contact_hmac_key: SecretStr | None = None
    admin_session_secret: SecretStr | None = None
    release_sha: str | None = None
    ai_curation_enabled: bool = False
    ai_recovery_enabled: bool = False
    ai_recovery_activation_verified: bool = False
    ai_recovery_auto_apply: bool = False
    ai_recovery_owner_id: UUID | Literal[""] | None = None
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_zdr_verified: bool = False
    groq_timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    groq_use_batch_api: bool = True
    groq_batch_chunk_size: int = Field(default=20, ge=1, le=100)
    groq_batch_poll_interval_seconds: float = Field(default=2.0, ge=0.5, le=60)
    groq_batch_max_wait_seconds: float = Field(default=3600.0, ge=30, le=86400)


def load_settings() -> Settings:
    """Load settings explicitly instead of at module import time."""
    _load_dotenv_files()
    return Settings()
