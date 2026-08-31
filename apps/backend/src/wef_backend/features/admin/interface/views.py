"""Owner-console Starlette Admin custom views."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import escape
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode
from uuid import UUID, uuid4

from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette_admin import CustomView
from starlette_admin.routing import route
from starlette_admin.security.csrf import csrf_input
from starlette_admin.widgets import HtmlWidget, TableWidget

from wef_backend.features.admin.application.admin_ops import (
    AdminDeniedError,
    AdminService,
    LocationAdminSummary,
    LocationEditDetail,
    LocationStatusFilter,
    OfferContextSummary,
)
from wef_backend.features.admin.application.ai_review import (
    FieldAction,
    PlaceReviewRun,
    PlaceReviewStatus,
    ReviewRunState,
)

if TYPE_CHECKING:
    from starlette.datastructures import FormData
    from starlette.requests import Request

_WARSAW_CENTER = ("52.2297", "21.0122")
_FILTER_TABS: tuple[tuple[LocationStatusFilter, str], ...] = (
    (LocationStatusFilter.PENDING, "Pending"),
    (LocationStatusFilter.NEEDS_REVIEW, "Needs review"),
    (LocationStatusFilter.UNGEOCODED, "Ungeocoded"),
    (LocationStatusFilter.ACCEPTED, "Accepted"),
    (LocationStatusFilter.REJECTED, "Rejected"),
    (LocationStatusFilter.ALL, "All"),
)


def _admin(request: Request) -> AdminService:
    admin: AdminService = request.state.admin
    return admin


class UsersAdminView(CustomView):
    """List accounts and run owner-authorized account actions."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Users",
            icon="fa fa-users",
            path="/users",
            widget=self._users_widget,
        )

    async def _users_widget(self, request: Request) -> HtmlWidget:
        accounts = await _admin(request).list_accounts(limit=100)
        rows = "".join(
            (
                "<tr>"
                f"<td>{escape(account.username)}</td>"
                f"<td>{escape(account.role.value)}</td>"
                f"<td>{'active' if account.is_active else 'disabled'}</td>"
                f"<td>{'yes' if account.must_change_password else 'no'}</td>"
                f"<td><code>{escape(str(account.id))}</code></td>"
                "<td class='admin-actions'>"
                f"{_action_form(request, 'disable', account.id, 'Disable')}"
                f"{_action_form(request, 'reactivate', account.id, 'Reactivate')}"
                f"{_action_form(request, 'revoke', account.id, 'Revoke sessions')}"
                f"{_reset_form(request, account.id)}"
                "</td></tr>"
            )
            for account in accounts
        )
        html = (
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Username</th><th>Role</th><th>Status</th>"
            "<th>Must change</th><th>Id</th><th>Actions</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=6>No accounts</td></tr>'}"
            "</tbody></table></div>"
        )
        return HtmlWidget(html=html)

    @route("/disable", methods=["POST"], name="disable")
    async def disable(self, request: Request) -> Response:
        """Disable one account through the owner interactor."""
        return await _run_user_action(request, "disable")

    @route("/reactivate", methods=["POST"], name="reactivate")
    async def reactivate(self, request: Request) -> Response:
        """Reactivate one account through the owner interactor."""
        return await _run_user_action(request, "reactivate")

    @route("/revoke", methods=["POST"], name="revoke")
    async def revoke(self, request: Request) -> Response:
        """Revoke sessions for one account through the owner interactor."""
        return await _run_user_action(request, "revoke")

    @route("/reset", methods=["POST"], name="reset")
    async def reset(self, request: Request) -> Response:
        """Force-reset one account password through the owner interactor."""
        form = await request.form()
        target = UUID(str(form.get("user_id")))
        temporary = str(form.get("temporary_password") or "")
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).force_reset_password(
                owner_id=request.state.admin_owner_id,
                target_user_id=target,
                temporary_password=temporary,
                request_id=getattr(request.state, "admin_request_id", uuid4()),
            )
        return RedirectResponse(url="/admin/users", status_code=303)


