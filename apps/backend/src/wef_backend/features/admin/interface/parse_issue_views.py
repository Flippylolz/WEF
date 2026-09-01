"""Owner HTML and export routes for ingestion parse issues."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import io
import json
from html import escape
from typing import TYPE_CHECKING, cast

from starlette.responses import HTMLResponse, Response
from starlette_admin import CustomView
from starlette_admin.routing import route

if TYPE_CHECKING:
    from uuid import UUID

    from starlette.requests import Request

    from wef_backend.features.admin.application.admin_ops import AdminService


def _admin(request: Request) -> AdminService:
    return cast("AdminService", request.state.admin)


def _owner_id(request: Request) -> UUID:
    return cast("UUID", request.state.admin_owner_id)


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title>"
        "<link rel='stylesheet' href='/admin/static/css/admin.css?v=1'>"
        f"</head><body class='wef-page ingestion-issues-page'>"
        f"<h1>{escape(title)}</h1>"
        f"{body}"
        "</body></html>",
    )


class IngestionIssuesAdminView(CustomView):
    """Review parser misses and incomplete parses for future parser work."""

    def __init__(self) -> None:
        """Register the ingestion issues admin menu entry."""
        super().__init__(
            menu_label="Ingestion issues",
            icon="fa fa-triangle-exclamation",
            path="/ingestion-issues",
        )

    @route("", methods=["GET"], name="ingestion_issues_home")
    async def index(self, request: Request) -> Response:
        """Render the parse issue table."""
        events = await _admin(request).list_parse_issue_events(owner_id=_owner_id(request))
        rows = "".join(
            "<tr>"
            f"<td>{event.external_message_id}</td>"
            f"<td>{escape(event.issue_outcome.value)}</td>"
            f"<td>{event.score}/{event.threshold}</td>"
            f"<td>{escape(event.boundary_band)}</td>"
            f"<td>{escape(event.signal_combination)}</td>"
            f"<td>{escape(event.parser_version)}</td>"
            f"<td>{escape(event.text_excerpt_redacted[:120])}</td>"
            "</tr>"
            for event in events
        )
        body = (
            "<p><a href='/admin/ingestion-issues/export.json'>Export JSON</a> · "
            "<a href='/admin/ingestion-issues/export.csv'>Export CSV</a></p>"
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Message</th><th>Issue</th><th>Score</th><th>Boundary</th>"
            "<th>Signals</th><th>Parser</th><th>Excerpt</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=7>No parse issues yet</td></tr>'}</tbody></table></div>"
        )
        return _page("Ingestion parse issues", body)

    @route("/export.json", methods=["GET"], name="ingestion_issues_json")
    async def export_json(self, request: Request) -> Response:
        """Download parse issues as JSON."""
        events = await _admin(request).list_parse_issue_events(owner_id=_owner_id(request))
        payload = [
            {
                "external_message_id": event.external_message_id,
                "source_message_revision_id": str(event.source_message_revision_id),
                "parser_version": event.parser_version,
                "score": event.score,
                "threshold": event.threshold,
                "is_candidate": event.is_candidate,
                "boundary_band": event.boundary_band,
                "signal_combination": event.signal_combination,
                "signals": list(event.signals_json),
                "warnings": list(event.warnings_json),
                "issue_outcome": event.issue_outcome.value,
                "message_outcome": event.message_outcome,
                "offer_id": str(event.offer_id) if event.offer_id is not None else None,
                "text_excerpt_redacted": event.text_excerpt_redacted,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
        return Response(
            json.dumps(payload, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="ingestion-issues.json"'},
        )

    @route("/export.csv", methods=["GET"], name="ingestion_issues_csv")
    async def export_csv(self, request: Request) -> Response:
        """Download parse issues as CSV."""
        events = await _admin(request).list_parse_issue_events(owner_id=_owner_id(request))
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "external_message_id",
                "source_message_revision_id",
                "parser_version",
                "score",
                "threshold",
                "is_candidate",
                "boundary_band",
                "signal_combination",
                "signals_json",
                "warnings_json",
                "issue_outcome",
                "message_outcome",
                "offer_id",
                "text_excerpt_redacted",
                "created_at",
            ],
        )
        for event in events:
            writer.writerow(
                [
                    event.external_message_id,
                    str(event.source_message_revision_id),
                    event.parser_version,
                    event.score,
                    event.threshold,
                    event.is_candidate,
                    event.boundary_band,
                    event.signal_combination,
                    json.dumps(list(event.signals_json), ensure_ascii=False),
                    json.dumps(list(event.warnings_json), ensure_ascii=False),
                    event.issue_outcome.value,
                    event.message_outcome,
                    str(event.offer_id) if event.offer_id is not None else "",
                    event.text_excerpt_redacted,
                    event.created_at.isoformat(),
                ],
            )
        return Response(
            buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="ingestion-issues.csv"'},
        )
