"""Admin HTTP tests for ingestion parse issue reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tests.fakes import FakeParseIssueStore
from tests.test_admin_api import _owner_session, admin_client
from wef_backend.features.ingestion.application.persistence import MessageOutcome
from wef_backend.features.ingestion.domain.parse_issue import (
    ParseIssueOutcome,
    SourceMessageParseIssue,
)


@pytest.mark.asyncio
async def test_ingestion_issues_export_is_redacted() -> None:
    """CSV export includes score metadata but no raw phone numbers."""
    store = FakeParseIssueStore()
    store.issues.append(
        SourceMessageParseIssue(
            id=uuid4(),
            source_channel_id=uuid4(),
            source_message_id=uuid4(),
            source_message_revision_id=uuid4(),
            external_message_id=29435,
            ingest_run_id=uuid4(),
            parser_version="e2-v5",
            score=3,
            threshold=5,
            is_candidate=False,
            signals_json=(
                {
                    "reason": "price_marker",
                    "weight": 3,
                    "source_start": 0,
                    "source_end": 4,
                },
            ),
            warnings_json=(),
            issue_outcome=ParseIssueOutcome.PARSER_MISS,
            message_outcome=MessageOutcome.SKIPPED_NON_CANDIDATE.value,
            boundary_band="non_candidate_one_below_threshold",
            signal_combination="price_marker",
            text_excerpt_redacted="Warsaw listing without enough markers",
            offer_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    async with admin_client(parse_issue_store=store) as (client, _identity):
        await _owner_session(client, _identity)
        home = await client.get("/admin/ingestion-issues")
        assert home.status_code == 200
        assert "29435" in home.text
        assert "parser_miss" in home.text
        csv_response = await client.get("/admin/ingestion-issues/export.csv")
        assert csv_response.status_code == 200
        body = csv_response.text
        assert "29435" in body
        assert "non_candidate_one_below_threshold" in body
        assert "+48" not in body
        json_response = await client.get("/admin/ingestion-issues/export.json")
        assert json_response.status_code == 200
        assert "Warsaw listing" in json_response.text
