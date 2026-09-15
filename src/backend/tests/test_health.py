"""Tests for the /health endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "supplyshield-backend"
    assert "version" in body
    assert "environment" in body


@pytest.mark.asyncio
async def test_health_content_type_is_json():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_openapi_schema_available():
    """OpenAPI docs endpoint should be reachable."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "SupplyShield"


@pytest.mark.asyncio
async def test_operational_api_routes_are_registered():
    """Guard static summary route placement and the shipment investigation API."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "/api/shipments/resilience/summary" in paths
    assert "/api/shipments" in paths
