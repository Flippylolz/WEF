"""Estate HTTP routes."""

from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, Request

from wef_backend.features.estates.interface.presenter import EstatesResponse, present_estates

if TYPE_CHECKING:
    from wef_backend.features.estates.application import ListEstates

router = APIRouter(prefix="/api/v1/estates", tags=["estates"])


@router.get(
    "",
    operation_id="listEstates",
    summary="List synthetic estates",
)
async def list_estates(request: Request) -> EstatesResponse:
    """Run the application query obtained from explicit app state."""
    query = cast("ListEstates", request.app.state.list_estates)
    return present_estates(await query())
