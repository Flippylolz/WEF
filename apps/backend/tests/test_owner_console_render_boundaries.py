"""Owner console handles expired reviews and nonspatial application receipts."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.datastructures import FormData
from starlette.requests import Request

from wef_backend.features.admin.application.admin_ops import LocationStatusFilter
from wef_backend.features.admin.application.ai_review import PlaceReviewRun, ReviewRunState
from wef_backend.features.admin.interface.parse_issue_views import _review_document
from wef_backend.features.admin.interface.views import (
    LocationsAdminView,
    _ai_review_document,
    _ai_review_url,
    _ListFilters,
    _run_place_action,
    _run_user_action,
)


def _request(admin: MagicMock) -> Request:
    return Request(
        {
            "type": "http",
            "headers": [],
            "session": {},
            "state": {"admin": admin, "admin_owner_id": uuid4()},
        }
    )


@pytest.mark.parametrize("kind", ["user", "place"])
async def test_unknown_owner_action_returns_to_list_without_mutation(kind: str) -> None:
    admin = MagicMock()
    request = MagicMock(state=MagicMock(admin=admin))
    request.form = AsyncMock(
        return_value=FormData({"user_id": str(uuid4()), "location_id": str(uuid4())})
    )
    action = _run_user_action if kind == "user" else _run_place_action
    response = await action(request, "unknown")
    assert response.status_code == 303
    admin.assert_not_called()
    assert not admin.method_calls


@pytest.mark.parametrize("reason", ["in_flight", "disabled"])
async def test_generation_without_persisted_run_returns_a_bounded_error(reason: str) -> None:
    admin = MagicMock(
        generate_place_review=AsyncMock(return_value=MagicMock(run=None, reason=reason)),
        get_place_review=MagicMock(pending_for_location=AsyncMock(return_value=None)),
    )
    request = MagicMock(state=MagicMock(admin=admin))
    request.form = AsyncMock(return_value=FormData({"location_id": str(uuid4())}))
    response = await LocationsAdminView().generate_place_ai_review(request)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/places?status=pending&error=")
    assert admin.get_place_review.pending_for_location.await_count == int(reason == "in_flight")


def test_review_urls_keep_explicit_errors_and_search_terms() -> None:
    url = _ai_review_url(
        uuid4(), _ListFilters(LocationStatusFilter.PENDING, "synthetic search"), error="synthetic"
    )
    assert "error=synthetic" in url
    assert "search=synthetic+search" in url


def test_applied_name_review_displays_scalar_receipt_without_coordinate_verification() -> None:
    run = MagicMock(
        spec=PlaceReviewRun,
        state=ReviewRunState.APPLIED,
        applied_fields=("display_name",),
        selected_source_count=1,
        omitted_source_count=0,
        warnings=(),
        proposed_fields=(),
        verdict="corrections_proposed",
    )
    page = _ai_review_document(
        _request(MagicMock()),
        run,
        filters=_ListFilters(LocationStatusFilter.PENDING, None),
        error=None,
    )
    assert "Selected fields were applied." in page
    assert "Verify the map point" not in page


def test_missing_parser_issue_and_run_render_only_the_safe_return_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "wef_backend.features.admin.interface.parse_issue_views.csrf_input", lambda _: ""
    )
    page = _review_document(_request(MagicMock()), event=None, run=None, error=None)
    assert "Back to issues" in page
    assert "<form" not in page
    assert "<dl>" not in page
