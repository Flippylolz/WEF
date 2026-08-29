"""HTTP adapter for authenticated visit and viewed-offer history."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict

from wef_backend.errors import AuthProblemError, ResourceNotFoundError
from wef_backend.features.identity.application.view_history import (
    ViewedOfferView,
    ViewHistoryService,
)
from wef_backend.features.identity.interface.router import (
    _require_account,
    enforce_trusted_origin,
)

router = APIRouter(
    prefix="/api/v1/view-history",
    tags=["view-history"],
    dependencies=[Depends(enforce_trusted_origin)],
)


class AccountVisitResponse(BaseModel):
    """Stable current and previous visit timestamps for one browser visit."""

    model_config = ConfigDict(extra="forbid")

    visit_id: UUID
    current_visit_at: datetime
    previous_visit_at: datetime | None


class ViewedOfferResponse(BaseModel):
    """One account's aggregate view state for a public offer."""

    model_config = ConfigDict(extra="forbid")

    offer_id: UUID
    first_viewed_at: datetime
    last_viewed_at: datetime
    view_count: int


class ViewedOfferListResponse(BaseModel):
    """Most-recent-first public offer view history."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[ViewedOfferResponse, ...]


def _view_history(request: Request) -> ViewHistoryService:
    service: ViewHistoryService | None = getattr(request.app.state, "view_history", None)
    if service is None:
        raise AuthProblemError(
            status_code=503,
            code="view_history_unavailable",
            detail="View history is currently unavailable.",
        )
    return service


def _present_viewed_offer(view: ViewedOfferView) -> ViewedOfferResponse:
    return ViewedOfferResponse(
        offer_id=view.offer_id,
        first_viewed_at=view.first_viewed_at,
        last_viewed_at=view.last_viewed_at,
        view_count=view.view_count,
    )


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"


@router.put(
    "/visits/{visit_id}",
    operation_id="startAccountVisit",
    summary="Start one idempotent account visit",
    responses={401: {"description": "Authentication is required."}},
)
async def start_account_visit(
    visit_id: UUID,
    request: Request,
    response: Response,
) -> AccountVisitResponse:
    """Capture and return the prior authenticated visit baseline."""
    _disable_caching(response)
    account = await _require_account(request)
    visit = await _view_history(request).start_visit(
        user_id=account.id,
        visit_id=visit_id,
    )
    return AccountVisitResponse(
        visit_id=visit.visit_id,
        current_visit_at=visit.current_visit_at,
        previous_visit_at=visit.previous_visit_at,
    )


@router.get(
    "/offers",
    operation_id="listViewedOffers",
    summary="List viewed offers for the account",
    responses={401: {"description": "Authentication is required."}},
)
async def list_viewed_offers(
    request: Request,
    response: Response,
) -> ViewedOfferListResponse:
    """Return public viewed-offer history newest-first."""
    _disable_caching(response)
    account = await _require_account(request)
    items = await _view_history(request).list_viewed_offers(account.id)
    return ViewedOfferListResponse(
        items=tuple(_present_viewed_offer(item) for item in items),
    )


@router.put(
    "/offers/{offer_id}",
    operation_id="markOfferViewed",
    summary="Record one viewed offer",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The offer is absent or not public."},
    },
)
async def mark_offer_viewed(
    offer_id: UUID,
    request: Request,
    response: Response,
) -> ViewedOfferResponse:
    """Record one successful authenticated public-offer detail view."""
    _disable_caching(response)
    account = await _require_account(request)
    view = await _view_history(request).mark_offer_viewed(
        user_id=account.id,
        offer_id=offer_id,
    )
    if view is None:
        raise ResourceNotFoundError
    return _present_viewed_offer(view)
