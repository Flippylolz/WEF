"""Safe relative media path validation for bundle staging."""

from __future__ import annotations

from pathlib import PurePosixPath


class PathValidationError(ValueError):
    """Raised when a media path is unsafe for staging."""


def validate_media_relative_path(path: str) -> str:
    """Accept one normalized relative media path or raise."""
    if not path or path.startswith("/") or "\\" in path:
        msg = "media path must be a non-empty relative POSIX path"
        raise PathValidationError(msg)

    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        msg = "media path must not traverse outside the staging root"
        raise PathValidationError(msg)
    if normalized.name in {".", ".."}:
        msg = "media path must not end in a special segment"
        raise PathValidationError(msg)

    return normalized.as_posix()
