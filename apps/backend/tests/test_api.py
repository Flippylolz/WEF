"""HTTP and offline-schema tests with explicit app-state doubles."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from tests.fakes import (
    FakeCatalogBrowse,
    FakeEstateQuery,
    FakeMapQuery,
    FakeOfferDetailQuery,
    always_ready,
    build_admin_service,
    build_contact_service,
    build_favorites_service,
    build_identity_service,
    build_view_history_service,
    close_nothing,
    empty_facet_snapshot,
    never_ready,
)
from wef_backend.app import create_http_app
from wef_backend.composition import AppServices, ReadyCheck
from wef_backend.features.catalog.application import (
    BrowseLocationOffers,
    BrowseViewportListings,
    ConfidenceIndicator,
    FacetSnapshot,
    GetOfferDetail,
    ListingBrowseRecord,
    ListingLocationContext,
    MapLocationRecord,
    OfferBrowseRecord,
    QueryFacets,
    QueryMapLocations,
)
from wef_backend.features.catalog.application.offer_detail import (
    LocationSummaryDTO,
    OfferDetailRecord,
)
from wef_backend.features.catalog.domain import ContentType, MarketType
from wef_backend.features.estates.application import EstateRecord, ListEstates
from wef_backend.features.estates.domain import Availability, GeoPoint
from wef_backend.features.identity.infrastructure.security import MemoryRateLimiter
from wef_backend.middleware.public_rate_limit import RateLimiter


def create_test_app(
    ready_check: ReadyCheck = always_ready,
    *,
    public_rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    """Build an isolated app with no database resources."""
    browse = FakeCatalogBrowse(facets=empty_facet_snapshot())
    services = AppServices(
        list_estates=ListEstates(FakeEstateQuery(records=())),
        query_map=QueryMapLocations(FakeMapQuery()),
        query_facets=QueryFacets(browse),
        browse_location_offers=BrowseLocationOffers(browse),
        browse_viewport_listings=BrowseViewportListings(browse),
        get_offer_detail=GetOfferDetail(FakeOfferDetailQuery()),
        is_ready=ready_check,
        close=close_nothing,
        identity=build_identity_service(),
        favorites=build_favorites_service(),
        view_history=build_view_history_service(),
        contacts=build_contact_service(),
        admin=build_admin_service(),
        auth_cookie_secure=False,
        admin_session_secret="test-admin-session-secret",
        public_rate_limiter=public_rate_limiter or MemoryRateLimiter(),
    )
    return create_http_app(services)


@asynccontextmanager
async def api_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Exercise an ASGI app while explicitly managing its lifespan."""
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client


async def test_list_estates_uses_app_state_override() -> None:
    """Call the query service supplied through explicit application state."""
    app = create_test_app()
    app.state.list_estates = ListEstates(
        FakeEstateQuery(
            records=(
                EstateRecord(
                    estate_id=23,
                    title="Synthetic city studio",
                    location=GeoPoint(longitude=-3.7038, latitude=40.4168),
                    availability=Availability.AVAILABLE,
                ),
            ),
        )
    )

    async with api_client(app) as client:
        response = await client.get("/api/v1/estates")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [
            {
                "availability": "available",
                "availability_label_key": "estates.availability.available",
                "id": 23,
                "location": {"latitude": 40.4168, "longitude": -3.7038},
                "title": "Synthetic city studio",
            },
        ],
    }


