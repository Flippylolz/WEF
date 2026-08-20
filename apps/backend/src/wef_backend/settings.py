"""Runtime settings loaded only by the composition root."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="WEF_",
        extra="ignore",
        frozen=True,
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


def load_settings() -> Settings:
    """Load settings explicitly instead of at module import time."""
    return Settings()
