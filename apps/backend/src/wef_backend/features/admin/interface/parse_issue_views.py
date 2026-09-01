"""Owner HTML and export routes for ingestion parse issues."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import io
import json
from html import escape
from typing import TYPE_CHECKING, cast
from urllib.parse import urlencode
from uuid import UUID, uuid4

from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette_admin import CustomView
from starlette_admin.routing import route
from starlette_admin.security.csrf import csrf_input

from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import ReviewRunState
from wef_backend.features.admin.application.ingestion_ai_parse import (
    IngestionAiApplyStatus,
    IngestionAiParseStatus,
)

if TYPE_CHECKING:
    from starlette.requests import Request

    from wef_backend.features.admin.application.admin_ops import AdminService
    from wef_backend.features.admin.application.ingestion_ai_parse import IngestionAiParseRun
    from wef_backend.features.ingestion.domain.parse_issue import SourceMessageParseIssue


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


def _review_url(
    *,
    revision_id: UUID | None = None,
    run_id: UUID | None = None,
    error: str | None = None,
) -> str:
    params: dict[str, str] = {}
    if revision_id is not None:
        params["revision_id"] = str(revision_id)
    if run_id is not None:
        params["run_id"] = str(run_id)
    if error:
        params["error"] = error
    query = urlencode(params)
    return f"/admin/ingestion-issues/review?{query}" if query else "/admin/ingestion-issues/review"


def _reason_text(reason: str) -> str:
    return {
        "disabled": "AI curation is disabled",
        "revision_not_found": "Source revision was not found",
        "offer_exists": "This message already has an offer",
        "in_flight": "A review is already in progress",
        "daily_limit": "Daily AI budget reached",
        "masking_failed": "Source masking failed",
    }.get(reason, reason.replace("_", " "))


def _field_rows(run: IngestionAiParseRun) -> str:
    rows = [
        "<tr>"
        f"<td>{escape(str(field.get('field_name', '')))}</td>"
        f"<td><code>{escape(str(field.get('proposed_value', '')))}</code></td>"
        f"<td>{escape(str(field.get('evidence_fragment', '')))}</td>"
        f"<td>{escape(str(field.get('confidence', '')))}</td>"
        "</tr>"
        for field in run.proposed_fields
    ]
    return "".join(rows) or "<tr><td colspan=4>No proposed fields</td></tr>"


def _review_document(
    request: Request,
    *,
    event: SourceMessageParseIssue | None,
    run: IngestionAiParseRun | None,
    error: str | None,
) -> str:
    csrf = csrf_input(request)
    actions = "<p><a href='/admin/ingestion-issues'>Back to issues</a></p>"
    if (
        event is not None
        and run is None
        and event.offer_id is None
        and _admin(request).ai_curation_enabled
    ):
        actions += (
            "<form method='post' action='/admin/ingestion-issues/ai-generate'>"
            f"{csrf}"
            f"<input type='hidden' name='revision_id' value='{event.source_message_revision_id}'>"
            "<button type='submit'>Generate AI listing proposal</button>"
            "</form>"
        )
    if run is not None:
        actions += (
            f"<p>Verdict: <strong>{escape(run.verdict or 'unknown')}</strong> · "
            f"State: {escape(run.state.value)} · "
            f"Expires: {escape(run.expires_at.isoformat())}</p>"
        )
        if (
            run.state is ReviewRunState.PENDING
            and run.verdict == "listing_proposed"
            and _admin(request).ai_curation_enabled
        ):
            actions += (
                "<form method='post' action='/admin/ingestion-issues/ai-apply'>"
                f"{csrf}"
                f"<input type='hidden' name='run_id' value='{run.id}'>"
                "<button type='submit'>Apply listing proposal</button>"
                "</form>"
            )
        if run.offer_id is not None:
            actions += f"<p>Offer created: <code>{escape(str(run.offer_id))}</code></p>"
    summary = ""
    if event is not None:
        summary = (
            "<dl>"
            f"<dt>Message</dt><dd>{event.external_message_id}</dd>"
            f"<dt>Issue</dt><dd>{escape(event.issue_outcome.value)}</dd>"
            f"<dt>Score</dt><dd>{event.score}/{event.threshold}</dd>"
            f"<dt>Boundary</dt><dd>{escape(event.boundary_band)}</dd>"
            f"<dt>Parser</dt><dd>{escape(event.parser_version)}</dd>"
            f"<dt>Excerpt</dt><dd>{escape(event.text_excerpt_redacted[:240])}</dd>"
            "</dl>"
        )
    error_html = f"<p class='error'>{escape(error)}</p>" if error else ""
    table = ""
    if run is not None:
        table = (
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Field</th><th>Value</th><th>Evidence</th><th>Confidence</th>"
            f"</tr></thead><tbody>{_field_rows(run)}</tbody></table></div>"
        )
    return summary + error_html + actions + table


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
        admin = _admin(request)
        events = await admin.list_parse_issue_events(owner_id=_owner_id(request))
        rows = "".join(
            "<tr>"
            f"<td>{event.external_message_id}</td>"
            f"<td>{escape(event.issue_outcome.value)}</td>"
            f"<td>{event.score}/{event.threshold}</td>"
            f"<td>{escape(event.boundary_band)}</td>"
            f"<td>{escape(event.signal_combination)}</td>"
            f"<td>{escape(event.parser_version)}</td>"
            f"<td>{escape(event.text_excerpt_redacted[:120])}</td>"
            + (
                "<td><a href='"
                f"{_review_url(revision_id=event.source_message_revision_id)}'>Review</a></td>"
                if event.offer_id is None and admin.ai_curation_enabled
                else "<td></td>"
            )
            + "</tr>"
            for event in events
        )
        body = (
            "<p><a href='/admin/ingestion-issues/export.json'>Export JSON</a> · "
            "<a href='/admin/ingestion-issues/export.csv'>Export CSV</a></p>"
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Message</th><th>Issue</th><th>Score</th><th>Boundary</th>"
            "<th>Signals</th><th>Parser</th><th>Excerpt</th><th>AI</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=8>No parse issues yet</td></tr>'}</tbody></table></div>"
        )
        return _page("Ingestion parse issues", body)

    @route("/review", methods=["GET"], name="ingestion_issue_review")
    async def review(self, request: Request) -> Response:
        """Render one parse issue and any pending AI proposal."""
        revision_raw = request.query_params.get("revision_id")
        run_raw = request.query_params.get("run_id")
        error = request.query_params.get("error")
        event = None
        run = None
        if revision_raw:
            try:
                revision_id = UUID(revision_raw)
            except ValueError:
                return RedirectResponse("/admin/ingestion-issues", status_code=303)
            events = await _admin(request).list_parse_issue_events(owner_id=_owner_id(request))
            event = next(
                (item for item in events if item.source_message_revision_id == revision_id),
                None,
            )
            if event is None:
                return RedirectResponse("/admin/ingestion-issues", status_code=303)
        if run_raw:
            try:
                run_id = UUID(run_raw)
            except ValueError:
                return RedirectResponse("/admin/ingestion-issues", status_code=303)
            run = await _admin(request).get_ingestion_ai_parse(run_id=run_id)
            if run is None:
                return RedirectResponse("/admin/ingestion-issues", status_code=303)
        body = _review_document(request, event=event, run=run, error=error)
        return _page("Ingestion AI parse review", body)

    @route("/ai-generate", methods=["POST"], name="generate_ingestion_ai_parse")
    async def generate_ai_parse(self, request: Request) -> Response:
        """Create one AI listing proposal for a parse miss."""
        form = await request.form()
        revision_raw = str(form.get("revision_id", ""))
        try:
            revision_id = UUID(revision_raw)
        except ValueError:
            return RedirectResponse("/admin/ingestion-issues", status_code=303)
        outcome = await _admin(request).generate_ingestion_ai_parse(
            owner_id=_owner_id(request),
            source_message_revision_id=revision_id,
            request_id=getattr(request.state, "admin_request_id", uuid4()),
        )
        if outcome.run is not None:
            error = None if outcome.status is IngestionAiParseStatus.GENERATED else outcome.reason
            return RedirectResponse(
                _review_url(
                    revision_id=revision_id,
                    run_id=outcome.run.id,
                    error=_reason_text(error) if error else None,
                ),
                status_code=303,
            )
        return RedirectResponse(
            _review_url(revision_id=revision_id, error=_reason_text(outcome.reason)),
            status_code=303,
        )

    @route("/ai-apply", methods=["POST"], name="apply_ingestion_ai_parse")
    async def apply_ai_parse(self, request: Request) -> Response:
        """Apply one owner-approved AI listing proposal."""
        form = await request.form()
        run_raw = str(form.get("run_id", ""))
        try:
            run_id = UUID(run_raw)
        except ValueError:
            return RedirectResponse("/admin/ingestion-issues", status_code=303)
        try:
            outcome = await _admin(request).apply_ingestion_ai_parse(
                owner_id=_owner_id(request),
                run_id=run_id,
                request_id=getattr(request.state, "admin_request_id", uuid4()),
            )
        except AdminDeniedError as denied:
            return RedirectResponse(
                _review_url(run_id=run_id, error=str(denied)),
                status_code=303,
            )
        error = None
        if outcome.status is not IngestionAiApplyStatus.APPLIED:
            error = outcome.status.value
        run = outcome.run
        revision_id = run.source_message_revision_id if run is not None else None
        return RedirectResponse(
            _review_url(
                revision_id=revision_id,
                run_id=run_id,
                error=error,
            ),
            status_code=303,
        )

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
