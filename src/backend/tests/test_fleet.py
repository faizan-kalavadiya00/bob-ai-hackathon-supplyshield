import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.routers.fleet import router

test_app = FastAPI()
test_app.include_router(router)

@pytest.mark.asyncio
async def test_list_fleet():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/fleet")
        
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_fleet_vehicle_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/fleet/999999")
        
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_list_routes():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/routes")
        
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_route_alternatives_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/routes/999999/alternatives")
        
    assert response.status_code == 404
