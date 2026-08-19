"""HTTP adapter for starred catalog locations."""

from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict

from wef_backend.errors import AuthProblemError, ResourceNotFoundError
from wef_backend.features.identity.application.favorites import FavoriteService
from wef_backend.features.identity.interface.router import _require_account

router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])


class FavoriteLocationResponse(BaseModel):
    """One starred location summary."""

    model_config = ConfigDict(extra="forbid")

    location_id: UUID
    display_name: str
    display_address: str
    district: str | None
    created_at: str


class FavoriteListResponse(BaseModel):
    """Account favorites newest-first."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[FavoriteLocationResponse, ...]


def _favorites(request: Request) -> FavoriteService:
    service: FavoriteService | None = getattr(request.app.state, "favorites", None)
    if service is None:
        raise AuthProblemError(
            status_code=503,
            code="favorites_unavailable",
            detail="Favorites are currently unavailable.",
        )
    return service


@router.get(
    "",
    operation_id="listFavoriteLocations",
    summary="List starred locations for the account",
    responses={401: {"description": "Authentication is required."}},
)
async def list_favorite_locations(request: Request) -> FavoriteListResponse:
    """Return starred locations with public labels."""
    account = await _require_account(request)
    items = await _favorites(request).list_favorites(account.id)
    return FavoriteListResponse(
        items=tuple(
            FavoriteLocationResponse(
                location_id=item.location_id,
                display_name=item.display_name,
                display_address=item.display_address,
                district=item.district,
                created_at=item.created_at,
            )
            for item in items
        ),
    )


@router.put(
    "/{location_id}",
    status_code=204,
    operation_id="addFavoriteLocation",
    summary="Star one location",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The location is absent or not public."},
    },
)
async def add_favorite_location(
    location_id: UUID,
    request: Request,
) -> Response:
    """Star one accepted in-scope location."""
    account = await _require_account(request)
    added = await _favorites(request).add_favorite(account.id, location_id)
    if not added:
        raise ResourceNotFoundError
    return Response(status_code=204)


@router.delete(
    "/{location_id}",
    status_code=204,
    operation_id="removeFavoriteLocation",
    summary="Remove one starred location",
    responses={401: {"description": "Authentication is required."}},
)
async def remove_favorite_location(
    location_id: UUID,
    request: Request,
) -> Response:
    """Remove one starred location idempotently."""
    account = await _require_account(request)
    await _favorites(request).remove_favorite(account.id, location_id)
    return Response(status_code=204)
