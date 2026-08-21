"""Operator CLI: publish historical offers and hide synthetic M1 seed."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application.promote_public_catalog import (
    PromotePublicCatalog,
)
from wef_backend.features.catalog.infrastructure.promote_public_catalog_adapter import (
    SQLAlchemyPromotePublicCatalogAdapter,
)
from wef_backend.settings import load_settings


async def run() -> dict[str, int]:
    """Promote reviewed historical offers and retire synthetic seed from public views."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        result = await PromotePublicCatalog(
            SQLAlchemyPromotePublicCatalogAdapter(database.session_factory),
        )()
        return asdict(result)
    finally:
        await database.engine.dispose()


def main() -> None:
    """Print promotion counts as JSON."""
    try:
        payload = asyncio.run(run())
    except Exception:  # noqa: BLE001
        sys.stderr.write("Public catalog promotion failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
