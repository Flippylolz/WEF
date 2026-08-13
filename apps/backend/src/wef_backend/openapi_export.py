"""Deterministic offline OpenAPI export."""

import json
from pathlib import Path

from wef_backend.app import create_http_app

DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parents[4] / "contracts/openapi/v1.json"


def export_openapi(destination: Path = DEFAULT_CONTRACT_PATH) -> Path:
    """Write a stable, synthetic OpenAPI document and return its path."""
    schema = create_http_app().openapi()
    serialized = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized, encoding="utf-8")
    return destination


def main() -> None:
    """Export the repository's committed synthetic API contract."""
    export_openapi()
