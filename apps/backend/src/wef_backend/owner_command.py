"""One-time owner bootstrap command fed from operator secrets."""

import asyncio
import json
import sys

from wef_backend.database import create_database_resources
from wef_backend.features.identity.application import (
    BootstrapOwner,
    BootstrapOwnerError,
)
from wef_backend.features.identity.infrastructure import (
    PwdlibPasswordHasher,
    SQLAlchemyIdentityStore,
)
from wef_backend.settings import load_settings


async def bootstrap() -> None:
    """Create the fixed owner account exactly once and print the result."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        service = BootstrapOwner(
            SQLAlchemyIdentityStore(database.session_factory),
            PwdlibPasswordHasher(),
            username=settings.bootstrap_owner_username,
            password=settings.bootstrap_owner_password,
        )
        account = await service()
        sys.stdout.write(
            json.dumps(
                {
                    "bootstrapped": True,
                    "owner_id": str(account.id),
                    "username": account.username,
                    "must_change_password": account.must_change_password,
                },
                sort_keys=True,
            )
            + "\n",
        )
    finally:
        await database.engine.dispose()


def main() -> None:
    """Run the async bootstrap from a synchronous console entry point."""
    try:
        asyncio.run(bootstrap())
    except BootstrapOwnerError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(2) from None
