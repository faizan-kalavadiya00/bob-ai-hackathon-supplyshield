from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models.cold_chain import ColdChainReading
from app.models.shipment import Shipment
from app.schemas.cold_chain import ColdChainReadingOut, ColdChainShipmentSummary, ColdChainShipmentDetail

router = APIRouter(prefix="/api/cold-chain", tags=["Cold Chain"])

@router.get("", response_model=List[ColdChainShipmentSummary])
async def list_cold_chain_shipments(db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        # Find all shipments that have cold chain readings
        shipments = sync_session.execute(
            select(Shipment)
            .join(ColdChainReading)
            .group_by(Shipment.id)
        ).scalars().all()
        
        result = []
        for ship in shipments:
            readings = sync_session.execute(
                select(ColdChainReading).where(ColdChainReading.shipment_id == ship.id)
            ).scalars().all()
            
            has_active_breach = any(r.is_breach for r in readings)
            result.append(ColdChainShipmentSummary(
                shipment_id=ship.id,
                shipment_code=ship.shipment_code,
                temperature_sensitive=ship.temperature_sensitive,
                min_temperature_c=ship.min_temperature_c,
                max_temperature_c=ship.max_temperature_c,
                has_active_breach=has_active_breach,
                reading_count=len(readings)
            ))
        return result
    
    return await db.run_sync(_work)

@router.get("/{shipment_id}", response_model=ColdChainShipmentDetail)
async def get_cold_chain_shipment(shipment_id: int, db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        ship = sync_session.get(Shipment, shipment_id)
        if not ship:
            return None
            
        readings = sync_session.execute(
            select(ColdChainReading)
            .where(ColdChainReading.shipment_id == shipment_id)
            .order_by(ColdChainReading.recorded_at.desc())
        ).scalars().all()
        
        has_active_breach = any(r.is_breach for r in readings)
        
        return ColdChainShipmentDetail(
            shipment_id=ship.id,
            shipment_code=ship.shipment_code,
            temperature_sensitive=ship.temperature_sensitive,
            min_temperature_c=ship.min_temperature_c,
            max_temperature_c=ship.max_temperature_c,
            has_active_breach=has_active_breach,
            reading_count=len(readings),
            readings=readings
        )
        
    detail = await db.run_sync(_work)
    if detail is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return detail

@router.get("/{shipment_id}/readings", response_model=List[ColdChainReadingOut])
async def list_shipment_readings(shipment_id: int, db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        # Validate shipment exists
        if not sync_session.get(Shipment, shipment_id):
            return None
            
        result = sync_session.execute(
            select(ColdChainReading)
            .where(ColdChainReading.shipment_id == shipment_id)
            .order_by(ColdChainReading.recorded_at.desc())
        )
        return result.scalars().all()
        
    readings = await db.run_sync(_work)
    if readings is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return readings
