"""Server-side dry-run gates before historical bundle transfer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scripts.transfer.constants import HEADROOM_MULTIPLIER, MIGRATION_HEAD

if TYPE_CHECKING:
    from pathlib import Path

    from scripts.transfer.transfer_plan import TransferPlan

DATABASE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
MIN_MEMORY_KB = 1_048_576


class ServerDryRunError(ValueError):
    """Raised when server dry-run inputs are invalid."""


@dataclass(frozen=True, slots=True)
class ServerDryRunSummary:
    """Non-sensitive result of one server-side transfer dry run."""

    allowed: bool
    refusal_reasons: tuple[str, ...]
    bundle_bytes: int
    available_disk_bytes: int
    minimum_headroom_bytes: int
    migration_head: str
    candidate_database: str


def load_server_inventory(path: Path) -> dict[str, Any]:
    """Load one bounded server inventory snapshot."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "wef-server-inventory@1":
        msg = "server inventory has an invalid schema"
        raise ServerDryRunError(msg)
    return payload


def evaluate_server_dry_run(
    *,
    plan: TransferPlan,
    inventory: dict[str, Any],
    candidate_database: str,
    existing_databases: tuple[str, ...] = (),
    incoming_exists: bool = False,
) -> ServerDryRunSummary:
    """Evaluate whether one bundle may transfer without server mutation."""
    if not DATABASE_IDENTIFIER.fullmatch(candidate_database):
        msg = "candidate database name must use a safe PostgreSQL identifier"
        raise ServerDryRunError(msg)

    refusal_reasons: list[str] = []
    resources = inventory.get("resources")
    if not isinstance(resources, dict):
        msg = "server inventory is missing resource metrics"
        raise ServerDryRunError(msg)

    disk_free = int(resources.get("disk_free_bytes", 0))
    memory_kb = int(resources.get("memory_available_kb", 0))
    minimum_headroom = int(plan.total_bytes * HEADROOM_MULTIPLIER)

    if plan.migration_head != MIGRATION_HEAD:
        refusal_reasons.append("bundle migration head does not match production head")
    if disk_free < minimum_headroom:
        refusal_reasons.append("insufficient remote disk headroom for bundle transfer")
    if memory_kb < MIN_MEMORY_KB:
        refusal_reasons.append("insufficient remote memory for transfer operations")
    if candidate_database in existing_databases:
        refusal_reasons.append("candidate database name is already in use")
    if incoming_exists:
        refusal_reasons.append("incoming bundle path already exists on server")

    wef_paths = inventory.get("wef_paths")
    if not isinstance(wef_paths, list):
        refusal_reasons.append("server inventory is missing WEF path metadata")
    else:
        path_names = {
            str(entry["path"])
            for entry in wef_paths
            if isinstance(entry, dict) and isinstance(entry.get("path"), str)
        }
        required = (
            str(plan.remote_incoming_dir.parent.parent),
            str(plan.remote_incoming_dir.parent),
        )
        if not all(path in path_names for path in required):
            refusal_reasons.append("required import path roots are missing on server")

    return ServerDryRunSummary(
        allowed=not refusal_reasons,
        refusal_reasons=tuple(sorted(refusal_reasons)),
        bundle_bytes=plan.total_bytes,
        available_disk_bytes=disk_free,
        minimum_headroom_bytes=minimum_headroom,
        migration_head=plan.migration_head,
        candidate_database=candidate_database,
    )
