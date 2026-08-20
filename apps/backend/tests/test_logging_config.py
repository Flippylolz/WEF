"""Tests for structured logging scrubbing helpers."""

from wef_backend.logging_config import scrub_event_dict, scrub_log_value


def test_scrub_log_value_masks_secret_substrings() -> None:
    scrubbed = scrub_log_value("password=super-secret token:abc Authorization: Bearer xyz")
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