async def _run_user_action(request: Request, action: str) -> Response:
    form = await request.form()
    target = UUID(str(form.get("user_id")))
    admin = _admin(request)
    owner_id = request.state.admin_owner_id
    request_id = getattr(request.state, "admin_request_id", uuid4())
    with contextlib.suppress(AdminDeniedError):
        if action == "disable":
            await admin.disable_user(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
        elif action == "reactivate":
            await admin.reactivate_user(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
        elif action == "revoke":
            await admin.revoke_user_sessions(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
    return RedirectResponse(url="/admin/users", status_code=303)


def _action_form(request: Request, action: str, user_id: UUID, label: str) -> str:
    return (
        f"<form method='post' action='/admin/users/{action}'>"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='user_id' value='{user_id}'/>"
        f"<button type='submit'>{escape(label)}</button></form> "
    )


def _reset_form(request: Request, user_id: UUID) -> str:
    return (
        "<form method='post' action='/admin/users/reset'>"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='user_id' value='{user_id}'/>"
        "<input type='password' name='temporary_password' "
        "placeholder='temporary password' minlength='10' required/>"
        "<button type='submit'>Force reset</button></form>"
    )


class RevealAuditsView(CustomView):
    """Read-only minimized contact reveal audits."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Reveal audits",
            icon="fa fa-eye",
            path="/reveal-audits",
            widget=TableWidget(
                title="Contact reveal audits",
                columns=["User", "Offer", "Outcome", "When", "Request"],
                rows_callback=_reveal_rows,
            ),
        )


async def _reveal_rows(request: Request) -> list[list[Any]]:
    rows = await _admin(request).list_reveal_audits(limit=100)
    return [
        [
            str(row.user_id),
            str(row.offer_id),
            row.outcome,
            row.revealed_at.isoformat(),
            str(row.request_id),
        ]
        for row in rows
    ]


class AdminAuditsView(CustomView):
    """Read-only redacted admin action history."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Admin audits",
            icon="fa fa-clipboard-list",
            path="/admin-audits",
            widget=TableWidget(
                title="Admin audits",
                columns=["Owner", "Action", "Target", "Outcome", "When"],
                rows_callback=_admin_audit_rows,
            ),
        )


async def _admin_audit_rows(request: Request) -> list[list[Any]]:
    rows = await _admin(request).list_admin_audits(limit=100)
    return [
        [
            str(row.owner_user_id),
            row.action,
            row.target_id or "",
            row.outcome.value,
            row.occurred_at.isoformat(),
        ]
        for row in rows
    ]


@dataclass(frozen=True, slots=True)
class _ListFilters:
    """Parsed list-page query state."""

    status: LocationStatusFilter
    search: str | None


def _parse_list_filters(request: Request) -> _ListFilters:
    """Read the bounded status slice and search term from the query string."""
    raw_status = str(request.query_params.get("status", LocationStatusFilter.PENDING.value))
    try:
        status = LocationStatusFilter(raw_status)
    except ValueError:
        status = LocationStatusFilter.PENDING
    raw_search = str(request.query_params.get("search", "")).strip()
    return _ListFilters(status=status, search=raw_search or None)


def _places_url(filters: _ListFilters) -> str:
    """Build the list-page URL preserving the current filter state."""
    params: dict[str, str] = {"status": filters.status.value}
    if filters.search is not None:
        params["search"] = filters.search
    return f"/admin/places?{urlencode(params)}"


def _filter_tabs(filters: _ListFilters) -> str:
    """Render the status-slice navigation tabs."""
    anchors = [
        "<a href='"
        + _places_url(_ListFilters(status=tab_status, search=filters.search))
        + "'>"
        + ("<strong>" if tab_status is filters.status else "")
        + escape(label)
        + ("</strong>" if tab_status is filters.status else "")
        + "</a>"
        for tab_status, label in _FILTER_TABS
    ]
    return f"<nav class='places-tabs'>{''.join(anchors)}</nav>"


def _search_form(filters: _ListFilters) -> str:
    """Render the address search form."""
    return (
        "<form method='get' action='/admin/places' class='places-search'>"
        f"<input type='hidden' name='status' value='{escape(filters.status.value)}'/>"
        "<input type='search' name='search' placeholder='Search address' "
        f"value='{escape(filters.search or '')}'/>"
        "<button type='submit'>Search</button>"
        "</form>"
    )


def _place_action_form(
    request: Request,
    action: str,
    place: LocationAdminSummary,
    filters: _ListFilters,
    label: str,
) -> str:
    """Render one CSRF-protected decision form preserving the filter state."""
    return (
        f"<form method='post' action='/admin/places/{action}' "
        "onsubmit=\"this.querySelectorAll('button').forEach(function(b){b.disabled=true})\">"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='location_id' value='{place.id}'/>"
        f"<input type='hidden' name='status' value='{escape(filters.status.value)}'/>"
        f"<input type='hidden' name='search' value='{escape(filters.search or '')}'/>"
        f"<button type='submit'>{escape(label)}</button></form> "
    )


def _place_row(
    request: Request,
    place: LocationAdminSummary,
    filters: _ListFilters,
    *,
    ai_enabled: bool,
) -> str:
    """Render one location row with its verification actions."""
    actions = f"<a href='/admin/places/set-point?location_id={place.id}'>Edit point</a> "
    if ai_enabled:
        actions += _place_action_form(
            request,
            "ai-review/generate",
            place,
            filters,
            "Review with AI",
        )
    if place.has_candidate:
        actions += _place_action_form(request, "accept", place, filters, "Accept candidate")
    if place.review_status != "rejected":
        actions += _place_action_form(request, "reject", place, filters, "Reject")
    if place.review_status in ("accepted", "rejected"):
        actions += _place_action_form(request, "unresolve", place, filters, "Unresolve")
    confidence = "—" if place.confidence is None else f"{place.confidence:.2f}"
    return (
        "<tr>"
        f"<td>{escape(place.display_address)}<br><small>{escape(place.display_name)}</small></td>"
        f"<td>{escape(place.district or '—')}</td>"
        f"<td>{escape(place.review_status)}{' (out of scope)' if place.out_of_scope else ''}</td>"
        f"<td>{escape(place.precision)}</td>"
        f"<td>{escape(confidence)}</td>"
        f"<td>{escape(place.reason_code or '—')}</td>"
        f"<td>{'yes' if place.has_point else 'no'}</td>"
        f"<td>{place.offer_count}</td>"
        f"<td class='admin-actions'>{actions}</td>"
        "</tr>"
    )


class LocationsAdminView(CustomView):
    """Browse every location and resolve its map point."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Locations",
            icon="fa fa-map-location-dot",
            path="/places",
            widget=self._places_widget,
        )

    async def _places_widget(self, request: Request) -> HtmlWidget:
        filters = _parse_list_filters(request)
        places = await _admin(request).list_locations(
            status=filters.status,
            search=filters.search,
            limit=100,
        )
        ai_enabled = _admin(request).ai_curation_enabled
        rows = "".join(
            _place_row(request, place, filters, ai_enabled=ai_enabled) for place in places
        )
        list_error = request.query_params.get("error")
        error_banner = (
            "" if not list_error else f"<div class='error' role='alert'>{escape(list_error)}</div>"
        )
        html = (
            f"{error_banner}"
            "<div class='places-toolbar'>"
            f"{_filter_tabs(filters)}"
            f"{_search_form(filters)}"
            "</div>"
            "<div class='table-wrap'><table class='data-table'><thead><tr>"
            "<th>Address</th><th>District</th><th>Status</th><th>Precision</th>"
            "<th>Confidence</th><th>Reason</th><th>Point</th><th>Offers</th><th>Actions</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=9>No locations</td></tr>'}"
            "</tbody></table></div>"
        )
        return HtmlWidget(html=html)

    @route("/accept", methods=["POST"], name="accept_place")
    async def accept_place(self, request: Request) -> Response:
        """Promote the latest in-scope candidate point for one location."""
        return await _run_place_action(request, "accept")

    @route("/reject", methods=["POST"], name="reject_place")
    async def reject_place(self, request: Request) -> Response:
        """Mark one location rejected."""
        return await _run_place_action(request, "reject")

    @route("/unresolve", methods=["POST"], name="unresolve_place")
    async def unresolve_place(self, request: Request) -> Response:
        """Return one decided location to needs_review."""
        return await _run_place_action(request, "unresolve")

    @route("/set-point", methods=["GET"], name="set_point_page")
    async def set_point_page(self, request: Request) -> Response:
        """Render the full-page map picker with the location's offer evidence."""
        filters = _parse_list_filters(request)
        error = request.query_params.get("error") or None
        try:
            location_id = UUID(str(request.query_params.get("location_id", "")))
        except ValueError:
            return RedirectResponse(_places_url(filters), status_code=303)
        with contextlib.suppress(AdminDeniedError):
            detail = await _admin(request).get_location_for_edit(location_id=location_id)
            return HTMLResponse(
                _set_point_document(request, detail, filters=filters, error=error),
            )
        return RedirectResponse(_places_url(filters), status_code=303)

    @route("/set-point", methods=["POST"], name="set_point_save")
    async def set_point_save(self, request: Request) -> Response:
        """Apply the operator-placed point through the owner interactor."""
        form = await request.form()
        filters = _ListFilters(
            status=_safe_status(str(form.get("status", LocationStatusFilter.PENDING.value))),
            search=str(form.get("search", "")).strip() or None,
        )
        location_id = str(form.get("location_id", ""))
        picker_url = (
            f"/admin/places/set-point?location_id={quote(location_id)}"
            f"&status={quote(filters.status.value)}"
        )
        if filters.search is not None:
            picker_url += f"&search={quote(filters.search)}"
        try:
            longitude = Decimal(str(form.get("longitude", "")))
            latitude = Decimal(str(form.get("latitude", "")))
        except (InvalidOperation, ValueError):
            return RedirectResponse(
                f"{picker_url}&error={quote('Coordinates must be decimal numbers')}",
                status_code=303,
            )
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).set_place_point(
                owner_id=request.state.admin_owner_id,
                location_id=UUID(location_id),
                longitude=longitude,
                latitude=latitude,
                request_id=getattr(request.state, "admin_request_id", uuid4()),
            )
            return RedirectResponse(_places_url(filters), status_code=303)
        refused = "The point was refused - it must be inside the Warsaw scope"
        return RedirectResponse(
            f"{picker_url}&error={quote(refused)}",
            status_code=303,
        )

    @route("/ai-review/generate", methods=["POST"], name="generate_place_ai_review")
    async def generate_place_ai_review(self, request: Request) -> Response:
        """Create one review and redirect to the result page."""
        form = await request.form()
        filters = _form_filters(form)
        location_id = _form_uuid(form, "location_id")
        if location_id is None:
            return RedirectResponse(_places_url(filters), status_code=303)
        admin = _admin(request)
        owner_id = request.state.admin_owner_id
        request_id = getattr(request.state, "admin_request_id", uuid4())
        outcome = await admin.generate_place_review(
            owner_id=owner_id,
            location_id=location_id,
            request_id=request_id,
        )
        if outcome.run is not None:
            error = None if outcome.status is PlaceReviewStatus.GENERATED else outcome.reason
            return RedirectResponse(
                _ai_review_url(outcome.run.id, filters, error=error),
                status_code=303,
            )
        if outcome.reason == "in_flight":
            pending = await admin.get_place_review.pending_for_location(
                owner_id=owner_id,
                location_id=location_id,
            )
            if pending is not None:
                return RedirectResponse(_ai_review_url(pending.id, filters), status_code=303)
        return RedirectResponse(
            f"{_places_url(filters)}&error={quote(_ai_reason_text(outcome.reason))}",
            status_code=303,
        )

    @route("/ai-review", methods=["GET"], name="place_ai_review")
    async def place_ai_review(self, request: Request) -> Response:
        """Render one persisted review without regenerating it."""
        filters = _parse_list_filters(request)
        error = request.query_params.get("error") or None
        try:
            run_id = UUID(str(request.query_params.get("run_id", "")))
        except ValueError:
            return RedirectResponse(_places_url(filters), status_code=303)
        run = await _admin(request).get_place_review(
            owner_id=request.state.admin_owner_id,
            run_id=run_id,
        )
        if run is None:
            return RedirectResponse(_places_url(filters), status_code=303)
        return HTMLResponse(
            _ai_review_document(request, run, filters=filters, error=error),
        )

    @route("/ai-review/apply", methods=["POST"], name="apply_place_ai_review")
    async def apply_place_ai_review(self, request: Request) -> Response:
        """Apply owner-selected fields from one pending review."""
        form = await request.form()
        filters = _form_filters(form)
        run_id = _form_uuid(form, "run_id")
        if run_id is None:
            return RedirectResponse(_places_url(filters), status_code=303)
        selected = tuple(
            str(value) for value in form.getlist("selected_fields") if str(value).strip()
        )
        try:
            run = await _admin(request).apply_place_review(
                owner_id=request.state.admin_owner_id,
                run_id=run_id,
                selected_fields=selected,
                request_id=getattr(request.state, "admin_request_id", uuid4()),
            )
        except AdminDeniedError as denied:
            return RedirectResponse(
                _ai_review_url(run_id, filters, error=str(denied)),
                status_code=303,
            )
        return RedirectResponse(_ai_review_url(run.id, filters), status_code=303)


def _form_filters(form: FormData) -> _ListFilters:
    """Read list filters from a posted admin form."""
    return _ListFilters(
        status=_safe_status(str(form.get("status", LocationStatusFilter.PENDING.value))),
        search=str(form.get("search", "")).strip() or None,
    )


def _form_uuid(form: FormData, name: str) -> UUID | None:
    """Parse one UUID form field, or None when missing/invalid."""
    try:
        return UUID(str(form.get(name, "")))
    except ValueError:
        return None


async def _run_place_action(request: Request, action: str) -> Response:
    """Run one location decision and return to the same list slice."""
    form = await request.form()
    filters = _ListFilters(
        status=_safe_status(str(form.get("status", LocationStatusFilter.PENDING.value))),
        search=str(form.get("search", "")).strip() or None,
    )
    target = UUID(str(form.get("location_id")))
    admin = _admin(request)
    owner_id = request.state.admin_owner_id
    request_id = getattr(request.state, "admin_request_id", uuid4())
    with contextlib.suppress(AdminDeniedError):
        if action == "accept":
            await admin.accept_place_candidate(
                owner_id=owner_id,
                location_id=target,
                request_id=request_id,
            )
        elif action == "reject":
            await admin.reject_place(
                owner_id=owner_id,
                location_id=target,
                request_id=request_id,
            )
        elif action == "unresolve":
            await admin.unresolve_place(
                owner_id=owner_id,
                location_id=target,
                request_id=request_id,
            )
    return RedirectResponse(url=_places_url(filters), status_code=303)


def _safe_status(raw: str) -> LocationStatusFilter:
    """Convert a form-provided status value, falling back to pending."""
    try:
        return LocationStatusFilter(raw)
    except ValueError:
        return LocationStatusFilter.PENDING


def _format_range(
    low: int | None,
    high: int | None,
    suffix: str,
    *,
    divisor: int = 1,
) -> str:
    """Format a min/max range; prices use a 100 divisor for minor units."""
    if low is None and high is None:
        return "—"

    def _text(value: int | None) -> str:
        return "—" if value is None else f"{value // divisor:,}".replace(",", " ")

    return f"{_text(low)}-{_text(high)} {suffix}".strip()


def _offer_card(offer: OfferContextSummary) -> str:
    """Render one retained offer as operator verification evidence."""
    published = offer.published_at.date().isoformat()
    area_low = None if offer.area_min_sqm is None else int(offer.area_min_sqm)
    area_high = None if offer.area_max_sqm is None else int(offer.area_max_sqm)
    price = _format_range(
        offer.price_min_minor,
        offer.price_max_minor,
        offer.currency or "",
        divisor=100,
    )
    area = _format_range(area_low, area_high, "m²")
    rooms = _format_range(offer.rooms_min, offer.rooms_max, "")
    return (
        "<div class='offer'>"
        f"<div><strong>{escape(offer.content_type)}</strong> · "
        f"{escape(offer.market_type)} · {escape(offer.visibility)}</div>"
        f"<div>{escape(price)} · {escape(area)} · rooms {escape(rooms)}</div>"
        f"<blockquote>{escape(offer.source_text_excerpt)}</blockquote>"
        f"<div class='muted'>published {escape(published)}</div>"
        "</div>"
    )


def _set_point_document(
    request: Request,
    detail: LocationEditDetail,
    *,
    filters: _ListFilters,
    error: str | None,
) -> str:
    """Build the standalone set-point picker page."""
    summary = detail.summary
    initial_lat, initial_lon = _WARSAW_CENTER
    initial_zoom = "12"
    point_lat = detail.latitude
    point_lon = detail.longitude
    if point_lat is not None and point_lon is not None:
        initial_lat, initial_lon, initial_zoom = f"{point_lat}", f"{point_lon}", "17"
    elif detail.candidate is not None:
        initial_lat, initial_lon, initial_zoom = (
            f"{detail.candidate.latitude}",
            f"{detail.candidate.longitude}",
            "17",
        )
    marker_attrs = (
        ""
        if point_lat is None or point_lon is None
        else f" data-point-lat='{point_lat}' data-point-lon='{point_lon}'"
    )
    candidate_attrs = (
        ""
        if detail.candidate is None
        else (
            " data-candidate-lat='"
            f"{detail.candidate.latitude}"
            "' data-candidate-lon='"
            f"{detail.candidate.longitude}"
            "'"
        )
    )
    candidate_line = "None retained"
    if detail.candidate is not None:
        candidate = detail.candidate
        candidate_line = (
            f"{escape(candidate.provider)} · {escape(candidate.precision)} · "
            f"{candidate.confidence:.2f}"
            + (f" — {escape(candidate.display_name or '')}" if candidate.display_name else "")
        )
    current_line = (
        "not placed" if point_lat is None or point_lon is None else f"{point_lat}, {point_lon}"
    )
    error_banner = "" if error is None else f"<div class='error'>{escape(error)}</div>"
    offers = "".join(_offer_card(offer) for offer in detail.offers)
    scope_note = " · OUT OF SCOPE" if summary.out_of_scope else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'/>"
        f"<title>Set point — {escape(summary.display_address)}</title>"
        "<link rel='stylesheet' href='/admin/static/css/admin.css?v=1'/>"
        "</head><body class='wef-page point-picker'>"
        "<header>"
        f"<a href='{_places_url(filters)}'>&larr; Locations</a>"
        f"<strong>{escape(summary.display_address)}</strong>"
        f"<span class='muted'>{escape(summary.city)}"
        + (f" · {escape(summary.district)}" if summary.district else "")
        + "</span></header>"
        f"{error_banner}"
        "<main><aside id='evidence'>"
        "<h3>Location</h3><dl>"
        f"<dt>Status</dt><dd>{escape(summary.review_status)}{scope_note}</dd>"
        f"<dt>Normalized address</dt><dd><code>{escape(detail.normalized_address)}</code></dd>"
        f"<dt>Current point</dt><dd>{escape(current_line)}</dd>"
        f"<dt>Candidate</dt><dd>{candidate_line}</dd>"
        "</dl>"
        f"<h3>Latest offers ({summary.offer_count})</h3>"
        + (offers or "<p class='muted'>No offers retained.</p>")
        + "</aside>"
        f"<div id='map' data-lat='{initial_lat}' data-lon='{initial_lon}' "
        f"data-zoom='{initial_zoom}'{marker_attrs}{candidate_attrs}>"
        "<div class='toolbar'>"
        "<button type='button' id='zoom-in' aria-label='Zoom in'>+</button>"
        "<button type='button' id='zoom-out' aria-label='Zoom out'>&minus;</button>"
        "</div>"
        "<div id='tile-error' hidden class='tile-error'>"
        "Map tiles failed to load — a browser extension or network filter "
        "may be blocking tile.openstreetmap.org."
        "</div>"
        "<div id='ghost' hidden></div>"
        "<div id='marker' hidden></div>"
        "</div></main>"
        "<form class='point' method='post' action='/admin/places/set-point'>"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='location_id' value='{summary.id}'/>"
        f"<input type='hidden' name='status' value='{escape(filters.status.value)}'/>"
        "<label>Latitude "
        f"<input name='latitude' id='lat-input' type='number' step='any' "
        f"min='-90' max='90' required value='{initial_lat}'/></label>"
        "<label>Longitude "
        f"<input name='longitude' id='lng-input' type='number' step='any' "
        f"min='-180' max='180' required value='{initial_lon}'/></label>"
        "<button type='submit'>Save point</button>"
        "<span class='muted'>Click the map to drop the pin · © OpenStreetMap contributors</span>"
        "</form>"
        "<script src='/admin/static/place_picker.js' defer></script>"
        "</body></html>"
    )


