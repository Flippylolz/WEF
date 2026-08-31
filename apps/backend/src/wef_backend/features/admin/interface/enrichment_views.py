"""Owner HTML for batch offer enrichment controls and parser-gap reporting."""

# ruff: noqa: E501

from __future__ import annotations

import contextlib
import csv
import io
import json
from html import escape
from typing import TYPE_CHECKING, cast
from uuid import UUID

from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette_admin import CustomView
from starlette_admin.routing import route
from starlette_admin.security.csrf import csrf_input

from wef_backend.features.admin.application.admin_ops import AdminDeniedError, AdminService
from wef_backend.features.admin.application.offer_enrichment import (
    DEFAULT_BATCH_LIMIT,
    BatchState,
)

if TYPE_CHECKING:
    from starlette.requests import Request


def _admin(request: Request) -> AdminService:
    return cast("AdminService", request.state.admin)


def _owner_id(request: Request) -> UUID:
    return cast("UUID", request.state.admin_owner_id)


def _request_id(request: Request) -> UUID:
    return cast("UUID", request.state.admin_request_id)


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title>"
        "<link rel='stylesheet' href='/admin/static/css/admin.css?v=1'>"
        f"</head><body class='wef-page enrichment-page'>"
        f"<h1>{escape(title)}</h1>"
        f"{body}"
        "<p><a href='/admin/offer-enrichment'>Back to batches</a></p>"
        "</body></html>",
    )


