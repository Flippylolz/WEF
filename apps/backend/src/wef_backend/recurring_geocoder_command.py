"""Operator CLI: revalidate recurring geocoder decision and optional live proof."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from wef_backend.features.ingestion.application.recurring_geocode import revalidation_report
from wef_backend.features.ingestion.domain.recurring_geocoder import (
    assert_provider_allowed_for_recurring,
    default_recurring_geocoder_decision,
)
from wef_backend.geocoder_check import GeoapifyCheckError, check_geoapify
from wef_backend.settings import load_settings


async def _run(*, live_check: bool) -> dict[str, object]:
    decision = default_recurring_geocoder_decision()
    assert_provider_allowed_for_recurring(decision.retained_provider)
    live: dict[str, object] | None = None
    if live_check:
        live = await check_geoapify(load_settings())
    return revalidation_report(checked_on=decision.checked_on, live_check=live)


def main(argv: list[str] | None = None) -> None:
    """Print a redacted revalidation report; optional one-credit live Geoapify check."""
    parser = argparse.ArgumentParser(
        description="Revalidate recurring geocoder policy (D-002 / E8-T4).",
    )
    parser.add_argument(
        "--live-check",
        action="store_true",
        help="Spend one Geoapify credit to prove key, egress, and attribution mapping.",
    )
    args = parser.parse_args(argv)
    try:
        payload = asyncio.run(_run(live_check=args.live_check))
    except GeoapifyCheckError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        sys.stderr.write("Recurring geocoder revalidation failed\n")
        raise SystemExit(2) from None
    payload["generated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload["checked_on_today"] = datetime.now(UTC).date().isoformat()
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
