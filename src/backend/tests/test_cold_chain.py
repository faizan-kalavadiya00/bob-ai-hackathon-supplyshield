import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.routers.cold_chain import router

test_app = FastAPI()
test_app.include_router(router)

@pytest.mark.asyncio
async def test_list_cold_chain_shipments():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/cold-chain")
        
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_cold_chain_shipment_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/cold-chain/999999")
        
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_list_shipment_readings_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/cold-chain/999999/readings")
        
    assert response.status_code == 404
