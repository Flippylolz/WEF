"""Runtime settings loaded only by the composition root."""

from pathlib import Path
from typing import Literal

from pydantic import Field
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
    allow_synthetic_seed: bool = False


def load_settings() -> Settings:
    """Load settings explicitly instead of at module import time."""
    return Settings()