class OfferEnrichmentAdminView(CustomView):
    """Start, monitor, and report on missing-only offer autofill batches."""

    def __init__(self) -> None:
        """Register the offer enrichment admin menu entry."""
        super().__init__(
            menu_label="Offer enrichment",
            icon="fa fa-wand-magic-sparkles",
            path="/offer-enrichment",
        )

    @route("", methods=["GET"], name="offer_enrichment_home")
    async def index(self, request: Request) -> Response:
        """List recent batches and link to preview/report pages."""
        if not _admin(request).ai_curation_enabled:
            return _page(
                "Offer enrichment",
                "<p class='warn'>AI curation is disabled in this environment.</p>",
            )
        batches = await _admin(request).list_offer_enrichment_batches(
            owner_id=_owner_id(request),
        )
        rows = "".join(
            "<tr>"
            f"<td><a href='/admin/offer-enrichment/batch?batch_id={batch.id}'>{escape(str(batch.id))}</a></td>"
            f"<td>{escape(batch.state.value)}</td>"
            f"<td>{batch.candidate_count}</td>"
            f"<td>{batch.processed_count}/{batch.candidate_count}</td>"
            f"<td>{batch.applied_count}</td>"
            f"<td>{batch.skipped_count}</td>"
            f"<td>{batch.failed_count}</td>"
            f"<td>{escape(batch.created_at.isoformat())}</td>"
            "</tr>"
            for batch in batches
        )
        body = (
            "<p><a href='/admin/offer-enrichment/preview'>Preview candidates</a> · "
            "<a href='/admin/offer-enrichment/parser-gaps'>Parser-gap report</a></p>"
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Batch</th><th>State</th><th>Scope</th><th>Processed</th>"
            "<th>Applied</th><th>Skipped</th><th>Failed</th><th>Created</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=8>No batches yet</td></tr>'}</tbody></table></div>"
        )
        return _page("Offer enrichment", body)

    @route("/preview", methods=["GET"], name="offer_enrichment_preview")
    async def preview(self, request: Request) -> Response:
        """Show immutable candidate scope before Start batch."""
        if not _admin(request).ai_curation_enabled:
            return RedirectResponse("/admin/offer-enrichment", status_code=303)
        preview = await _admin(request).preview_offer_enrichment(
            owner_id=_owner_id(request),
            limit=DEFAULT_BATCH_LIMIT,
        )
        body = (
            "<div class='warn' role='alert'>"
            "<strong>Start batch</strong> is the only confirmation before eligible "
            "missing fields are written automatically. Review the scope below first."
            "</div>"
            "<ul>"
            f"<li>Eligible offers in preview: {preview.candidate_count}</li>"
            f"<li>Batch size (immutable after start): up to {preview.preview_limit}</li>"
            f"<li>Queued items across open batches: {preview.queued_items}</li>"
            f"<li>Provider calls today: {preview.daily_used}/{preview.daily_limit}</li>"
            f"<li>Estimated free-tier days for this scope: {preview.estimated_days}</li>"
            "</ul>"
            "<form method='post' action='/admin/offer-enrichment/start'>"
            f"{csrf_input(request)}"
            f"<input type='hidden' name='limit' value='{preview.preview_limit}' />"
            "<button type='submit'>Start batch</button>"
            "</form>"
        )
        return _page("Preview offer enrichment", body)

    @route("/start", methods=["POST"], name="offer_enrichment_start")
    async def start(self, request: Request) -> Response:
        """Create one owner-authorized batch."""
        form = await request.form()
        limit = int(str(form.get("limit", DEFAULT_BATCH_LIMIT)))
        try:
            batch = await _admin(request).start_offer_enrichment(
                owner_id=_owner_id(request),
                request_id=_request_id(request),
                limit=limit,
            )
        except AdminDeniedError:
            return RedirectResponse("/admin/offer-enrichment/preview?error=denied", status_code=303)
        return RedirectResponse(
            f"/admin/offer-enrichment/batch?batch_id={batch.id}",
            status_code=303,
        )

    @route("/batch", methods=["GET"], name="offer_enrichment_batch")
    async def batch_detail(self, request: Request) -> Response:
        """Show batch progress, item outcomes, and controls."""
        batch_id_raw = request.query_params.get("batch_id")
        if batch_id_raw is None:
            return RedirectResponse("/admin/offer-enrichment", status_code=303)
        batch_id = UUID(batch_id_raw)
        with contextlib.suppress(AdminDeniedError):
            detail = await _admin(request).get_offer_enrichment_batch(
                owner_id=_owner_id(request),
                batch_id=batch_id,
            )
            batch = detail.batch
            item_rows = "".join(
                "<tr>"
                f"<td>{item.ordinal + 1}</td>"
                f"<td>{escape(str(item.offer_id))}</td>"
                f"<td>{escape(item.state.value)}</td>"
                f"<td>{escape(item.outcome.value if item.outcome else '—')}</td>"
                "</tr>"
                for item in detail.items
            )
            event_rows = "".join(
                "<tr>"
                f"<td>{escape(event.field_name)}</td>"
                f"<td>{escape(event.outcome.value)}</td>"
                f"<td>{escape(event.reason)}</td>"
                f"<td>{escape(str(event.applied_value))}</td>"
                "</tr>"
                for event in detail.events
            )
            origin_rows = "".join(
                "<tr>"
                f"<td>{escape(str(origin.offer_id))}</td>"
                f"<td>{escape(origin.field_name)}</td>"
                f"<td>{escape(origin.state.value)}</td>"
                f"<td>{escape(str(origin.parser_version or '—'))}</td>"
                "</tr>"
                for origin in detail.active_origins
            )
            controls = ""
            if batch.state in {BatchState.QUEUED, BatchState.RUNNING, BatchState.PAUSED}:
                controls += (
                    "<form method='post' action='/admin/offer-enrichment/process'>"
                    f"{csrf_input(request)}"
                    f"<input type='hidden' name='batch_id' value='{batch.id}' />"
                    "<button type='submit'>Process next item</button></form> "
                )
            if batch.state in {BatchState.QUEUED, BatchState.RUNNING}:
                controls += (
                    "<form method='post' action='/admin/offer-enrichment/pause'>"
                    f"{csrf_input(request)}"
                    f"<input type='hidden' name='batch_id' value='{batch.id}' />"
                    "<button type='submit'>Pause</button></form> "
                )
            if batch.state is BatchState.PAUSED:
                controls += (
                    "<form method='post' action='/admin/offer-enrichment/resume'>"
                    f"{csrf_input(request)}"
                    f"<input type='hidden' name='batch_id' value='{batch.id}' />"
                    "<button type='submit'>Resume</button></form> "
                )
            if batch.state in {BatchState.COMPLETED, BatchState.PAUSED, BatchState.FAILED}:
                controls += (
                    "<form method='post' action='/admin/offer-enrichment/revert'>"
                    f"{csrf_input(request)}"
                    f"<input type='hidden' name='batch_id' value='{batch.id}' />"
                    "<button type='submit'>Revert applied values</button></form>"
                )
            body = (
                f"<p>State: <strong>{escape(batch.state.value)}</strong> · "
                f"Processed {batch.processed_count}/{batch.candidate_count} · "
                f"Applied {batch.applied_count} · Skipped {batch.skipped_count} · "
                f"Failed {batch.failed_count}</p>"
                f"<p class='admin-actions'>{controls}</p>"
                "<h2>Items</h2>"
                "<div class='table-wrap'><table class='data-table'><thead><tr><th>#</th><th>Offer</th><th>State</th><th>Outcome</th>"
                f"</tr></thead><tbody>{item_rows or '<tr><td colspan=4>No items</td></tr>'}</tbody></table></div>"
                "<h2>Field events</h2>"
                "<div class='table-wrap'><table class='data-table'><thead><tr><th>Field</th><th>Outcome</th><th>Reason</th><th>Value</th>"
                f"</tr></thead><tbody>{event_rows or '<tr><td colspan=4>No events</td></tr>'}</tbody></table></div>"
                "<h2>Active AI origins</h2>"
                "<div class='table-wrap'><table class='data-table'><thead><tr><th>Offer</th><th>Field</th><th>State</th><th>Parser</th>"
                f"</tr></thead><tbody>{origin_rows or '<tr><td colspan=4>None</td></tr>'}</tbody></table></div>"
            )
            return _page("Batch progress", body)
        return RedirectResponse("/admin/offer-enrichment", status_code=303)

    @route("/process", methods=["POST"], name="offer_enrichment_process")
    async def process(self, request: Request) -> Response:
        """Process the next queued item in one batch."""
        form = await request.form()
        batch_id = UUID(str(form.get("batch_id")))
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).process_offer_enrichment(
                owner_id=_owner_id(request),
                batch_id=batch_id,
                request_id=_request_id(request),
            )
        return RedirectResponse(
            f"/admin/offer-enrichment/batch?batch_id={batch_id}",
            status_code=303,
        )

    @route("/pause", methods=["POST"], name="offer_enrichment_pause")
    async def pause(self, request: Request) -> Response:
        """Pause one running batch."""
        form = await request.form()
        batch_id = UUID(str(form.get("batch_id")))
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).pause_offer_enrichment(
                owner_id=_owner_id(request),
                batch_id=batch_id,
                request_id=_request_id(request),
            )
        return RedirectResponse(
            f"/admin/offer-enrichment/batch?batch_id={batch_id}",
            status_code=303,
        )

    @route("/resume", methods=["POST"], name="offer_enrichment_resume")
    async def resume(self, request: Request) -> Response:
        """Resume one paused batch."""
        form = await request.form()
        batch_id = UUID(str(form.get("batch_id")))
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).resume_offer_enrichment(
                owner_id=_owner_id(request),
                batch_id=batch_id,
                request_id=_request_id(request),
            )
        return RedirectResponse(
            f"/admin/offer-enrichment/batch?batch_id={batch_id}",
            status_code=303,
        )

    @route("/revert", methods=["POST"], name="offer_enrichment_revert")
    async def revert(self, request: Request) -> Response:
        """Revert still-matching applied values for one batch."""
        form = await request.form()
        batch_id = UUID(str(form.get("batch_id")))
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).revert_offer_enrichment(
                owner_id=_owner_id(request),
                batch_id=batch_id,
                request_id=_request_id(request),
            )
        return RedirectResponse(
            f"/admin/offer-enrichment/batch?batch_id={batch_id}",
            status_code=303,
        )

    @route("/parser-gaps", methods=["GET"], name="offer_enrichment_parser_gaps")
    async def parser_gaps(self, request: Request) -> Response:
        """Render the redacted parser-gap report table."""
        events = await _admin(request).list_parser_gap_events(owner_id=_owner_id(request))
        rows = "".join(
            "<tr>"
            f"<td>{escape(str(event.offer_id))}</td>"
            f"<td>{escape(event.field_name)}</td>"
            f"<td>{escape(event.outcome.value)}</td>"
            f"<td>{escape(str(event.applied_value or event.proposed_value))}</td>"
            f"<td>{escape(event.parser_version or '—')}</td>"
            f"<td>{escape(event.model)}</td>"
            f"<td>{escape(event.prompt_version)}</td>"
            f"<td>{escape(event.schema_version)}</td>"
            f"<td>{event.source_start}-{event.source_end}</td>"
            "</tr>"
            for event in events
        )
        body = (
            "<p><a href='/admin/offer-enrichment/parser-gaps/export.json'>Export JSON</a> · "
            "<a href='/admin/offer-enrichment/parser-gaps/export.csv'>Export CSV</a></p>"
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Offer</th><th>Field</th><th>Outcome</th><th>Value</th>"
            "<th>Parser</th><th>Model</th><th>Prompt</th><th>Schema</th><th>Offsets</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=9>No parser-gap events</td></tr>'}</tbody></table></div>"
        )
        return _page("Parser-gap report", body)

    @route("/parser-gaps/export.json", methods=["GET"], name="offer_enrichment_parser_gaps_json")
    async def parser_gaps_json(self, request: Request) -> Response:
        """Download parser-gap rows as JSON."""
        events = await _admin(request).list_parser_gap_events(owner_id=_owner_id(request))
        payload = [
            {
                "offer_id": str(event.offer_id),
                "field_name": event.field_name,
                "outcome": event.outcome.value,
                "typed_value": event.applied_value
                if event.applied_value is not None
                else event.proposed_value,
                "source_revision_id": str(event.source_message_revision_id)
                if event.source_message_revision_id
                else None,
                "source_start": event.source_start,
                "source_end": event.source_end,
                "parser_version": event.parser_version,
                "model": event.model,
                "prompt_version": event.prompt_version,
                "schema_version": event.schema_version,
            }
            for event in events
        ]
        return Response(
            json.dumps(payload, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="parser-gaps.json"'},
        )

    @route("/parser-gaps/export.csv", methods=["GET"], name="offer_enrichment_parser_gaps_csv")
    async def parser_gaps_csv(self, request: Request) -> Response:
        """Download parser-gap rows as CSV."""
        events = await _admin(request).list_parser_gap_events(owner_id=_owner_id(request))
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "offer_id",
                "field_name",
                "outcome",
                "typed_value",
                "source_revision_id",
                "source_start",
                "source_end",
                "parser_version",
                "model",
                "prompt_version",
                "schema_version",
            ],
        )
        for event in events:
            writer.writerow(
                [
                    str(event.offer_id),
                    event.field_name,
                    event.outcome.value,
                    event.applied_value
                    if event.applied_value is not None
                    else event.proposed_value,
                    str(event.source_message_revision_id)
                    if event.source_message_revision_id
                    else "",
                    event.source_start,
                    event.source_end,
                    event.parser_version or "",
                    event.model,
                    event.prompt_version,
                    event.schema_version,
                ],
            )
        return Response(
            buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="parser-gaps.csv"'},
        )
