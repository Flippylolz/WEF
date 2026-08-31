"""Public coarse data-origin projection for offer listings."""

from typing import Literal

DataOrigin = Literal["parser", "ai_assisted"]


def derive_data_origin(*, has_active_ai_origin: bool) -> DataOrigin:
    """Return ai_assisted when any active AI field origin exists for the offer."""
    return "ai_assisted" if has_active_ai_origin else "parser"
