"""Operator CLI: accept in-scope pending geocode pins for the public map."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.accept_pending_geocode_pins import (
    AcceptPendingGeocodePins,
)
from wef_backend.features.ingestion.infrastructure.accept_pending_geocode_pins_adapter import (
    SQLAlchemyAcceptPendingGeocodePinsAdapter,
)
from wef_backend.settings import load_settings


async def run() -> dict[str, int]:
    """Accept pending pins and return JSON-serializable counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        result = await AcceptPendingGeocodePins(
            SQLAlchemyAcceptPendingGeocodePinsAdapter(database.session_factory),
        )()
        return asdict(result)
    finally:
        await database.engine.dispose()


def main() -> None:
    """Print acceptance counts as JSON."""
    try:
        payload = asyncio.run(run())
    except Exception:  # noqa: BLE001
        sys.stderr.write("Accept pending geocode pins failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