async def test_health_endpoints_reflect_composed_readiness() -> None:
    """Separate process liveness from database readiness."""
    async with api_client(create_test_app()) as ready_client:
        successful_ready_response = await ready_client.get("/api/v1/health/ready")
    async with api_client(create_test_app(never_ready)) as client:
        live_response = await client.get("/api/v1/health/live")
        ready_response = await client.get("/api/v1/health/ready")

    assert successful_ready_response.status_code == status.HTTP_200_OK
    assert successful_ready_response.json() == {"status": "ready"}
    assert live_response.status_code == status.HTTP_200_OK
    assert live_response.json() == {"status": "live"}
    assert ready_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_map_endpoint_presents_etag_and_conditional_response() -> None:
    """Present grouped backend decisions and honor conditional requests."""
    app = create_test_app()
    app.state.query_map = QueryMapLocations(
        FakeMapQuery(
            records=(
                MapLocationRecord(
                    id=UUID("10000000-0000-4000-8000-000000000001"),
                    longitude=21.0122,
                    latitude=52.2297,
                    display_name="Synthetic Śródmieście",
                    display_address="Synthetic address",
                    district="Śródmieście",
                    precision="building",
                    confidence=Decimal("0.97"),
                    matching_offer_count=1,
                    total_offer_count=2,
                    latest_published_at=datetime(2026, 8, 1, tzinfo=UTC),
                    price_min_minor=600_000_00,
                    price_max_minor=650_000_00,
                    area_min_sqm=Decimal("40.0"),
                    area_max_sqm=Decimal("45.0"),
                ),
            ),
        ),
    )

    async with api_client(app) as client:
        response = await client.get(
            "/api/v1/map/locations",
            params={"bbox": "20.9,52.1,21.2,52.4"},
        )
        conditional = await client.get(
            "/api/v1/map/locations",
            params={"bbox": "20.9,52.1,21.2,52.4"},
            headers={"If-None-Match": response.headers["etag"]},
        )

    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["etag"].startswith('W/"')
    assert response.headers["x-request-id"] == payload["meta"]["request_id"]
    assert payload["features"][0]["geometry"]["coordinates"] == [21.0122, 52.2297]
    assert payload["features"][0]["properties"]["confidence"] == "high"
    assert payload["features"][0]["properties"]["matching_offer_count"] == 1
    assert payload["features"][0]["properties"]["total_offer_count"] == 2
    assert conditional.status_code == status.HTTP_304_NOT_MODIFIED
    assert conditional.content == b""


async def test_map_endpoint_rejects_unknown_and_unsafe_queries_safely() -> None:
    """Reject unbounded/unknown inputs without reflecting their values."""
    app = create_test_app()

    async with api_client(app) as client:
        unknown = await client.get(
            "/api/v1/map/locations",
            params={
                "bbox": "20.9,52.1,21.2,52.4",
                "raw_payload": "do-not-reflect-this",
            },
        )
        unsafe = await client.get(
            "/api/v1/map/locations",
            params={"bbox": "-180,-90,180,90"},
        )

    assert unknown.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert unknown.headers["content-type"].startswith("application/problem+json")
    assert "do-not-reflect-this" not in unknown.text
    assert unknown.json()["code"] == "invalid_query"
    assert unsafe.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert unsafe.json()["detail"] == "bbox must remain within the Warsaw query boundary"


async def test_facets_and_selected_location_offer_contracts() -> None:
    """Expose backend-owned options and dated offer display decisions."""
    app = create_test_app()
    facets = FacetSnapshot(
        districts=("srodmiescie", "wola"),
        rooms=(1, 2, 3),
        market_types=(MarketType.PRIMARY, MarketType.SECONDARY),
        content_types=(ContentType.DEVELOPMENT, ContentType.UNIT),
        price_min_minor=69_000_000,
        price_max_minor=149_000_000,
        area_min_sqm=Decimal("29.50"),
        area_max_sqm=Decimal("72.00"),
        published_from=datetime(2026, 6, 30, tzinfo=UTC),
        published_to=datetime(2026, 8, 5, tzinfo=UTC),
    )
    records = (
        OfferBrowseRecord(
            id=UUID("20000000-0000-4000-8000-000000000001"),
            content_type=ContentType.DEVELOPMENT,
            market_type=MarketType.PRIMARY,
            published_at=datetime(2026, 8, 1, tzinfo=UTC),
            currency="PLN",
            price_min_minor=80_000_000,
            price_max_minor=125_000_000,
            parking_price_min_minor=4_500_000,
            parking_price_max_minor=4_500_000,
            parking_included_in_price=False,
            storage_price_min_minor=None,
            storage_price_max_minor=None,
            storage_included_in_price=True,
            area_min_sqm=Decimal("35.00"),
            area_max_sqm=Decimal("71.50"),
            rooms_min=1,
            rooms_max=3,
            floor_label=None,
            delivery_label="Synthetic delivery",
            matches_filters=True,
        ),
    )
    browse = FakeCatalogBrowse(
        facets=facets,
        records=records,
        matching_count=1,
        total_count=2,
    )
    app.state.query_facets = QueryFacets(browse)
    app.state.browse_location_offers = BrowseLocationOffers(browse)

    async with api_client(app) as client:
        facet_response = await client.get("/api/v1/filter-facets")
        offer_response = await client.get(
            "/api/v1/locations/10000000-0000-4000-8000-000000000001/offers",
            params={"bbox": "20.9,52.1,21.2,52.4"},
        )

    assert facet_response.status_code == status.HTTP_200_OK
    assert facet_response.json()["districts"] == ["srodmiescie", "wola"]
    payload = offer_response.json()
    assert offer_response.status_code == status.HTTP_200_OK
    assert payload["matching_count"] == 1
    assert payload["total_count"] == 2
    assert payload["items"][0]["display_name"] == "Development post · Primary market"
    assert payload["items"][0]["data_confidence"] == "complete"
    assert payload["items"][0]["data_origin"] == "parser"
    assert payload["items"][0]["parking_price_min_minor"] == 4_500_000
    assert payload["items"][0]["parking_price_max_minor"] == 4_500_000
    assert payload["items"][0]["storage_included_in_price"] is True
    assert "source_text" not in offer_response.text


