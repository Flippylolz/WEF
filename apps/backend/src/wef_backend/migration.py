"""Alembic command entry point with runtime-provided database configuration."""

from alembic import command as alembic_command
from alembic.config import Config

from wef_backend.settings import Settings, load_settings

EXPECTED_DATABASE_REVISION = "20260906_0026"
# E28-T4 adds only a defaulted discovery receipt to offer_sources. This reader
# is the verified rollback target for that additive migration.
READ_COMPATIBLE_DATABASE_REVISIONS = frozenset({EXPECTED_DATABASE_REVISION, "20260908_0027"})

__all__ = [
    "EXPECTED_DATABASE_REVISION",
    "READ_COMPATIBLE_DATABASE_REVISIONS",
    "alembic_command",
    "alembic_config",
    "migrate",
]


def alembic_config(settings: Settings) -> Config:
    """Build Alembic configuration without persisting a database URL."""
    config = Config(str(settings.alembic_config))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def migrate() -> None:
    """Upgrade the configured database to the expected head revision."""
    alembic_command.upgrade(alembic_config(load_settings()), "head")
