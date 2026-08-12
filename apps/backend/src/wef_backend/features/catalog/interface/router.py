"""HTTP adapter for the grouped map query."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from wef_backend.errors import (
    NotFoundProblemResponse,
    ProblemResponse,
    QueryValidationError,
    ResourceNotFoundError,
)
from wef_backend.features.catalog.application import (
    BoundingBox,
    CursorError,
    MapFilterError,
    MapFilters,
)
from wef_backend.features.catalog.domain import ContentType, MarketType
from wef_backend.features.catalog.interface.presenter import (
    FilterFacetsResponse,
    LocationMapResponse,
    LocationOfferPageResponse,
    present_facets,
    present_location_map,
    present_location_offer_page,
)

RoomValue = Annotated[int, Field(ge=0, le=20)]
DistrictValue = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]


class MapQueryParams(BaseModel):
    """Strict transport syntax for the M1 map filter set."""

    model_config = ConfigDict(extra="forbid")

    bbox: str = Field(min_length=7, max_length=100)
    price_min: int | None = Field(default=None, ge=0, le=10_000_000_00)
    price_max: int | None = Field(default=None, ge=0, le=10_000_000_00)
    area_min: Decimal | None = Field(default=None, gt=0, le=100_000)
    area_max: Decimal | None = Field(default=None, gt=0, le=100_000)
    rooms: list[RoomValue] = Field(default_factory=list, max_length=10)
    district: list[DistrictValue] = Field(default_factory=list, max_length=20)
    market_type: list[MarketType] = Field(default_factory=list, max_length=5)
    content_type: list[ContentType] = Field(default_factory=list, max_length=5)
    published_from: datetime | None = None
    published_to: datetime | None = None

    def to_filters(self) -> MapFilters:
        """Translate validated HTTP syntax to the application DTO."""
        try:
            return MapFilters(
                bbox=BoundingBox.parse(self.bbox),
                price_min=self.price_min,
                price_max=self.price_max,
                area_min=self.area_min,
                area_max=self.area_max,
                rooms=tuple(self.rooms),
                districts=tuple(self.district),
                market_types=tuple(self.market_type),
                content_types=tuple(self.content_type),
                published_from=self.published_from,
                published_to=self.published_to,
            )
        except MapFilterError as error:
            raise QueryValidationError(str(error)) from error


class LocationOfferQueryParams(MapQueryParams):
    """Shared filters plus explicit history and cursor controls."""

    include_non_matching: bool = False
    cursor: str | None = Field(default=None, max_length=512)
    limit: int = Field(default=20, ge=1, le=50)


router = APIRouter(prefix="/api/v1/map", tags=["map"])
facets_router = APIRouter(prefix="/api/v1", tags=["filters"])
locations_router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get(
    "/locations",
    response_model=LocationMapResponse,
    operation_id="queryMapLocations",
    summary="Query grouped map locations",
    responses={
        304: {"description": "The filtered projection has not changed."},
        422: {
            "model": ProblemResponse,
            "description": "The query is malformed, contradictory, or unsafe.",
        },
    },
)
async def query_map_locations(
    request: Request,
    response: Response,
    filters: Annotated[MapQueryParams, Query()],
    if_none_match: Annotated[str | None, Header()] = None,
) -> LocationMapResponse | Response:
    """Return grouped accepted locations for the normalized filter query."""
    result = await request.app.state.query_map(filters.to_filters())
    headers = {
        "Cache-Control": "public, max-age=30",
        "ETag": result.etag,
        "Vary": "If-None-Match",
    }
    if _etag_matches(if_none_match, result.etag):
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return present_location_map(result, request_id=request.state.request_id)


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    """Match a strong ETag in a bounded standard header list."""
    if if_none_match is None:
        return False
    values = {item.strip() for item in if_none_match.split(",")[:20]}
    return "*" in values or etag in values


@facets_router.get(
    "/filter-facets",
    operation_id="getFilterFacets",
    summary="Get canonical visible filter facets",
)
async def get_filter_facets(request: Request) -> FilterFacetsResponse:
    """Return canonical options and visible dataset bounds."""
    return present_facets(await request.app.state.query_facets())


@locations_router.get(
    "/{location_id}/offers",
    operation_id="listLocationOffers",
    summary="List dated offers for a selected location",
    responses={
        404: {
            "model": NotFoundProblemResponse,
            "description": "The location is absent or not public.",
        },
        422: {
            "model": ProblemResponse,
            "description": "The filters or cursor are invalid.",
        },
    },
)
async def list_location_offers(
    location_id: UUID,
    request: Request,
    query: Annotated[LocationOfferQueryParams, Query()],
) -> LocationOfferPageResponse:
    """Return matching offers first and optional non-matching history."""
    try:
        page = await request.app.state.browse_location_offers(
            location_id=location_id,
            filters=query.to_filters(),
            include_non_matching=query.include_non_matching,
            cursor=query.cursor,
            limit=query.limit,
        )
    except CursorError as error:
        raise QueryValidationError(str(error)) from error
    if not page.location_exists:
        raise ResourceNotFoundError
    return present_location_offer_page(page)
