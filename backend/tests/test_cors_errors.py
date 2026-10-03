import httpx
import pytest
from app.config import settings
from app.main import api_app, app
from fastapi.routing import APIRoute


@pytest.mark.asyncio
async def test_cors_headers_are_present_on_unhandled_server_errors():
    async def fail():
        raise RuntimeError("simulated backend failure")

    path = "/_test/unhandled-cors-error"
    origin = settings.CORS_ORIGINS[0]
    api_app.add_api_route(path, fail, methods=["GET"])
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                path,
                headers={"Origin": origin},
            )
    finally:
        api_app.router.routes[:] = [
            route
            for route in api_app.router.routes
            if not (isinstance(route, APIRoute) and route.path == path)
        ]

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == origin
