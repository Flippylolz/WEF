"""Private aggregate location validation status and one-time rollout controls."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from wef_backend.database import create_database_resources
from wef_backend.features.ingestion.application.location_revalidation import VALIDATION_TARGET
from wef_backend.features.ingestion.infrastructure.location_validation_store import (
    SQLAlchemyLocationValidationStore,
)
from wef_backend.settings import load_settings


async def run(
    action: str, *, canary_ids: tuple[UUID, ...] = (), discovery_ready: bool = False
) -> dict[str, object]:
    """Return private aggregates; changing mode never performs provider calls inline."""
    settings = load_settings()
    database = create_database_resources(settings.database_url)
    try:
        store = SQLAlchemyLocationValidationStore(database.session_factory)
        if action == "rollback":
            await store.rollback(target=VALIDATION_TARGET)
        elif action == "verify-canary":
            await store.verify_canary(target=VALIDATION_TARGET)
        elif action != "status":
            await store.control(
                target=VALIDATION_TARGET,
                mode=action,
                canary_ids=canary_ids,
                discovery_ready=discovery_ready,
            )
        return await store.status(target=VALIDATION_TARGET)
    finally:
        await database.engine.dispose()


def main() -> None:
    """Require explicit discovery readiness and observed canaries before apply mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("status", "off", "observe", "apply", "verify-canary", "rollback"),
        nargs="?",
        default="status",
    )
    parser.add_argument(
        "--canary-id",
        action="append",
        type=UUID,
        default=[],
        help="Prioritize 1-25 observation cases; restrict initial apply to observed cases",
    )
    parser.add_argument("--discovery-ready", action="store_true")
    args = parser.parse_args()
    sys.stdout.write(
        json.dumps(
            asyncio.run(
                run(
                    args.action,
                    canary_ids=tuple(args.canary_id),
                    discovery_ready=args.discovery_ready,
                )
            )
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
