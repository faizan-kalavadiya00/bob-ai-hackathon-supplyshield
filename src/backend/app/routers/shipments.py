"""Shipment read APIs used by the operational dashboard.

This router deliberately exposes shipment facts only. Resilience calculations
remain in the resilience service so their deterministic source is explicit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.shipment import Shipment

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.get("", summary="List shipments for operational investigation")
async def list_shipments(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return live shipment records without inventing an operational status."""
    result = await db.execute(select(Shipment).order_by(Shipment.created_at.desc()))
    shipments = result.scalars().all()
    return [
        {
            "id": shipment.id,
            "shipment_code": shipment.shipment_code,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "cargo_type": shipment.cargo_type,
            "cargo_value_usd": float(shipment.cargo_value_usd),
            "weight_kg": shipment.weight_kg,
            "priority": shipment.priority.value,
            "status": shipment.status.value,
            "temperature_sensitive": shipment.temperature_sensitive,
            "eta": shipment.eta,
        }
        for shipment in shipments
    ]
