"""HTTP and offline-schema tests with explicit app-state doubles."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from tests.fakes import FakeEstateQuery, always_ready, close_nothing, never_ready
from wef_backend.app import create_http_app
from wef_backend.composition import AppServices, ReadyCheck
from wef_backend.features.estates.application import EstateRecord, ListEstates
from wef_backend.features.estates.domain import Availability, GeoPoint


def create_test_app(ready_check: ReadyCheck = always_ready) -> FastAPI:
    """Build an isolated app with no database resources."""
    services = AppServices(
        list_estates=ListEstates(FakeEstateQuery(records=())),
        is_ready=ready_check,
        close=close_nothing,
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


async def test_runtime_docs_routes_are_absent_but_offline_schema_works() -> None:
    """Disable HTTP documentation while retaining direct schema generation."""
    app = create_http_app()
    async with api_client(app) as client:
        assert (await client.get("/docs")).status_code == status.HTTP_404_NOT_FOUND
        assert (await client.get("/redoc")).status_code == status.HTTP_404_NOT_FOUND
        assert (await client.get("/openapi.json")).status_code == status.HTTP_404_NOT_FOUND

    schema = app.openapi()

    assert schema["paths"]["/api/v1/estates"]["get"]["operationId"] == "listEstates"
