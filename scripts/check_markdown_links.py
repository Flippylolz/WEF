"""Validate that repository-relative Markdown link targets exist."""

# ruff: noqa: T201

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

LINK_PATTERN = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def tracked_markdown_files() -> tuple[Path, ...]:
    """Return tracked Markdown files in deterministic order."""
    if GIT is None:
        msg = "git is required to enumerate tracked Markdown files"
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - executable resolved from trusted PATH
        [GIT, "ls-files", "--", "*.md"],
        check=True,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    return tuple(REPOSITORY_ROOT / line for line in result.stdout.splitlines() if line)


def target_path(source: Path, raw_target: str) -> Path | None:
    """Resolve a local Markdown target, excluding URLs and anchor-only links."""
    target = raw_target.strip().strip("<>")
    if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
        return None

    path_part = unquote(target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0])
    if not path_part:
        return None

    candidate = Path(path_part)
    if candidate.is_absolute():
        return REPOSITORY_ROOT / path_part.lstrip("/")
    return source.parent / candidate


def main() -> int:
    """Print missing local targets and return a non-zero status when found."""
    missing: list[str] = []
    for source in tracked_markdown_files():
        text = source.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            raw_target = match.group(1)
            resolved = target_path(source, raw_target)
            if resolved is not None and not resolved.exists():
                relative_source = source.relative_to(REPOSITORY_ROOT)
                missing.append(f"{relative_source}: {raw_target}")

    if missing:
        print("Missing relative Markdown targets:")
        print("\n".join(f"- {item}" for item in missing))
        return 1

    print("All tracked relative Markdown link targets exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