_AI_REASON_TEXT = {
    "disabled": "AI review is turned off or not fully configured.",
    "location_not_found": "That place was not found.",
    "daily_limit": "The daily AI review limit has been reached.",
    "masking_failed": "Sources could not be prepared for review.",
    "token_budget": "The available sources exceed the review size limit.",
    "in_flight": "A review is already pending for this place.",
    "timeout": "The AI provider timed out. Try again later.",
    "refusal": "The AI provider refused this review.",
    "quota": "The AI provider quota is exhausted.",
    "rate_limited": "The AI provider rate limit was reached.",
    "network": "The AI provider could not be reached.",
    "schema": "The AI response was not a valid review.",
    "no fields selected": "Select at least one proposed correction before applying.",
    "unsupported field": "Only display name, address, and district can be applied.",
    "selected field is not a correction": "Only proposed corrections can be applied.",
    "review is stale": "This review is stale because the place or sources changed.",
    "review is expired or not pending": "This review has expired or is no longer pending.",
    "canonical location collision": "Applying the address would collide with another place.",
    "AI place review is disabled": "AI review is turned off or not fully configured.",
    "review not found": "That review was not found.",
    "location not found": "That place was not found.",
}

_FIELD_LABELS = {
    "display_name": "Display name",
    "display_address": "Address",
    "district": "District",
}


