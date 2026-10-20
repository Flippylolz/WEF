"""Alembic command entry point with runtime-provided database configuration."""

from alembic import command as alembic_command
from alembic.config import Config
from alembic.script import ScriptDirectory

from wef_backend.settings import Settings, load_settings

__all__ = [
    "alembic_command",
    "alembic_config",
    "expected_database_revision",
    "migrate",
]


def alembic_config(settings: Settings) -> Config:
    """Build Alembic configuration without persisting a database URL."""
    config = Config(str(settings.alembic_config))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def expected_database_revision(settings: Settings | None = None) -> str:
    """Read the single head from the release's configured migration history."""
    runtime_settings = settings or load_settings()
    scripts = ScriptDirectory.from_config(Config(str(runtime_settings.alembic_config)))
    head = scripts.get_current_head()
    if head is None:
        message = "Alembic migration history has no head"
        raise RuntimeError(message)
    return head


def migrate() -> None:
    """Upgrade the configured database to the expected head revision."""
    alembic_command.upgrade(alembic_config(load_settings()), "head")
