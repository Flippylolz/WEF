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
MINIMUM = 100
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
        if metric == "branches" and covered == total == 0:
            # The required lines metric still rejects an empty/non-executable file.
            return MAXIMUM
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
            if not MINIMUM <= floor <= MAXIMUM:
                message = "critical floors must require 100%"
                raise ValueError(message)
            measured = _measure(row, metric=metric, backend=backend)
            if measured < floor:
                errors.append(f"{suffix}: {metric} {measured:.2f}% < {floor}%")
    if not policy:
        message = "critical coverage policy cannot be empty"
        raise ValueError(message)
    return errors


def _shell_count(value: object) -> int:
    """Kcov emits file counters as decimal strings and aggregate counters as integers."""
    if isinstance(value, str):
        if not value.isascii() or not value.isdecimal():
            message = "shell coverage counters must be unsigned decimal integers"
            raise ValueError(message)
        value = int(value)
    return _count(value)


def check_shell(report: Mapping[str, object], policy: Mapping[str, object]) -> list[str]:
    """Require every runtime shell file at 100% without inventing branch counters."""
    raw_files = report["files"]
    if not isinstance(raw_files, list):
        message = "shell coverage files must be a list"
        raise TypeError(message)
    rows: list[tuple[str, int, int]] = []
    for raw in raw_files:
        row = _object(raw)
        path = row["file"]
        if not isinstance(path, str) or not path:
            message = "shell coverage file paths must be nonempty strings"
            raise ValueError(message)
        covered, total = _shell_count(row["covered_lines"]), _shell_count(row["total_lines"])
        _percentage(covered, total)
        rows.append((path, covered, total))
    if not policy:
        message = "shell coverage policy cannot be empty"
        raise ValueError(message)
    errors: list[str] = []
    for suffix, raw_floors in policy.items():
        floors = _object(raw_floors)
        if set(floors) != {"lines"} or _count(floors["lines"]) != MAXIMUM:
            message = "shell policy must require exactly 100% lines"
            raise ValueError(message)
        matches = [
            (covered, total)
            for path, covered, total in rows
            if path == suffix or path.endswith("/" + suffix)
        ]
        if len(matches) != 1:
            errors.append(f"{suffix}: expected exactly one measured shell file")
        elif matches[0][0] != matches[0][1]:
            errors.append(f"{suffix}: lines {_percentage(*matches[0]):.2f}% < 100%")
    errors.extend(
        f"{path}: unexpected measured shell file"
        for path, _, _ in rows
        if not any(path == suffix or path.endswith("/" + suffix) for suffix in policy)
    )
    if _count(report["covered_lines"]) != sum(row[1] for row in rows) or _count(
        report["total_lines"]
    ) != sum(row[2] for row in rows):
        message = "shell aggregate counters disagree with measured files"
        raise ValueError(message)
    return errors


def main() -> int:
    """Allow independent suites while requiring the selected side's complete policy."""
    parser = argparse.ArgumentParser(description=__doc__)
    side = parser.add_mutually_exclusive_group(required=True)
    side.add_argument("--backend", type=Path)
    side.add_argument("--frontend", type=Path)
    side.add_argument("--operations", type=Path)
    side.add_argument("--shell", type=Path)
    args = parser.parse_args()
    backend = args.frontend is None
    report_path = args.backend or args.frontend or args.operations or args.shell
    policy_name = (
        "backend"
        if args.backend
        else "frontend"
        if args.frontend
        else "operations"
        if args.operations
        else "shell"
    )
    try:
        policy = _object(json.loads((ROOT / ".github/critical-coverage.json").read_text()))
        report = _object(json.loads(report_path.read_text()))
        floors = _object(policy[policy_name])
        errors = (
            check_shell(report, floors) if args.shell else check(report, floors, backend=backend)
        )
    except (KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"Invalid critical coverage evidence: {error}\n")
        return 1
    for failure in errors:
        sys.stderr.write(failure + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
