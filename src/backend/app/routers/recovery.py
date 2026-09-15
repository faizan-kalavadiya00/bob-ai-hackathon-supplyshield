from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.recovery import RecoveryPlan
from app.models.disruption import ShipmentDisruption
from app.schemas.recovery import RecoveryPlanOut, RecoveryPlanCreate

router = APIRouter(prefix="/api/recovery", tags=["Recovery"])

@router.get("/{disruption_id}", response_model=List[RecoveryPlanOut])
async def get_recovery_plan(disruption_id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        return session.scalars(select(RecoveryPlan).where(RecoveryPlan.disruption_id == disruption_id)).all()
        
    plans = await db.run_sync(_work)
    return plans

@router.get("/shipment/{shipment_id}", response_model=List[RecoveryPlanOut])
async def get_recovery_plan_for_shipment(shipment_id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        # Find all disruptions for this shipment
        disruptions = session.scalars(
            select(ShipmentDisruption).where(ShipmentDisruption.shipment_id == shipment_id)
        ).all()
        
        disruption_ids = [d.disruption_id for d in disruptions]
        if not disruption_ids:
            return []
            
        return session.scalars(
            select(RecoveryPlan).where(RecoveryPlan.disruption_id.in_(disruption_ids))
        ).all()
        
    plans = await db.run_sync(_work)
    return plans
