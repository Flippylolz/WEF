"""Row conflict classification for candidate restore preflight."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class ConflictClass(StrEnum):
    """Restore preflight outcome for one keyed row."""

    IDENTICAL = "identical"
    NEW = "new"
    CONFLICTING = "conflicting"


@dataclass(frozen=True, slots=True)
class ConflictSummary:
    """Aggregate restore preflight counts."""

    identical: int
    new: int
    conflicting: int

    @property
    def blocks_restore(self) -> bool:
        """Return whether any conflicting row prevents merge."""
        return self.conflicting > 0


def classify_row(
    *,
    key: tuple[str, object],
    existing: Mapping[tuple[str, object], object] | None,
    incoming: object,
) -> ConflictClass:
    """Classify one keyed row against the current production snapshot."""
    if existing is None or key not in existing:
        return ConflictClass.NEW
    if existing[key] == incoming:
        return ConflictClass.IDENTICAL
    return ConflictClass.CONFLICTING


def summarize_conflicts(classes: list[ConflictClass]) -> ConflictSummary:
    """Count identical, new, and conflicting rows."""
    identical = sum(1 for item in classes if item is ConflictClass.IDENTICAL)
    new = sum(1 for item in classes if item is ConflictClass.NEW)
    conflicting = sum(1 for item in classes if item is ConflictClass.CONFLICTING)
    return ConflictSummary(identical=identical, new=new, conflicting=conflicting)