async def test_selected_location_hides_absence_and_rejects_bad_cursor() -> None:
    """Use safe indistinguishable not-found and validation problems."""
    app = create_test_app()
    missing = FakeCatalogBrowse(
        facets=empty_facet_snapshot(),
        location_exists=False,
    )
    app.state.browse_location_offers = BrowseLocationOffers(missing)

    async with api_client(app) as client:
        not_found = await client.get(
            "/api/v1/locations/10000000-0000-4000-8000-000000000099/offers",
            params={"bbox": "20.9,52.1,21.2,52.4"},
        )
        bad_cursor = await client.get(
            "/api/v1/locations/10000000-0000-4000-8000-000000000099/offers",
            params={
                "bbox": "20.9,52.1,21.2,52.4",
                "cursor": "not-valid!",
            },
        )

    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert not_found.json()["code"] == "not_found"
    assert bad_cursor.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_cursor.json()["detail"] == "cursor is invalid"


async def test_runtime_docs_routes_are_absent_but_offline_schema_works() -> None:
    """Disable HTTP documentation while retaining direct schema generation."""
    app = create_http_app()
    async with api_client(app) as client:
        assert (await client.get("/docs")).status_code == status.HTTP_404_NOT_FOUND
        assert (await client.get("/redoc")).status_code == status.HTTP_404_NOT_FOUND
        assert (await client.get("/openapi.json")).status_code == status.HTTP_404_NOT_FOUND

    schema = app.openapi()

    assert schema["paths"]["/api/v1/estates"]["get"]["operationId"] == "listEstates"
    assert schema["paths"]["/api/v1/map/locations"]["get"]["operationId"] == ("queryMapLocations")
    assert schema["paths"]["/api/v1/filter-facets"]["get"]["operationId"] == ("getFilterFacets")
    assert (
        schema["paths"]["/api/v1/locations/{location_id}/offers"]["get"]["operationId"]
        == "listLocationOffers"
    )
    assert schema["paths"]["/api/v1/offers/{offer_id}"]["get"]["operationId"] == "getOfferDetail"


async def test_offer_detail_hides_absence_and_excludes_sensitive_fields() -> None:
    """Return safe not-found behavior and only masked public source text."""
    app = create_test_app()
    app.state.get_offer_detail = GetOfferDetail(FakeOfferDetailQuery(record=None))

    async with api_client(app) as client:
        not_found = await client.get(
            "/api/v1/offers/20000000-0000-4000-8000-000000000099",
        )

    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert not_found.json()["code"] == "not_found"

    detail_record = OfferDetailRecord(
        id=UUID("20000000-0000-4000-8000-000000000002"),
        content_type=ContentType.UNIT,
        market_type=MarketType.SECONDARY,
        published_at=datetime(2026, 7, 18, 9, 30, tzinfo=UTC),
        currency="PLN",
        price_min_minor=105_000_000,
        price_max_minor=105_000_000,
        parking_price_min_minor=None,
        parking_price_max_minor=None,
        parking_included_in_price=False,
        storage_price_min_minor=None,
        storage_price_max_minor=None,
        storage_included_in_price=False,
        area_min_sqm=Decimal("48.20"),
        area_max_sqm=Decimal("48.20"),
        rooms_min=2,
        rooms_max=2,
        floor_label="Synthetic floor 4",
        delivery_label=None,
        public_source_text="Masked public text only.",
        parser_version="synthetic-m1-v1",
        location=LocationSummaryDTO(
            id=UUID("10000000-0000-4000-8000-000000000001"),
            display_name="Synthetic Central Residence",
            display_address="Synthetic address 1",
            district="srodmiescie",
            coordinate_precision="building",
            confidence=ConfidenceIndicator.HIGH,
        ),
        development=None,
        field_confidence=(),
        media=(),
        source_message_id=None,
        verified_source_url=None,
        source_history=(),
    )
    app.state.get_offer_detail = GetOfferDetail(FakeOfferDetailQuery(record=detail_record))

    async with api_client(app) as client:
        response = await client.get("/api/v1/offers/20000000-0000-4000-8000-000000000002")

    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert payload["public_source_text"] == "Masked public text only."
    assert payload["data_origin"] == "parser"
    assert payload["verified_source_url"] is None
    assert payload["media"] == []
    assert "source_text_excerpt" not in response.text
    assert "raw_payload" not in response.text
    assert "text_original" not in response.text


