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

from wef_backend.features.ingestion.application.telegram_worker_liveness import (
    worker_liveness_ok,
)
from wef_backend.features.ingestion.application.telegram_worker_status import (
    WorkerStatusOptions,
    build_telegram_worker_status,
    rotation_rehearsal_report,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    credentials_present,
    unwrap_secret,
)
from wef_backend.features.ingestion.infrastructure.telegram_worker_status_store import (
    SQLAlchemyTelegramWorkerStatusStore,
)
from wef_backend.settings import load_settings
from wef_backend.telegram_credentials import secret_text

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.telegram_worker_ops import TelegramWorkerStatus


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
        "--liveness",
        action="store_true",
        help="Exit 0 only when the listen-loop heartbeat is fresh (Compose healthcheck)",
    )
    return parser


def _serialize_status(status: TelegramWorkerStatus) -> dict[str, object]:
    payload = asdict(status)
    finished = status.last_live_run_finished_at
    if finished is not None:
        payload["last_live_run_finished_at"] = (
            finished.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )
    payload["reconciliation"] = asdict(status.reconciliation)
    payload["freshness"] = status.freshness.value
    payload["reconciliation"]["status"] = status.reconciliation.status.value
    return payload


async def run_status() -> dict[str, object]:
    """Load DB + env credential presence into a redacted status report."""
    settings = load_settings()
    api_hash = secret_text(settings.telegram_api_hash)
    session = secret_text(settings.telegram_session)
    if not session and settings.telegram_session_path is not None:
        path = settings.telegram_session_path
        session = unwrap_secret(path.read_text(encoding="utf-8")) if path.is_file() else None
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SQLAlchemyTelegramWorkerStatusStore(session_factory)
    try:
        status = await build_telegram_worker_status(
            store,
            options=WorkerStatusOptions(
                credentials_ready=credentials_present(
                    api_id=settings.telegram_api_id,
                    api_hash=api_hash,
                ),
                session_ready=bool(session),
            ),
        )
        return _serialize_status(status)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    """Print JSON status or rotation dry-run; exit 2 on unexpected failure."""
    args = build_parser().parse_args(argv)
    if args.liveness:
        settings = load_settings()
        if worker_liveness_ok(settings.telegram_heartbeat_path):
            return
        sys.stderr.write("Telegram worker liveness failed\n")
        raise SystemExit(1)
    try:
        if args.rotation_dry_run:
            payload = rotation_rehearsal_report()
        else:
            payload = asyncio.run(run_status())
    except Exception:  # noqa: BLE001
        sys.stderr.write("Telegram worker status failed\n")
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    if not args.rotation_dry_run:
        reconciliation = payload.get("reconciliation")
        if isinstance(reconciliation, dict) and reconciliation.get("unexplained"):
            raise SystemExit(3)