def _ai_reason_text(reason: str) -> str:
    """Map a bounded reason code or apply denial to owner-safe copy."""
    return _AI_REASON_TEXT.get(reason, "AI review could not be completed.")


def _ai_review_url(
    run_id: UUID,
    filters: _ListFilters,
    error: str | None = None,
) -> str:
    """Build the GET URL for one persisted review."""
    params: dict[str, str] = {"run_id": str(run_id), "status": filters.status.value}
    if filters.search is not None:
        params["search"] = filters.search
    if error:
        params["error"] = error
    return f"/admin/places/ai-review?{urlencode(params)}"


def _field_rows(run: PlaceReviewRun) -> str:
    """Render current/proposed diffs with unselected correction checkboxes."""
    rows: list[str] = []
    for field in run.proposed_fields:
        current = field.current_value or "—"
        proposed = field.proposed_value or "—"
        selectable = field.action == FieldAction.CORRECT.value
        field_id = f"field-{field.field_name}"
        title = escape(_FIELD_LABELS.get(field.field_name, field.field_name))
        checkbox = ""
        label = (
            f"<label for='{escape(field_id)}'>{title}</label>"
            if selectable and run.state is ReviewRunState.PENDING
            else f"<span>{title}</span>"
        )
        if selectable and run.state is ReviewRunState.PENDING:
            checkbox = (
                f"<input type='checkbox' id='{escape(field_id)}' "
                f"name='selected_fields' value='{escape(field.field_name)}'/>"
            )
        rows.append(
            "<tr>"
            f"<td>{checkbox}{label}</td>"
            f"<td>{escape(field.action)}</td>"
            f"<td>{escape(current)}</td>"
            f"<td>{escape(proposed)}</td>"
            f"<td>{escape(field.confidence)}</td>"
            f"<td>{escape(', '.join(field.evidence_revision_ids) or '—')}</td>"
            f"<td>{escape(field.rationale_code)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _ai_review_document(
    request: Request,
    run: PlaceReviewRun,
    *,
    filters: _ListFilters,
    error: str | None,
) -> str:
    """Build the standalone Review with AI result page."""
    error_text = None if error is None else _ai_reason_text(error)
    error_banner = (
        "" if not error_text else f"<div class='error' role='alert'>{escape(error_text)}</div>"
    )
    omitted = run.omitted_source_count
    coverage = (
        f"Reviewed {run.selected_source_count} source description"
        f"{'s' if run.selected_source_count != 1 else ''}. "
    )
    if omitted:
        coverage += (
            f"{omitted} additional description{'s' if omitted != 1 else ''} "
            "were omitted and were not reviewed."
        )
    else:
        coverage += "No source descriptions were omitted."
    warnings = "".join(f"<li>{escape(item)}</li>" for item in run.warnings)
    warning_block = (
        "" if not warnings else f"<section><h2>Warnings</h2><ul>{warnings}</ul></section>"
    )
    applied = run.state is ReviewRunState.APPLIED
    spatial = any(name in run.applied_fields for name in ("display_address", "district"))
    verify = ""
    if applied and spatial:
        verify = (
            "<p role='status'>This place is back in <code>needs_review</code>. "
            "Coordinate verification is a separate action. "
            f"<a href='/admin/places/set-point?location_id={run.location_id}'>"
            "Verify the map point</a>.</p>"
        )
    elif applied:
        verify = "<p role='status'>Selected fields were applied.</p>"
    apply_form = ""
    if run.state is ReviewRunState.PENDING:
        apply_form = (
            "<form method='post' action='/admin/places/ai-review/apply' "
            "onsubmit=\"this.querySelectorAll('button').forEach(function(b){b.disabled=true})\">"
            f"{csrf_input(request)}"
            f"<input type='hidden' name='run_id' value='{run.id}'/>"
            f"<input type='hidden' name='status' value='{escape(filters.status.value)}'/>"
            f"<input type='hidden' name='search' value='{escape(filters.search or '')}'/>"
            "<p>No change is selected by default. Choose each field to apply.</p>"
            "<div class='table-wrap'><table><thead><tr>"
            "<th>Apply</th><th>Action</th><th>Current</th><th>Proposed</th>"
            "<th>Confidence</th><th>Evidence</th><th>Rationale</th>"
            f"</tr></thead><tbody>{_field_rows(run) or '<tr><td colspan=7>No fields</td></tr>'}"
            "</tbody></table></div>"
            "<button type='submit'>Apply selected fields</button>"
            "</form>"
        )
    else:
        apply_form = (
            "<div class='table-wrap'><table><thead><tr>"
            "<th>Field</th><th>Action</th><th>Current</th><th>Proposed</th>"
            "<th>Confidence</th><th>Evidence</th><th>Rationale</th>"
            f"</tr></thead><tbody>{_field_rows(run) or '<tr><td colspan=7>No fields</td></tr>'}"
            "</tbody></table></div>"
        )
    verdict = run.verdict or run.state.value
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'/>"
        "<title>Review with AI</title>"
        "<link rel='stylesheet' href='/admin/static/css/admin.css?v=1'/>"
        "</head><body class='wef-page review-page'>"
        f"<a href='{_places_url(filters)}'>&larr; Locations</a>"
        "<h1>Review with AI</h1>"
        f"{error_banner}"
        f"<p>{escape(coverage)}</p>"
        f"<p>Overall verdict: <strong>{escape(verdict)}</strong> · "
        f"state <code>{escape(run.state.value)}</code></p>"
        f"{warning_block}"
        f"{verify}"
        f"{apply_form}"
        "<p class='muted'>Coordinates are not changed by this review. "
        "Use Edit point after an address or district correction.</p>"
        "</body></html>"
    )
