import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.routers.recovery import router

test_app = FastAPI()
test_app.include_router(router)

@pytest.mark.asyncio
async def test_get_recovery_plan():
    pass

@pytest.mark.asyncio
async def test_get_recovery_plan_shipment():
    pass
