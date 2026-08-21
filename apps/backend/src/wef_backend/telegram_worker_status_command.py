"""Operator CLI: redacted Telegram worker status and rotation dry-run."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
    rotation_rehearsal_report,
)
from wef_backend.features.ingestion.domain.telegram_channel import TelegramWorkerSecretPaths
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.settings import load_settings

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.telegram_worker_ops import TelegramWorkerStatus


def _secret_paths() -> TelegramWorkerSecretPaths:
    settings = load_settings()
    return TelegramWorkerSecretPaths(
        api_id_file=settings.telegram_api_id_file,
        api_hash_file=settings.telegram_api_hash_file,
        session_file=settings.telegram_session_file,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the worker-status CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Redacted Telegram worker ops status, checkpoint reconciliation, "
            "and session-rotation dry-run checklist."
        ),
    )
    parser.add_argument(
        "--rotation-dry-run",
        action="store_true",
        help="Print the session rotation rehearsal checklist only",
    )
    parser.add_argument(
        "--owner-gate-open",
        action="store_true",
        help="Mark the production activation owner gate as open (status only)",
    )
    return parser


def _serialize_status(status: TelegramWorkerStatus) -> dict[str, object]:
    payload = asdict(status)
    finished = status.last_live_run_finished_at
    if finished is not None:
        payload["last_live_run_finished_at"] = (
            finished.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )
    payload["secret_files"] = [asdict(item) for item in status.secret_files]
    payload["reconciliation"] = asdict(status.reconciliation)
    payload["freshness"] = status.freshness.value
    payload["reconciliation"]["status"] = status.reconciliation.status.value
    return payload


async def run_status(*, owner_gate_open: bool) -> dict[str, object]:
    """Load DB + secret path evidence into a redacted status report."""
    settings = load_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SQLAlchemyTelegramWorkerStatusStore(session_factory)
    try:
        status = await build_telegram_worker_status(
            store,
            secret_paths=_secret_paths(),
            options=WorkerStatusOptions(owner_gate_open=owner_gate_open),
        )
        return _serialize_status(status)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print JSON status or rotation dry-run; exit 2 on unexpected failure."""
    args = build_parser().parse_args(argv)
    try:
        if args.rotation_dry_run:
            payload = rotation_rehearsal_report()
        else:
            payload = asyncio.run(run_status(owner_gate_open=args.owner_gate_open))
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram worker status failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    if not args.rotation_dry_run:
        reconciliation = payload.get("reconciliation")
        if isinstance(reconciliation, dict) and reconciliation.get("unexplained"):
            raise SystemExit(3)
