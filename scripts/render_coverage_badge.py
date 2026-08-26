"""Render one branch-aware coverage badge from backend and web reports."""

# ruff: noqa: T201

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

GREEN_THRESHOLD = 90
YELLOW_THRESHOLD = 80
COVERAGE_FLOOR = float(GREEN_THRESHOLD)


class CoverageDataError(ValueError):
    """Raised when a coverage report does not contain valid counters."""


@dataclass(frozen=True)
class CoverageCounts:
    """Covered and total executable lines plus branch paths."""

    covered: int
    total: int

    def __post_init__(self) -> None:
        """Reject impossible coverage totals."""
        if self.covered < 0 or self.total <= 0 or self.covered > self.total:
            msg = f"invalid coverage counts: {self.covered}/{self.total}"
            raise CoverageDataError(msg)

    def __add__(self, other: CoverageCounts) -> CoverageCounts:
        """Combine coverage from independently tested applications."""
        return CoverageCounts(self.covered + other.covered, self.total + other.total)

    @property
    def percentage(self) -> float:
        """Return the coverage percentage represented by these counts."""
        return self.covered / self.total * 100


def _load_object(path: Path) -> dict[str, object]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"{path} must contain a JSON object"
        raise CoverageDataError(msg)
    return {str(key): value for key, value in raw.items()}


def _object(data: Mapping[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        msg = f"coverage report field {key!r} must be an object"
        raise CoverageDataError(msg)
    return {str(child_key): child for child_key, child in value.items()}


def _count(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"coverage report field {key!r} must be an integer"
        raise CoverageDataError(msg)
    return value


def backend_counts(path: Path) -> CoverageCounts:
    """Read line and branch counts from Coverage.py JSON output."""
    totals = _object(_load_object(path), "totals")
    covered = _count(totals, "covered_lines") + _count(totals, "covered_branches")
    total = _count(totals, "num_statements") + _count(totals, "num_branches")
    return CoverageCounts(covered, total)


def frontend_counts(path: Path) -> CoverageCounts:
    """Read line and branch counts from a Vitest JSON summary."""
    total_summary = _object(_load_object(path), "total")
    lines = _object(total_summary, "lines")
    branches = _object(total_summary, "branches")
    covered = _count(lines, "covered") + _count(branches, "covered")
    total = _count(lines, "total") + _count(branches, "total")
    return CoverageCounts(covered, total)


def coverage_shortfalls(
    suites: Mapping[str, CoverageCounts],
    floor: float,
) -> tuple[str, ...]:
    """Return named totals whose coverage is below the required floor."""
    return tuple(
        f"{name} {counts.percentage:.1f}%"
        for name, counts in suites.items()
        if counts.percentage < floor
    )


def badge_color(percentage: float) -> str:
    """Use familiar coverage colors without depending on a badge service."""
    if percentage >= GREEN_THRESHOLD:
        return "#4c1"
    if percentage >= YELLOW_THRESHOLD:
        return "#dfb317"
    return "#e05d44"


def render_badge(percentage: float) -> str:
    """Return an accessible, deterministic SVG coverage badge."""
    display = f"{percentage:.1f}%"
    color = badge_color(percentage)
    title = f"Repository branch-aware coverage: {display}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="128" height="20"
  role="img" aria-label="{title}">
  <title>{title}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="128" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="76" height="20" fill="#555"/>
    <rect x="76" width="52" height="20" fill="{color}"/>
    <rect width="128" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle"
    font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="38" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="38" y="14">coverage</text>
    <text x="102" y="15" fill="#010101" fill-opacity=".3">{display}</text>
    <text x="102" y="14">{display}</text>
  </g>
</svg>
"""


def parse_args() -> argparse.Namespace:
    """Parse report paths, output path, and the coverage floor."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, type=Path)
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--fail-under",
        type=float,
        default=COVERAGE_FLOOR,
        help="fail if backend or frontend coverage is below this percentage",
    )
    return parser.parse_args()


def main() -> int:
    """Combine both reports, write the badge, and enforce the coverage floor."""
    args = parse_args()
    backend = backend_counts(args.backend)
    frontend = frontend_counts(args.frontend)
    combined = backend + frontend
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_badge(combined.percentage), encoding="utf-8")
    print(f"Backend branch-aware coverage: {backend.percentage:.1f}%")
    print(f"Frontend branch-aware coverage: {frontend.percentage:.1f}%")
    print(f"Repository branch-aware coverage: {combined.percentage:.1f}%")
    shortfalls = coverage_shortfalls(
        {"backend": backend, "frontend": frontend},
        args.fail_under,
    )
    if shortfalls:
        joined = ", ".join(shortfalls)
        print(
            f"Coverage is below the {args.fail_under:.0f}% floor: {joined}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
