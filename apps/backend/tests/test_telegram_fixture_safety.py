"""Safety checks for the committed Telegram export fixture corpus."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures/telegram_export"
TRUNCATED_FIXTURE = "synthetic-truncated.json"
ALLOWED_FIXTURE_FILES = {
    "sanitized-complete.golden.json",
    "sanitized-complete.json",
    "synthetic-malformed-record.json",
    TRUNCATED_FIXTURE,
}
SAFE_CHANNEL_ID = 9001
SAFE_CHANNEL_NAME = "Sanitized Fixture Channel"
SAFE_MESSAGE_IDS = set(range(101, 109))
SAFE_PUBLISHER = "Sanitized Publisher"
CONTACT_PATTERNS = (
    re.compile(r"@[A-Za-z0-9_]{3,}"),
    re.compile(r"(?:t|telegram)\.me/", re.IGNORECASE),
    re.compile(r"\b(?:tel|phone|whatsapp)\s*:", re.IGNORECASE),
    re.compile(r"(?<!\w)\+[\d ()-]{7,}\d"),
    re.compile(r"\b\d{3}[ .]\d{3}[ .]\d{3}\b"),
)
SOURCE_IDENTITY_PATTERNS = tuple(
    re.compile(re.escape(value), re.IGNORECASE)
    for value in (
        "2180077318",
        "El Estate | Покупка Варшава",
        "elestate_warszawa",
    )
)
FORBIDDEN_TEXT = ("warszawa", "варшава", "real source", "private channel")
MEDIA_KEYS = {"file", "photo", "thumbnail"}
SAFE_MEDIA_ROOTS = {"photos", "video_files"}


def _walk(value: object) -> Iterator[tuple[str | None, object]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield None, item
            yield from _walk(item)


def test_fixture_directory_contains_only_reviewed_text_json() -> None:
    """No unreviewed archive, media byte, session, or generated file is committed."""
    files = {path.name for path in FIXTURE_ROOT.iterdir() if path.is_file()}
    assert files == ALLOWED_FIXTURE_FILES
    assert all(path.suffix == ".json" for path in FIXTURE_ROOT.iterdir())

    for path in FIXTURE_ROOT.iterdir():
        if not path.is_file():
            continue
        payload = path.read_bytes()
        assert b"\x00" not in payload
        payload.decode("utf-8")


@pytest.mark.parametrize("path", tuple(FIXTURE_ROOT.glob("*.json")))
def test_fixture_bytes_reject_contact_and_source_identity_patterns(path: Path) -> None:
    """Broad leak indicators stay absent from fixtures and goldens."""
    text = path.read_text(encoding="utf-8")
    for pattern in CONTACT_PATTERNS + SOURCE_IDENTITY_PATTERNS:
        assert pattern.search(text) is None
    lowered = text.casefold()
    assert all(forbidden not in lowered for forbidden in FORBIDDEN_TEXT)


@pytest.mark.parametrize(
    "path",
    tuple(path for path in FIXTURE_ROOT.glob("*.json") if path.name != TRUNCATED_FIXTURE),
)
def test_fixture_json_has_only_rebased_identity_and_safe_media_paths(path: Path) -> None:
    """Identifiers and media references use the reviewed fixture namespace."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if "messages" in document:
        assert document["id"] == SAFE_CHANNEL_ID
        assert document["name"] == SAFE_CHANNEL_NAME

    for key, value in _walk(document):
        if key in {"id", "external_message_id", "reply_to_message_id"} and value is not None:
            assert value in SAFE_MESSAGE_IDS | {SAFE_CHANNEL_ID}
        if key == "channel_id":
            assert value == str(SAFE_CHANNEL_ID)
        if key in {"from", "actor"}:
            assert value == SAFE_PUBLISHER
        if key in {"channel_name", "name"}:
            assert value == SAFE_CHANNEL_NAME
        assert key not in {"from_id", "actor_id", "username"}
        if key in MEDIA_KEYS and isinstance(value, str) and value:
            posix = PurePosixPath(value)
            windows = PureWindowsPath(value)
            assert not posix.is_absolute()
            assert not windows.is_absolute()
            assert ".." not in posix.parts
            assert posix.parts[0] in SAFE_MEDIA_ROOTS
            assert posix.name.startswith("sample_")
