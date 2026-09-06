"""Enforce independent critical-path floors from real branch-aware coverage reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
MINIMUM = 90
MAXIMUM = 100


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        message = "coverage value must be an object"
        raise TypeError(message)
    return cast("dict[str, object]", value)


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        message = "coverage counters must be nonnegative integers"
        raise ValueError(message)
    return value


def _percentage(covered: int, total: int) -> float:
    if total <= 0 or covered > total:
        message = "critical coverage has missing or invalid executable counters"
        raise ValueError(message)
    return covered / total * MAXIMUM


def _measure(row: dict[str, object], *, metric: str, backend: bool) -> float:
    """Calculate executed paths rather than trusting rounded percentage fields."""
    if backend:
        summary = _object(row["summary"])
        covered = _count(summary["covered_lines"]) + _count(summary["covered_branches"])
        total = _count(summary["num_statements"]) + _count(summary["num_branches"])
    else:
        summary = _object(row[metric])
        covered, total = _count(summary["covered"]), _count(summary["total"])
    return _percentage(covered, total)


def check(
    report: Mapping[str, object], policy: Mapping[str, object], *, backend: bool
) -> list[str]:
    """Missing files, ambiguous suffixes and malformed counters always fail closed."""
    files = _object(report["files"]) if backend else report
    errors: list[str] = []
    for suffix, raw_floors in policy.items():
        rows = [
            value for path, value in files.items() if path == suffix or path.endswith("/" + suffix)
        ]
        if len(rows) != 1:
            errors.append(f"{suffix}: expected exactly one measured file")
            continue
        row = _object(rows[0])
        floors = _object(raw_floors)
        if set(floors) != ({"combined"} if backend else {"lines", "branches"}):
            message = "critical policy must include every required metric"
            raise ValueError(message)
        for metric, raw_floor in floors.items():
            floor = _count(raw_floor)
            if not MINIMUM < floor <= MAXIMUM:
                message = "critical floors must exceed the global 90% floor"
                raise ValueError(message)
            measured = _measure(row, metric=metric, backend=backend)
            if measured < floor:
                errors.append(f"{suffix}: {metric} {measured:.2f}% < {floor}%")
    if not policy:
        message = "critical coverage policy cannot be empty"
        raise ValueError(message)
    return errors


def main() -> int:
    """Allow parallel backend/frontend jobs while requiring the selected side's policy."""
    parser = argparse.ArgumentParser(description=__doc__)
    side = parser.add_mutually_exclusive_group(required=True)
    side.add_argument("--backend", type=Path)
    side.add_argument("--frontend", type=Path)
    args = parser.parse_args()
    backend = args.backend is not None
    report_path = args.backend if backend else args.frontend
    try:
        policy = _object(json.loads((ROOT / ".github/critical-coverage.json").read_text()))
        errors = check(
            _object(json.loads(report_path.read_text())),
            _object(policy["backend" if backend else "frontend"]),
            backend=backend,
        )
    except (KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"Invalid critical coverage evidence: {error}\n")
        return 1
    for failure in errors:
        sys.stderr.write(failure + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
