"""Explicit synthetic M1 seed command."""

import asyncio
import json
import sys
from dataclasses import asdict

from wef_backend.database import create_database_resources
from wef_backend.features.catalog.application import ProductionSeedError, SeedM1Catalog
from wef_backend.features.catalog.application.m1_fixture import m1_fixture
from wef_backend.features.catalog.infrastructure import SQLAlchemyCatalogSeedAdapter
from wef_backend.settings import load_settings


async def seed() -> None:
    """Converge the invented M1 fixture and emit reconciliation counts."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        service = SeedM1Catalog(
            SQLAlchemyCatalogSeedAdapter(database.session_factory),
            environment=settings.env,
            allow_production=settings.allow_synthetic_seed,
        )
        result = await service(*m1_fixture())
        sys.stdout.write(json.dumps(asdict(result), sort_keys=True) + "\n")
    finally:
        await database.engine.dispose()


def main() -> None:
    """Run the async seed from a synchronous console entry point."""
    try:
        asyncio.run(seed())
    except ProductionSeedError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(2) from None
