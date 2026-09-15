"""Health-check router.

GET /health  — lightweight liveness probe; no DB call.
GET /health/db — checks database connectivity.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    service: str
    version: str
    environment: str


class DbHealthResponse(HealthResponse):
    database: Literal["connected", "unavailable"]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 when the service process is running.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="supplyshield-backend",
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get(
    "/health/db",
    response_model=DbHealthResponse,
    summary="Database readiness probe",
    description="Returns 200 when the database is reachable, 503 otherwise.",
)
async def db_health_check(
    db: AsyncSession = Depends(get_db),
) -> DbHealthResponse:
    settings = get_settings()
    try:
        await db.execute(text("SELECT 1"))
        db_status: Literal["connected", "unavailable"] = "connected"
        http_status = status.HTTP_200_OK
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        db_status = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    response = DbHealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        service="supplyshield-backend",
        version=settings.app_version,
        environment=settings.app_env,
        database=db_status,
    )

    if http_status != status.HTTP_200_OK:
        raise HTTPException(status_code=http_status, detail=response.model_dump())

    return response
