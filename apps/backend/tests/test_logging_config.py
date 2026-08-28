"""Tests for structured logging scrubbing helpers."""

import logging

import pytest

from wef_backend.logging_config import (
    configure_logging,
    configure_safe_telethon_logging,
    scrub_event_dict,
    scrub_log_value,
)


def test_scrub_log_value_masks_secret_substrings() -> None:
    scrubbed = scrub_log_value("password=super-secret token:abc Authorization: Bearer xyz")
    assert isinstance(scrubbed, str)
    assert "super-secret" not in scrubbed
    assert "abc" not in scrubbed
    assert "xyz" not in scrubbed
    assert "password=***" in scrubbed


def test_scrub_event_dict_preserves_safe_fields() -> None:
    event = scrub_event_dict(
        None,
        "info",
        {
            "event": "http_request",
            "path": "/api/v1/health/live",
            "status_code": 200,
            "detail": "cookie=session-value",
        },
    )
    assert event["path"] == "/api/v1/health/live"
    assert event["status_code"] == 200
    assert "session-value" not in event["detail"]


def test_safe_telethon_bridge_never_renders_message_or_exception(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(json_logs=True)
    configure_safe_telethon_logging()
    logging.getLogger("telethon.events").warning(
        "password=super-secret source listing text",
        exc_info=RuntimeError("session=private"),
    )
    output = capsys.readouterr().out
    assert "telethon_runtime_diagnostic" in output
    assert "super-secret" not in output
    assert "source listing" not in output
    assert "session=private" not in output
