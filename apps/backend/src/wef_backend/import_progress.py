"""Bounded source-free terminal presentation for historical imports."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from io import TextIOBase
_NONINTERACTIVE_PROGRESS_STEP = 500


class TerminalProgress:
    """Small dependency-free progress bar that never logs source values."""

    def __init__(
        self,
        label: str,
        total: int | None,
        *,
        output: TextIOBase | None = None,
    ) -> None:
        """Initialize one bounded terminal renderer."""
        self.label = label
        self.total = total
        self.output = output or sys.stderr
        self.current = 0
        self._last_rendered = -1
        self._interactive = bool(getattr(self.output, "isatty", lambda: False)())

    def update(self, current: int) -> None:
        """Render monotonic progress without emitting one line per record."""
        self.current = max(self.current, current)
        if (
            self._interactive
            or self.current == 1
            or self.current - self._last_rendered >= _NONINTERACTIVE_PROGRESS_STEP
        ):
            self._render(final=False)

    def finish(self, *, complete: bool = True) -> None:
        """Render one final line, optionally without claiming completion."""
        if complete and self.total is not None:
            self.current = max(self.current, self.total)
        self._render(final=True)

    def _render(self, *, final: bool) -> None:
        width = 28
        if self.total is None or self.total <= 0:
            bar = "=" * min(width, (self.current // 100) % (width + 1))
            rendered = f"{self.label:12} [{bar:<{width}}] {self.current:,}"
        else:
            ratio = min(1.0, self.current / self.total)
            filled = round(width * ratio)
            bar = "#" * filled + "-" * (width - filled)
            rendered = f"{self.label:12} [{bar}] {ratio:6.1%} {self.current:,}/{self.total:,}"
        end = "\n" if final or not self._interactive else "\r"
        self.output.write(rendered + end)
        self.output.flush()
        self._last_rendered = self.current