async def test_error_responses_include_request_id_header() -> None:
    """Problem responses carry the same correlation id as success responses."""
    app = create_test_app()
    app.state.browse_location_offers = BrowseLocationOffers(
        FakeCatalogBrowse(facets=empty_facet_snapshot(), location_exists=False),
    )

    async with api_client(app) as client:
        response = await client.get(
            "/api/v1/locations/10000000-0000-4000-8000-000000000099/offers",
            params={"bbox": "20.9,52.1,21.2,52.4"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["x-request-id"] == response.json()["request_id"]


async def test_public_read_rate_limit_returns_safe_throttle() -> None:
    """Blocked public reads return a bounded throttle problem without reflection."""

    class BlockAll:
        def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
            del key, limit, window_seconds
            return False

    app = create_test_app(public_rate_limiter=BlockAll())

    async with api_client(app) as client:
        response = await client.get(
            "/api/v1/map/locations",
            params={"bbox": "20.9,52.1,21.2,52.4"},
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    payload = response.json()
    assert payload["code"] == "rate_limited"
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["x-request-id"] == payload["request_id"]
    assert "127.0.0.1" not in response.text


async def test_filter_facets_are_short_cacheable() -> None:
    """Canonical facets advertise a short public cache lifetime."""
    app = create_test_app()

    async with api_client(app) as client:
        response = await client.get("/api/v1/filter-facets")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["cache-control"] == "public, max-age=60"


async def test_viewport_listings_present_parent_location_and_reject_bad_cursor() -> None:
    """Present newest-first listing cards and validate cursors safely."""
    app = create_test_app()
    browse = FakeCatalogBrowse(
        facets=empty_facet_snapshot(),
        viewport_records=(
            ListingBrowseRecord(
                id=UUID("20000000-0000-4000-8000-000000000001"),
                content_type=ContentType.DEVELOPMENT,
                market_type=MarketType.PRIMARY,
                published_at=datetime(2026, 8, 1, tzinfo=UTC),
                currency="PLN",
                price_min_minor=80_000_000,
                price_max_minor=125_000_000,
                parking_price_min_minor=None,
                parking_price_max_minor=None,
                parking_included_in_price=False,
                storage_price_min_minor=None,
                storage_price_max_minor=None,
                storage_included_in_price=False,
                area_min_sqm=Decimal("35.00"),
                area_max_sqm=Decimal("71.50"),
                rooms_min=1,
                rooms_max=3,
                floor_label=None,
                delivery_label=None,
                location=ListingLocationContext(
                    id=UUID("10000000-0000-4000-8000-000000000001"),
                    display_name="Synthetic Central Residence",
                    display_address="Synthetic address 1, Warsaw",
                    district="srodmiescie",
                    precision="address",
                    confidence=Decimal("0.60"),
                    longitude=21.0122,
                    latitude=52.2297,
                ),
            ),
        ),
        viewport_matching_count=1,
    )
    app.state.browse_viewport_listings = BrowseViewportListings(browse)

    async with api_client(app) as client:
        listing_response = await client.get(
            "/api/v1/listings",
            params={
                "bbox": "20.9,52.1,21.2,52.4",
                "price_min": 50_000_000,
                "rooms": 2,
                "limit": 1,
            },
        )
        bad_cursor = await client.get(
            "/api/v1/listings",
            params={"bbox": "20.9,52.1,21.2,52.4", "cursor": "not-valid!"},
        )
        schema = app.openapi()

    assert listing_response.status_code == status.HTTP_200_OK
    payload = listing_response.json()
    assert payload["matching_count"] == 1
    assert payload["next_cursor"] is None
    item = payload["items"][0]
    assert item["display_name"] == "Development post · Primary market"
    assert item["data_confidence"] == "complete"
    assert item["price_max_minor"] == 125_000_000
    assert item["location"]["display_name"] == "Synthetic Central Residence"
    assert item["location"]["district"] == "srodmiescie"
    assert item["location"]["confidence"] == "low"
    assert item["location"]["geometry"]["coordinates"] == [21.0122, 52.2297]
    assert "source_text" not in listing_response.text
    assert "public_source_text" not in listing_response.text

    assert bad_cursor.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_cursor.json()["detail"] == "cursor is invalid"

    assert schema["paths"]["/api/v1/listings"]["get"]["operationId"] == ("listViewportListings")
